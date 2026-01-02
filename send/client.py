from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from send.credentials.models import KeyPolicy, MSalConfig, GoogleAPIConfig


class EmailClient:
    def __init__(
        self,
        *,
        msal_config: Mapping[str, Any] | None = None,
        google_api_config: Mapping[str, Any] | None = None,
        key_policy: Mapping[str, Any] | None = None,
    ) -> None:

        self.msal_config: MSalConfig | None = (
            self.update_msal(msal_config) if msal_config else None
        )
        self.google_api_config: GoogleAPIConfig | None = (
            self.update_google_api(google_api_config) if google_api_config else None
        )
        self.key_policy: KeyPolicy = self.update_key_policy(key_policy)

    def update_msal(
        self, config: Mapping[str, Any] | None = None, **kwargs: Any
    ) -> MSalConfig:
        data: dict[str, Any] = {}
        if config:
            data.update(config)
        data.update(kwargs)

        required = ("host", "port", "username", "email_address")
        missing = [field for field in required if not data.get(field)]
        if missing:
            raise ValueError(
                f"Missing required MSAL config fields: {', '.join(missing)}"
            )

        msal_config = MSalConfig(
            host=str(data["host"]),
            port=int(data["port"]),
            starttls=bool(data.get("starttls", False)),
            username=str(data["username"]),
            email_address=str(data["email_address"]),
            client_id=data.get("client_id"),
            authority=data.get("authority", "organization"),
        )
        self.msal_config = msal_config

    def update_google_api(
        self, config: Mapping[str, Any] | None = None, **kwargs: Any
    ) -> GoogleAPIConfig:
        data: dict[str, Any] = {}
        if config:
            data.update(config)
        data.update(kwargs)

        required = ("host", "port", "username", "password", "email_address")
        missing = [field for field in required if not data.get(field)]
        if missing:
            raise ValueError(
                f"Missing required SMTP config fields: {', '.join(missing)}"
            )

        google_api_config = GoogleAPIConfig(
            host=str(data["host"]),
            port=int(data["port"]),
            use_tls=bool(data.get("use_tls", True)),
            email_address=str(data["email_address"]),
            client_id=str(data["client_id"]),
        )
        self.google_api_config = google_api_config

    def update_key_policy(
        self, policy: Mapping[str, Any] | None = None, **kwargs: Any
    ) -> KeyPolicy:
        data: dict[str, Any] = {}
        if policy:
            data.update(policy)
        data.update(kwargs)

        prefer_keyring = bool(data.get("prefer_keyring", True))
        allow_passphrase_fallback = bool(data.get("allow_passphrase_fallback", False))

        self.key_policy = KeyPolicy(
            prefer_keyring=prefer_keyring,
            allow_passphrase_fallback=allow_passphrase_fallback,
        )

    def send(
        self,
        to: list[str],
        subject: str,
        body_html: str | None = None,
        body_text: str | None = None,
        attachments: list[Path] | None = None,
    ):
        attachments = attachments or []
        pass

