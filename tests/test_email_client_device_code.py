import pytest

from send.client import EmailClient


class DummySecureConfig:
    def __init__(self, initial: dict | None = None) -> None:
        self._data = dict(initial or {})

    def load(self) -> dict:
        return dict(self._data)

    def save(self, data: dict) -> None:
        self._data = dict(data)


def test_device_code_routes_to_msal(monkeypatch, tmp_path):
    captured: dict = {}
    monkeypatch.setenv("NICEMAIL_DIR", str(tmp_path))

    def fake_show(msg):
        captured["show_called"] = True
        captured["show_msg"] = msg

    class FakeProvider:
        def __init__(self, secure_config=None, authority=None, show_message=None, client_id=None):
            captured["secure_config"] = secure_config
            captured["authority"] = authority
            captured["show_message"] = show_message
            captured["client_id"] = client_id

        def acquire_token(self, interactive=True, scopes=None):
            captured["interactive"] = interactive
            captured["scopes"] = scopes
            return "ms-token"

    monkeypatch.setattr("send.client.MSalDeviceCodeTokenProvider", FakeProvider)

    client = EmailClient(
        msal_config={
            "email_address": "user@example.com",
            "client_id": "client-123",
            "authority": "organization",
        },
        backend="ms_graph",
        key_policy={"prefer_keyring": False, "allow_passphrase_fallback": True},
        passphrase="pw",
    )
    client.secure_config = DummySecureConfig()

    token = client.device_code(interactive=False, scopes=["scope-a"], show_message=fake_show)

    assert token == "ms-token"
    assert captured["interactive"] is False
    assert captured["scopes"] == ["scope-a"]
    assert captured["authority"] == "organization"
    assert captured["client_id"] == "client-123"
    assert captured["show_message"] is fake_show
    assert isinstance(captured["secure_config"], DummySecureConfig)


def test_device_code_routes_to_google(monkeypatch, tmp_path):
    captured: dict = {}
    monkeypatch.setenv("NICEMAIL_DIR", str(tmp_path))

    class FakeProvider:
        def __init__(
            self,
            secure_config=None,
            client_id=None,
            client_secret=None,
            scopes=None,
            show_message=None,
        ):
            captured["secure_config"] = secure_config
            captured["client_id"] = client_id
            captured["client_secret"] = client_secret
            captured["init_scopes"] = scopes
            captured["show_message"] = show_message

        def acquire_token(self, interactive=True, scopes=None):
            captured["interactive"] = interactive
            captured["scopes"] = scopes
            return "google-token"

    monkeypatch.setattr("send.client.GoogleDeviceCodeTokenProvider", FakeProvider)

    client = EmailClient(
        google_api_config={
            "email_address": "user@example.com",
            "client_id": "gid-123",
            "scopes": ["existing-scope"],
        },
        backend="google_api",
        key_policy={"prefer_keyring": False, "allow_passphrase_fallback": True},
        passphrase="pw",
    )
    client.secure_config = DummySecureConfig({"google_client_secret": "secret-xyz"})

    def stub_show(msg):
        captured["show_called"] = True
        captured["show_msg"] = msg

    token = client.device_code(scopes=["override-scope"], show_message=stub_show)

    assert token == "google-token"
    assert captured["client_id"] == "gid-123"
    assert captured["client_secret"] == "secret-xyz"
    assert captured["init_scopes"] == ["override-scope"]
    assert captured["scopes"] == ["override-scope"]
    assert captured["interactive"] is True
    assert captured["show_message"] is stub_show
    assert isinstance(captured["secure_config"], DummySecureConfig)


def test_device_code_warns_for_dry_run(monkeypatch, tmp_path):
    monkeypatch.setenv("NICEMAIL_DIR", str(tmp_path))
    client = EmailClient(
        backend="dry_run",
        key_policy={"prefer_keyring": False, "allow_passphrase_fallback": True},
        passphrase="pw",
    )
    client.secure_config = DummySecureConfig()

    with pytest.warns(RuntimeWarning):
        token = client.device_code()

    assert token is None
