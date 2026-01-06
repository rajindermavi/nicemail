from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import requests

from send.credentials.store import SecureConfig

DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class GoogleDeviceCodeTokenProvider:
    """
    Handles access token acquisition for Google APIs using the device authorization flow.
    """

    TOKEN_CACHE_KEY = "google_token_cache"
    GOOGLE_CONFIG_KEY = "google_api_config"
    CLIENT_ID_KEY = "google_client_id"
    CLIENT_SECRET_KEY = "google_client_secret"
    EMAIL_KEY = "google_email_address"

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
                "client_id is required for Google device code flow. "
                "Provide it directly or store it in SecureConfig under 'google_client_id' or 'google_api_config.client_id'."
            )

        self._token = self._load_token(self._config_snapshot)

    def acquire_token(self, interactive: bool = True, scopes: list[str] | None = None) -> str:
        """
        Get a valid Google API access token.

        1. Use cached token if still valid.
        2. Refresh using refresh_token if available.
        3. If allowed, run device code flow to obtain a new token.
        """
        resolved_scopes = self._normalize_scopes(scopes) or self.scopes or DEFAULT_SCOPES
        self.scopes = resolved_scopes

        if self._is_token_valid(self._token):
            return self._token["access_token"]  # type: ignore[index]

        refreshed = None
        if self._token and self._token.get("refresh_token"):
            refreshed = self._refresh_token(self._token["refresh_token"], resolved_scopes)
            if refreshed:
                return refreshed

        if not interactive:
            raise RuntimeError("Could not obtain Google access token and interactive auth is disabled.")

        flow = self._initiate_device_flow(resolved_scopes)
        token_data = self._poll_for_token(flow, resolved_scopes)
        self._token = token_data
        self._persist_token(token_data)
        return token_data["access_token"]

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

    def _initiate_device_flow(self, scopes: list[str]) -> dict[str, Any]:
        payload = {"client_id": self.client_id, "scope": " ".join(scopes)}
        response = requests.post(DEVICE_CODE_URL, data=payload, timeout=10)
        if response.status_code != 200:
            raise RuntimeError(f"Failed to initiate Google device flow: {response.text}")

        flow = self._safe_json(response)
        if "device_code" not in flow:
            raise RuntimeError(f"Invalid device flow response: {flow!r}")

        self._display_message(flow)
        return flow

    def _poll_for_token(self, flow: dict[str, Any], scopes: list[str]) -> dict[str, Any]:
        interval = max(int(flow.get("interval", 5)), 1)
        expires_in = int(flow.get("expires_in", 600))
        deadline = time.monotonic() + expires_in

        payload: dict[str, Any] = {
            "client_id": self.client_id,
            "device_code": flow["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }
        if self.client_secret:
            payload["client_secret"] = self.client_secret

        while time.monotonic() < deadline:
            response = requests.post(TOKEN_URL, data=payload, timeout=10)
            data = self._safe_json(response)

            if response.status_code == 200 and "access_token" in data:
                return self._finalize_token_payload(data, scopes)

            error = data.get("error")
            if error == "authorization_pending":
                time.sleep(interval)
                continue
            if error == "slow_down":
                interval += 5
                time.sleep(interval)
                continue
            if error == "access_denied":
                raise RuntimeError("User denied the Google device authorization request.")
            if error == "expired_token":
                break
            if response.status_code >= 400:
                raise RuntimeError(f"Google token endpoint returned error: {data}")

        raise RuntimeError("Google device authorization timed out before completion.")

    def _refresh_token(self, refresh_token: str, scopes: list[str]) -> str | None:
        payload: dict[str, Any] = {
            "client_id": self.client_id,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        if self.client_secret:
            payload["client_secret"] = self.client_secret

        response = requests.post(TOKEN_URL, data=payload, timeout=10)
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

    def _finalize_token_payload(self, payload: dict[str, Any], scopes: list[str]) -> dict[str, Any]:
        expires_in = int(payload.get("expires_in", 0))
        if expires_in:
            payload["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
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

    def _display_message(self, flow: dict[str, Any]) -> None:
        if callable(self._show_message):
            self._show_message(flow)
            return

        verification_url = (
            flow.get("verification_uri_complete")
            or flow.get("verification_url")
            or flow.get("verification_uri")
        )
        user_code = flow.get("user_code")
        if verification_url and user_code:
            text = f"Visit {verification_url} and enter code: {user_code}"
        elif verification_url:
            text = f"Visit {verification_url} to authorize this device."
        else:
            text = str(flow)

        print(text, flush=True)

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
