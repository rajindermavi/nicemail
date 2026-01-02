
from __future__ import annotations

from typing import Iterable, Any, Callable

try:
    from tkinter import messagebox  # GUI popup for device-code instructions
except Exception:  # pragma: no cover - fallback for non-GUI contexts
    messagebox = None

import msal

from send.credentials.store import SecureConfig

GRAPH_MAIL_SCOPES = ["https://graph.microsoft.com/Mail.Send"]
ORG_AUTHORITY = "https://login.microsoftonline.com/organizations"
CONSUMER_AUTHORITY = "https://login.microsoftonline.com/consumers"
CLIENT_ID = ''

class MSalDeviceCodeTokenProvider:
    """
    Handles access token acquisition for a single mailbox using MSAL Device Code Flow.
    """

    TOKEN_CACHE_KEY = "ms_token_cache"
    MS_USERNAME_KEY = "ms_username"

    def __init__(self, secure_config: SecureConfig | None = None, authority: str | None = None, show_message: Callable[[object], None] | None = None) -> None:
        self.secure_config = secure_config
        self._show_message = show_message

        self._cache = msal.SerializableTokenCache()
        self._load_cache()

        self.authority = self.resolve_authority(authority)

        self._app = self._build_app()

    @staticmethod
    def resolve_authority(authority: str | None) -> str:
        if not authority:
            return ORG_AUTHORITY
        if authority.startswith("http"):
            return authority
        authority_key = authority.lower()
        if authority_key in ("organizations", "org", "work", "work/school", "work_school"):
            return ORG_AUTHORITY
        if authority_key in ("consumers", "consumer", "personal", "outlook"):
            return CONSUMER_AUTHORITY
        return ORG_AUTHORITY

    def _build_app(self) -> msal.PublicClientApplication:
        return msal.PublicClientApplication(
            client_id=CLIENT_ID,
            authority=self.authority,
            token_cache=self._cache,
        )

    def set_authority(self, authority: str | None) -> None:
        new_authority = self.resolve_authority(authority)
        if new_authority == getattr(self, "authority", None):
            return
        self.authority = new_authority
        self._app = self._build_app()

    def _load_cache(self) -> None:
        if self.secure_config:
            data = self.secure_config.load() or {}
            self.ms_username = data.get(self.MS_USERNAME_KEY)
            serialized_cache = data.get(self.TOKEN_CACHE_KEY)
            if serialized_cache:
                try:
                    self._cache.deserialize(serialized_cache)
                    return
                except Exception:
                    self._cache = msal.SerializableTokenCache()

    def _save_cache_if_changed(self) -> None:
        if self._cache.has_state_changed:
            serialized = self._cache.serialize()
            if self.secure_config:
                data = self.secure_config.load() or {}
                data[self.TOKEN_CACHE_KEY] = serialized
                # Also set a lightweight flag for UI display.
                if getattr(self, "ms_username", None):
                    data[self.MS_USERNAME_KEY] = self.ms_username
                self.secure_config.save(data)

    def acquire_token(self, interactive: bool = True, scopes: list[str] | None = None) -> str:
        """
        Get a valid access token for cfg.scopes.

        1. Try silent acquisition from cache.
        2. If not available and interactive=True, run device code flow.
        3. Save cache if changed.
        Raises RuntimeError if token cannot be obtained.
        """
        scopes = scopes or GRAPH_MAIL_SCOPES
        # Try silent first, using account matching the email (if any)
        accounts = self._app.get_accounts()
        account = accounts[0] if accounts else None
        #print(account)
        result = self._app.acquire_token_silent(scopes, account=account)
        #print(result)
        if not result and interactive:
            # Initiate device code flow
            flow = self._app.initiate_device_flow(scopes=scopes)
            if "user_code" not in flow:
                raise RuntimeError(f"Failed to initiate device code flow: {flow!r}")

            self._display_message(flow)

            # This call blocks until user completes auth or it times out.
            result = self._app.acquire_token_by_device_flow(flow)

        if not result or "access_token" not in result:
            err = None
            if isinstance(result, dict):
                err = result.get("error_description") or result.get("error")
            raise RuntimeError(f"Could not obtain access token. Details: {err!r}")

        # Capture username from the auth result so we can persist it with the cache.
        username = self._extract_username(result)
        if username:
            self.ms_username = username

        self._save_cache_if_changed()
        return result["access_token"]

    def _display_message(self, msg: object) -> None:
        """
        Show device-flow instructions.
        `msg` can be the flow dict or a plain string; callbacks get the raw object.
        """
        if callable(self._show_message):
            self._show_message(msg)
            return
        text = msg.get("message") if isinstance(msg, dict) else str(msg)
        if messagebox:
            messagebox.showinfo("Microsoft Sign-in", text)
            return
        print(text, flush=True)

    def _extract_username(self, result: dict) -> str | None:
        """
        Pull a username/email from an MSAL token result, if present.
        """
        if not isinstance(result, dict):
            return None
        claims = result.get("id_token_claims") or {}
        return (
            claims.get("preferred_username")
            or claims.get("upn")
            or result.get("username")
        )