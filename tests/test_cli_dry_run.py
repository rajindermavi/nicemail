import os
import subprocess
import sys


def test_cli_dry_run_creates_outputs(tmp_path):
    out_dir = tmp_path / "dry_run"
    config_dir = tmp_path / "config"

    env = os.environ.copy()
    env["NICEMAIL_DIR"] = str(config_dir)
    env["NICEMAIL_PASSPHRASE"] = "test-passphrase"

    cmd = [
        sys.executable,
        "-m",
        "send.cli",
        "dry-run",
        "--to",
        "to@example.com",
        "--from",
        "from@example.com",
        "--subject",
        "CLI Dry Run",
        "--body",
        "Hello from the CLI",
        "--out-dir",
        str(out_dir),
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
    assert list(out_dir.glob("*.eml"))
    assert list(out_dir.glob("*.json"))
