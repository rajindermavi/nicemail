import pytest
from email.message import EmailMessage

from send.common.errors import TransportError
from send.transport.ms_graph_transport import MSGraphTransport


class DummyResponse:
    def __init__(self, status_code: int = 202, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


def _make_transport() -> MSGraphTransport:
    return MSGraphTransport(access_token="token-abc", from_address="sender@example.com")


def _capture_payload(monkeypatch) -> dict:
    captured: dict = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["payload"] = json
        return DummyResponse(202)

    monkeypatch.setattr("send.transport.ms_graph_transport.requests.post", fake_post)
    return captured


# ---------------------------------------------------------------------------
# payload structure
# ---------------------------------------------------------------------------

def test_to_only(monkeypatch):
    captured = _capture_payload(monkeypatch)
    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["To"] = "a@example.com"
    msg["Subject"] = "Hello"
    msg.set_content("body")

    _make_transport().send_email(msg)

    message = captured["payload"]["message"]
    assert message["toRecipients"] == [{"emailAddress": {"address": "a@example.com"}}]
    assert "ccRecipients" not in message
    assert "bccRecipients" not in message


def test_cc_included_in_payload(monkeypatch):
    captured = _capture_payload(monkeypatch)
    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["To"] = "a@example.com"
    msg["Cc"] = "b@example.com"
    msg.set_content("body")

    _make_transport().send_email(msg)

    message = captured["payload"]["message"]
    assert message["ccRecipients"] == [{"emailAddress": {"address": "b@example.com"}}]
    assert "bccRecipients" not in message


def test_bcc_included_in_payload(monkeypatch):
    captured = _capture_payload(monkeypatch)
    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["To"] = "a@example.com"
    msg["Bcc"] = "c@example.com"
    msg.set_content("body")

    _make_transport().send_email(msg)

    message = captured["payload"]["message"]
    assert message["bccRecipients"] == [{"emailAddress": {"address": "c@example.com"}}]
    assert "ccRecipients" not in message


def test_to_cc_bcc_all_present(monkeypatch):
    captured = _capture_payload(monkeypatch)
    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["To"] = "a@example.com, b@example.com"
    msg["Cc"] = "c@example.com"
    msg["Bcc"] = "d@example.com"
    msg.set_content("body")

    _make_transport().send_email(msg)

    message = captured["payload"]["message"]
    to_addrs = [r["emailAddress"]["address"] for r in message["toRecipients"]]
    assert sorted(to_addrs) == ["a@example.com", "b@example.com"]
    assert message["ccRecipients"] == [{"emailAddress": {"address": "c@example.com"}}]
    assert message["bccRecipients"] == [{"emailAddress": {"address": "d@example.com"}}]


def test_multiple_cc_recipients(monkeypatch):
    captured = _capture_payload(monkeypatch)
    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["To"] = "a@example.com"
    msg["Cc"] = "b@example.com, c@example.com"
    msg.set_content("body")

    _make_transport().send_email(msg)

    cc_addrs = [r["emailAddress"]["address"] for r in captured["payload"]["message"]["ccRecipients"]]
    assert sorted(cc_addrs) == ["b@example.com", "c@example.com"]


# ---------------------------------------------------------------------------
# error handling
# ---------------------------------------------------------------------------

def test_raises_transport_error_on_http_failure(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return DummyResponse(400, "Bad Request")

    monkeypatch.setattr("send.transport.ms_graph_transport.requests.post", fake_post)

    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["To"] = "a@example.com"
    msg.set_content("body")

    with pytest.raises(TransportError):
        _make_transport().send_email(msg)


# ---------------------------------------------------------------------------
# connect_with_oauth
# ---------------------------------------------------------------------------

def test_connect_with_oauth_raises_without_token():
    cfg = {"ms_email_address": "sender@example.com"}
    with pytest.raises(ValueError, match="access_token"):
        MSGraphTransport.connect_with_oauth(cfg, access_token=None)


def test_connect_with_oauth_raises_without_email():
    with pytest.raises(ValueError, match="email address"):
        MSGraphTransport.connect_with_oauth({}, access_token="token-abc")


def test_connect_with_oauth_returns_transport():
    cfg = {"ms_email_address": "sender@example.com"}
    transport = MSGraphTransport.connect_with_oauth(cfg, access_token="token-abc")
    assert isinstance(transport, MSGraphTransport)
    assert transport._from_address == "sender@example.com"
