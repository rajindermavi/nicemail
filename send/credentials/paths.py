from __future__ import annotations

from pathlib import Path
from send.runtime.paths import AppPaths

KEY_FILENAME = "encryption.key"
CONFIG_FILENAME = "config.enc"

def get_key_path(paths: AppPaths) -> Path:
    # keys belong in durable state (not config)
    return paths.state_dir / KEY_FILENAME

def get_encrypted_config_path(paths: AppPaths) -> Path:
    # encrypted config belongs in config_dir
    return paths.config_dir / CONFIG_FILENAME