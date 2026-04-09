from __future__ import annotations

import secrets
import threading
import urllib.parse
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable

import requests

from send.credentials.store import SecureConfig

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
REDIRECT_HOST = "127.0.0.1"


class GoogleLoopbackTokenProvider:
    """
    Handles access token acquisition for Google APIs using the authorization
    code flow with a loopback redirect (http://127.0.0.1:<port>).

    Requires a "Desktop app" OAuth 2.0 client from Google Cloud Console.
    """

    TOKEN_CACHE_KEY = "google_token_cache"
    GOOGLE_CONFIG_KEY = "google_api_config"
    CLIENT_ID_KEY = "google_client_id"
    CLIENT_SECRET_KEY = "google_client_secret"

    def __init__(
        self,
        secure_config: SecureConfig | None = None,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        scopes: list[str] | None = None,
        show_message: Callable[[object], None] | None = None,
    ) -> None:
        self.secure_config = secure_config
        self._show_message = show_message
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes

        self._config_snapshot = self._load_config()
        self.client_id = self.client_id or self._extract_client_id(self._config_snapshot)
        self.client_secret = self.client_secret or self._extract_client_secret(self._config_snapshot)
        self.scopes = (
            self._normalize_scopes(self.scopes)
            or self._extract_scopes(self._config_snapshot)
            or DEFAULT_SCOPES
        )

        if not self.client_id:
            raise ValueError(
                "client_id is required for Google loopback flow. "
                "Provide it directly or store it in SecureConfig under 'google_client_id'."
            )
        if not self.client_secret:
            raise ValueError(
                "client_secret is required for Google loopback flow. "
                "Provide it directly or store it in SecureConfig under 'google_client_secret'."
            )

        self._token = self._load_token(self._config_snapshot)

    def acquire_token(self, interactive: bool = True, scopes: list[str] | None = None) -> str:
        """
        Get a valid Google API access token.

        1. Use cached token if still valid.
        2. Refresh using refresh_token if available.
        3. If allowed, open a browser to complete the authorization code flow.
        """
        resolved_scopes = self._normalize_scopes(scopes) or self.scopes or DEFAULT_SCOPES
        self.scopes = resolved_scopes

        if self._is_token_valid(self._token):
            return self._token["access_token"]  # type: ignore[index]

        if self._token and self._token.get("refresh_token"):
            refreshed = self._refresh_token(self._token["refresh_token"], resolved_scopes)
            if refreshed:
                return refreshed

        if not interactive:
            raise RuntimeError("Could not obtain Google access token and interactive auth is disabled.")

        code, redirect_uri = self._run_loopback_flow(resolved_scopes)
        token_data = self._exchange_code(code, redirect_uri, resolved_scopes)
        self._token = token_data
        self._persist_token(token_data)
        return token_data["access_token"]

    def _run_loopback_flow(self, scopes: list[str]) -> tuple[str, str]:
        state = secrets.token_urlsafe(16)

        auth_params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

        result: dict[str, str] = {}

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urllib.parse.urlparse(self.path)
                result.update(urllib.parse.parse_qsl(parsed.query))
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><p>Authorization complete. You may close this window.</p></body></html>"
                )

            def log_message(self, format: str, *args: Any) -> None:
                pass  # suppress request logs

        # Port 0 lets the OS pick a free port atomically — no TOCTOU race.
        server = HTTPServer((REDIRECT_HOST, 0), _Handler)
        port = server.server_address[1]
        redirect_uri = f"http://{REDIRECT_HOST}:{port}"
        server_thread = threading.Thread(target=server.handle_request, daemon=True)
        server_thread.start()

        self._display_message(auth_url)
        webbrowser.open(auth_url)

        server_thread.join(timeout=120)
        server.server_close()

        if server_thread.is_alive():
            raise RuntimeError(
                "OAuth loopback flow timed out after 120 seconds. "
                "The browser window may still be open."
            )

        code = result.get("code")
        if not code:
            raise RuntimeError("No authorization code received. Authorization may have timed out or been denied.")
        if result.get("state") != state:
            raise RuntimeError("OAuth state mismatch.")

        return code, redirect_uri

    def _exchange_code(self, code: str, redirect_uri: str, scopes: list[str]) -> dict[str, Any]:
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        try:
            response = requests.post(TOKEN_URL, data=payload, timeout=10)
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Network error during Google token exchange: {exc}") from exc
        data = self._safe_json(response)
        if response.status_code != 200 or "access_token" not in data:
            raise RuntimeError(f"Google token exchange failed: {data}")
        return self._finalize_token_payload(data, scopes)

    def _refresh_token(self, refresh_token: str, scopes: list[str]) -> str | None:
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            response = requests.post(TOKEN_URL, data=payload, timeout=10)
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Network error during Google token refresh: {exc}") from exc
        if response.status_code != 200:
            return None
        data = self._safe_json(response)
        if "access_token" not in data:
            return None
        if "refresh_token" not in data:
            data["refresh_token"] = refresh_token
        finalized = self._finalize_token_payload(data, scopes)
        self._token = finalized
        self._persist_token(finalized)
        return finalized["access_token"]

    def _display_message(self, auth_url: str) -> None:
        if callable(self._show_message):
            self._show_message(auth_url)
            return
        print(
            f"Opening browser for Google authorization.\n"
            f"If it does not open automatically, visit:\n{auth_url}",
            flush=True,
        )

    def _load_config(self) -> dict[str, Any]:
        if not self.secure_config:
            return {}
        return self.secure_config.load() or {}

    def _extract_client_id(self, data: dict[str, Any]) -> str | None:
        if not data:
            return None
        flat_value = data.get(self.CLIENT_ID_KEY)
        if flat_value:
            return str(flat_value)
        google_config = data.get(self.GOOGLE_CONFIG_KEY)
        if isinstance(google_config, dict):
            nested_value = google_config.get("client_id")
            if nested_value:
                return str(nested_value)
        return None

    def _extract_client_secret(self, data: dict[str, Any]) -> str | None:
        if not data:
            return None
        flat_value = data.get(self.CLIENT_SECRET_KEY)
        if flat_value:
            return str(flat_value)
        google_config = data.get(self.GOOGLE_CONFIG_KEY)
        if isinstance(google_config, dict):
            nested_value = google_config.get("client_secret")
            if nested_value:
                return str(nested_value)
        return None

    def _extract_scopes(self, data: dict[str, Any]) -> list[str] | None:
        if not data:
            return None
        google_config = data.get(self.GOOGLE_CONFIG_KEY)
        if isinstance(google_config, dict):
            return self._normalize_scopes(google_config.get("scopes"))
        return None

    def _load_token(self, data: dict[str, Any]) -> dict[str, Any] | None:
        token_data = data.get(self.TOKEN_CACHE_KEY)
        if isinstance(token_data, dict):
            return token_data
        google_config = data.get(self.GOOGLE_CONFIG_KEY)
        if isinstance(google_config, dict):
            token_value = google_config.get("token_value")
            token_timestamp = google_config.get("token_timestamp")
            if token_value and token_timestamp:
                return {
                    "access_token": token_value,
                    "expires_at": token_timestamp,
                }
        return None

    def _is_token_valid(self, token_data: dict[str, Any] | None) -> bool:
        if not token_data or "access_token" not in token_data:
            return False
        expires_at = self._parse_datetime(token_data.get("expires_at"))
        if not expires_at:
            return False
        return datetime.now(timezone.utc) < expires_at - timedelta(minutes=1)

    def _finalize_token_payload(self, payload: dict[str, Any], scopes: list[str]) -> dict[str, Any]:
        expires_in = int(payload.get("expires_in", 0))
        if expires_in:
            payload["expires_at"] = (
                datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            ).isoformat()
        payload["scopes"] = scopes
        return payload

    def _persist_token(self, token_data: dict[str, Any]) -> None:
        if not self.secure_config:
            return
        data = self.secure_config.load() or {}
        data[self.TOKEN_CACHE_KEY] = token_data
        if self.client_id:
            data[self.CLIENT_ID_KEY] = self.client_id
        if self.client_secret:
            data[self.CLIENT_SECRET_KEY] = self.client_secret
        google_config = data.get(self.GOOGLE_CONFIG_KEY)
        if isinstance(google_config, dict):
            google_config["token_value"] = token_data.get("access_token")
            google_config["token_timestamp"] = token_data.get("expires_at")
            google_config.setdefault("client_id", self.client_id)
            data[self.GOOGLE_CONFIG_KEY] = google_config
        self.secure_config.save(data)

    def _normalize_scopes(self, scopes: Any) -> list[str] | None:
        if scopes is None:
            return None
        if isinstance(scopes, str):
            scopes = [scope.strip() for scope in scopes.split(" ") if scope.strip()]
        return [str(scope) for scope in scopes if scope]

    def _parse_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                return None
        return None

    def _safe_json(self, response: requests.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except Exception:
            data = {}
        if not isinstance(data, dict):
            return {}
        return data
