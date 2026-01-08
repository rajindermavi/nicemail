# src/nicemail/runtime/env.py
from __future__ import annotations

from enum import Enum
from typing import Optional


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"

    @classmethod
    def parse(cls, value: str | None) -> Optional["Environment"]:
        if not value:
            return None
        v = value.strip().lower()
        if v in {"dev", "development"}:
            return cls.DEVELOPMENT
        if v in {"prod", "production"}:
            return cls.PRODUCTION
        if v in {"test", "testing"}:
            return cls.TEST
        return None
