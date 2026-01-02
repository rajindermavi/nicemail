from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .env import Environment


@dataclass(frozen=True)
class RuntimeContext:
    app_name: str = "Outbox"
    env: Environment = Environment.PRODUCTION

    # Optional: isolate multiple independent configurations (per client/mailbox)
    profile: str = "default"

    # Optional: hard override all platformdirs roots (useful for tests)
    root_override: Optional[Path] = None

    # Env var names (host can change if desired)
    env_var: str = "OUTBOX_ENV"
    profile_var: str = "OUTBOX_PROFILE"
    root_var: str = "OUTBOX_DIR"


def get_runtime_context(
    *,
    app_name: str = "Outbox",
    env: Environment | str | None = None,
    profile: str | None = None,
    root_override: Path | None = None,
    env_var: str = "OUTBOX_ENV",
    profile_var: str = "OUTBOX_PROFILE",
    root_var: str = "OUTBOX_DIR",
) -> RuntimeContext:
    resolved_env = env if isinstance(env, Environment) else Environment.parse(env)  # type: ignore[arg-type]
    if resolved_env is None:
        resolved_env = Environment.parse(os.getenv(env_var)) or Environment.PRODUCTION

    resolved_profile = profile or os.getenv(profile_var) or "default"

    resolved_root = root_override
    if resolved_root is None:
        root_str = (os.getenv(root_var) or "").strip()
        resolved_root = Path(root_str).expanduser() if root_str else None

    return RuntimeContext(
        app_name=app_name,
        env=resolved_env,
        profile=resolved_profile,
        root_override=resolved_root,
        env_var=env_var,
        profile_var=profile_var,
        root_var=root_var,
    )
