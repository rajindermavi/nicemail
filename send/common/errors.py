from __future__ import annotations


class TransportError(RuntimeError):
    """Raised when a transport fails to deliver a message."""
