from __future__ import annotations

import os
from pathlib import Path

from nicemail import EmailClient


def _pick_latest(paths: set[Path]) -> Path | None:
    if not paths:
        return None
    return max(paths, key=lambda path: path.stat().st_mtime)


def main() -> int:
    to_address = "recipient@example.com"
    from_address = "sender@example.com"
    subject = "Hello from Nicemail (dry run)"
    body = "This is a dry-run email."

    out_dir = Path("dry_run_out")
    out_dir.mkdir(parents=True, exist_ok=True)

    client = EmailClient(
        backend="dry_run",
        out_dir=out_dir,
        passphrase=os.getenv("NICEMAIL_PASSPHRASE"),
    )

    message = client.message(
        to=to_address,
        subject=subject,
        body_text=body,
        from_address=from_address,
    )
    print(f"Built message: subject={message.get('Subject')!r}")

    before_eml = set(out_dir.glob("*.eml"))
    before_json = set(out_dir.glob("*.json"))

    client.send(
        to=to_address,
        subject=subject,
        body_text=body,
        from_address=from_address,
    )

    new_eml = set(out_dir.glob("*.eml")) - before_eml
    new_json = set(out_dir.glob("*.json")) - before_json

    eml_path = _pick_latest(new_eml)
    json_path = _pick_latest(new_json)

    print(f"Dry run output directory: {out_dir.resolve()}")
    if eml_path:
        print(f"eml: {eml_path.resolve()}")
    if json_path:
        print(f"metadata: {json_path.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
