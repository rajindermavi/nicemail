from datetime import datetime, timedelta, timezone

import pytest

from send.auth.google_device_code import (
    DEVICE_CODE_URL,
    TOKEN_URL,
    GoogleDeviceCodeTokenProvider,
)


class DummySecureConfig:
    def __init__(self, initial: dict | None = None) -> None:
        self._data = initial or {}

    def load(self) -> dict:
        return dict(self._data)

    def save(self, data: dict) -> None:
        self._data = dict(data)


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = str(payload)

    def json(self):
        return self._payload


def test_uses_cached_token_when_valid(monkeypatch):
    now = datetime.now(timezone.utc)
    cached = {
        "access_token": "cached-token",
        "expires_at": (now + timedelta(minutes=5)).isoformat(),
    }
    config = DummySecureConfig({"google_token_cache": cached, "google_client_id": "cid"})

    provider = GoogleDeviceCodeTokenProvider(
        secure_config=config,
        client_id="cid",
        scopes=["scope-a"],
    )

    token = provider.acquire_token(interactive=False)

    assert token == "cached-token"


def test_refreshes_expired_token(monkeypatch):
    now = datetime.now(timezone.utc)
    expired = {
        "access_token": "old-token",
        "refresh_token": "refresh-token",
        "expires_at": (now - timedelta(minutes=5)).isoformat(),
    }
    config = DummySecureConfig({"google_token_cache": expired, "google_client_id": "cid"})

    def fake_post(url, data=None, timeout=None):
        assert url == TOKEN_URL
        return FakeResponse(
            200,
            {
                "access_token": "new-token",
                "expires_in": 3600,
            },
        )

    monkeypatch.setattr("send.auth.google_device_code.requests.post", fake_post)

    provider = GoogleDeviceCodeTokenProvider(
        secure_config=config,
        client_id="cid",
        scopes=["scope-a"],
    )

    token = provider.acquire_token(interactive=False)

    assert token == "new-token"
    saved = config.load().get("google_token_cache", {})
    assert saved.get("access_token") == "new-token"
    assert saved.get("refresh_token") == "refresh-token"


def test_device_flow_happy_path(monkeypatch):
    config = DummySecureConfig({"google_client_id": "cid"})
    flow_response = {
        "device_code": "device-123",
        "user_code": "CODE-XYZ",
        "verification_url": "https://example.test/device",
        "expires_in": 120,
        "interval": 0,
    }
    token_calls = {"count": 0}

    def fake_post(url, data=None, timeout=None):
        if url == DEVICE_CODE_URL:
            return FakeResponse(200, flow_response)
        token_calls["count"] += 1
        if token_calls["count"] == 1:
            return FakeResponse(400, {"error": "authorization_pending"})
        return FakeResponse(
            200,
            {
                "access_token": "device-token",
                "refresh_token": "device-refresh",
                "expires_in": 600,
            },
        )

    monkeypatch.setattr("send.auth.google_device_code.requests.post", fake_post)
    monkeypatch.setattr("send.auth.google_device_code.time.sleep", lambda s: None)

    messages: list[dict] = []
    provider = GoogleDeviceCodeTokenProvider(
        secure_config=config,
        client_id="cid",
        scopes=["scope-a"],
        show_message=lambda msg: messages.append(msg),
    )

    token = provider.acquire_token()

    assert token == "device-token"
    assert messages and messages[0]["device_code"] == flow_response["device_code"]

    saved = config.load().get("google_token_cache", {})
    assert saved.get("refresh_token") == "device-refresh"
