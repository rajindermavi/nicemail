import pytest

from send.client import EmailClient


def test_message_uses_configured_from_and_builder(monkeypatch, tmp_path):
    monkeypatch.setenv("NICEMAIL_DIR", str(tmp_path))

    client = EmailClient(
        msal_config={
            "email_address": "sender@example.com",
            "client_id": "client-123",
            "authority": "organization",
        },
        backend="ms_graph",
        key_policy={"prefer_keyring": False, "allow_passphrase_fallback": True},
        passphrase="pw",
    )

    msg = client.message(
        to=["dest@example.com", "Another <another@example.com>"],
        cc="cc@example.com",
        bcc="bcc@example.com",
        subject="Hi",
        body_text="Body text",
    )

    assert msg["From"] == "sender@example.com"
    assert msg["To"] == "dest@example.com, Another <another@example.com>"
    assert msg["Cc"] == "cc@example.com"
    assert msg["Bcc"] == "bcc@example.com"
    assert msg["Subject"] == "Hi"
    assert msg.get_content().strip() == "Body text"


def test_message_allows_override_from_and_attachments(monkeypatch, tmp_path):
    monkeypatch.setenv("NICEMAIL_DIR", str(tmp_path))

    attachment_path = tmp_path / "sample.txt"
    attachment_path.write_text("sample", encoding="utf-8")

    client = EmailClient(
        backend="google_api",
        key_policy={"prefer_keyring": False, "allow_passphrase_fallback": True},
        passphrase="pw",
    )

    msg = client.message(
        from_address="override@example.com",
        to="dest@example.com",
        subject="Attachment",
        body_text="See attachment",
        attachments=[attachment_path],
    )

    assert msg["From"] == "override@example.com"
    attachments = list(msg.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "sample.txt"
    assert attachments[0].get_payload(decode=True) == b"sample"


def test_message_requires_from(monkeypatch, tmp_path):
    monkeypatch.setenv("NICEMAIL_DIR", str(tmp_path))

    client = EmailClient(
        backend="dry_run",
        key_policy={"prefer_keyring": False, "allow_passphrase_fallback": True},
        passphrase="pw",
    )

    with pytest.raises(ValueError):
        client.message(to="dest@example.com", body_text="hi")
