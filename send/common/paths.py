from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

KEY_FILENAME = "encryption.key"
CONFIG_FILENAME = "config.enc"


@dataclass(frozen=True)
class AppPaths:
    config_dir: Path   # encrypted config files
    state_dir: Path    # token caches, durable state, keys
    cache_dir: Path    # ephemeral cache
    logs_dir: Path     # logs

    def ensure(self) -> "AppPaths":
        for d in (self.config_dir, self.state_dir, self.cache_dir, self.logs_dir):
            d.mkdir(parents=True, exist_ok=True)
        return self


def get_key_path(paths: AppPaths) -> Path:
    # keys belong in durable state (not config)
    return paths.state_dir / KEY_FILENAME

def get_encrypted_config_path(paths: AppPaths) -> Path:
    # encrypted config belongs in config_dir
    return paths.config_dir / CONFIG_FILENAME
