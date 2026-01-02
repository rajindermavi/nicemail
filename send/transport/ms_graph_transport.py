from __future__ import annotations

import inspect
import requests
import base64
from typing import Optional, Dict
from email.message import EmailMessage
from email.utils import getaddresses

from send.auth.msal_device_code import MSalDeviceCodeTokenProvider
from credentials.store import SecureConfig

from send.logging import get_logger

logger = get_logger(__name__)

class GraphMailClient:
    GRAPH_SENDMAIL_URL = "https://graph.microsoft.com/v1.0/me/sendMail"
    GRAPH_MAIL_SCOPES = ["https://graph.microsoft.com/Mail.Send"]

    def __init__(self, access_token: str, from_address: str) -> None:
        self._access_token = access_token
        self._from_address = from_address

        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def send_message(self, msg: EmailMessage) -> None:
        logger.info(f'Start. Class: {self.__class__.__name__}. Method: {inspect.currentframe().f_code.co_name}.')
        payload = self._emailmessage_to_graph_payload(msg)

        resp = requests.post(
            self.GRAPH_SENDMAIL_URL,
            headers=self._headers,
            json=payload,
            timeout=30,
        )

        if resp.status_code not in (200, 202):
            raise RuntimeError(
                f"Graph sendMail failed: {resp.status_code} {resp.text}"
            )

    def __enter__(self) -> "GraphMailClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        # nothing to close (HTTP)
        return None

    @classmethod
    def connect_with_oauth(
        cls,
        cfg: Dict,
        token_provider: Optional[MSalDeviceCodeTokenProvider] = None,
        interactive: bool = True,
        secure_config: SecureConfig | None = None,
    ) -> "GraphMailClient":
        """
        Create and return a GraphMailClient using OAuth2.

        - Acquires an access token (silent + optional device-code interactive).
        - Prepares Graph sendMail client.
        - Raises RuntimeError if token or config is invalid.

        Usage:

            with GraphMailClient.connect_with_oauth(cfg, token_provider) as graph:
                graph.send_message(msg)
        """
        authority_value = cfg.get("ms_authority") if isinstance(cfg, dict) else None
        if token_provider is None:
            token_provider = MSalDeviceCodeTokenProvider(
                secure_config=secure_config,
                authority=authority_value,
            )
        elif authority_value:
            token_provider.set_authority(authority_value)

        from_address = cfg.get("ms_email_address") or getattr(
            token_provider, "ms_username", None
        )

        if not from_address:
            raise ValueError("MS email address is required to send mail via Graph.")

        access_token = token_provider.acquire_token(
            interactive=interactive,
            scopes=cls.GRAPH_MAIL_SCOPES,
        )

        return cls(
            access_token=access_token,
            from_address=from_address,
        )

    @classmethod
    def send_email(
        cls,
        cfg: Dict,
        msg: EmailMessage,
        token_provider: Optional[MSalDeviceCodeTokenProvider] = None,
        interactive: bool = True,
        secure_config: SecureConfig | None = None,
    ) -> None:
        """
        Convenience wrapper:
        - Connects via Microsoft Graph
        - Sends a single EmailMessage
        - Cleans up

        `msg["From"]` will be set to cfg["ms_email_address"] if not already set.
        """
        if "ms_token" in cfg:
            cfg = cfg.get("ms_token") or {}
        if not cfg:
            raise ValueError("Missing ms_token configuration for MS Graph send.")

        if not msg.get("From"):
            msg["From"] = cfg.get("ms_email_address")

        with cls.connect_with_oauth(
            cfg,
            token_provider,
            interactive=interactive,
            secure_config=secure_config,
        ) as graph:
            graph.send_message(msg)

    def _emailmessage_to_graph_payload(self, msg: EmailMessage) -> Dict:
        def _body_content(msg: EmailMessage) -> tuple[str, str]:
            """
            Returns (content, graph_content_type) where graph_content_type is
            either "Text" or "HTML".
            """
            # Prefer a plain part, fall back to HTML, then to the raw content.
            preferred_part = msg.get_body(preferencelist=("plain", "html"))
            if preferred_part:
                content_type = preferred_part.get_content_type()
                content = preferred_part.get_content()
            elif not msg.is_multipart():
                content_type = msg.get_content_type()
                content = msg.get_content()
            else:
                # Multipart without a text part; send an empty text body.
                content_type = "text/plain"
                content = ""

            graph_type = "HTML" if content_type == "text/html" else "Text"
            return content or "", graph_type

        to_addrs = []
        for _, addr in getaddresses(msg.get_all("To") or []):
            if addr:
                to_addrs.append({"emailAddress": {"address": addr}})

        body_text, body_type = _body_content(msg)

        payload = {
            "message": {
                "subject": msg.get("Subject", ""),
                "body": {
                    "contentType": body_type,
                    "content": body_text,
                },
                "from": {
                    "emailAddress": {"address": msg.get("From") or self._from_address}
                },
                "toRecipients": to_addrs,
            }
        }

        # Attachments (optional, but important for InvoiceMailer)
        attachments = []
        for part in msg.iter_attachments():
            filename = part.get_filename()
            content = part.get_payload(decode=True)
            if filename and content:
                attachments.append({
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": filename,
                    "contentBytes": base64.b64encode(content).decode("utf-8"),
                })

        if attachments:
            payload["message"]["attachments"] = attachments

        return payload
