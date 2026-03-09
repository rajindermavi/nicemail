from email.message import EmailMessage

import pytest

from send.transport.google_transport import GoogleTransport


class DummyResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = str(payload)

    def json(self):
        return self._payload



def test_google_transport_raises_on_http_error(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return DummyResponse(400, {"error": "bad"})

    monkeypatch.setattr("send.transport.google_transport.requests.post", fake_post)

    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["To"] = "dest@example.com"
    msg.set_content("hi")

    transport = GoogleTransport("token-123", "sender@example.com")

    with pytest.raises(RuntimeError):
        transport.send_email(msg)


def test_connect_with_oauth_uses_access_token_and_config():
    cfg = {
        "google_email_address": "user@example.com",
        "google_api_config": {
            "host": "example.googleapis.com",
        },
    }

    transport = GoogleTransport.connect_with_oauth(cfg, access_token="token-xyz")

    assert isinstance(transport, GoogleTransport)
    assert transport._host == "example.googleapis.com"
    assert transport._from_address == "user@example.com"
