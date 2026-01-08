from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from send.client import EmailClient
from send.runtime.paths import resolve_dry_run_out_dir


def _parse_addresses(value: str | None) -> list[str] | None:
    if not value:
        return None
    parts = [part.strip() for part in value.split(",") if part.strip()]
    return parts or None


def _pick_latest(paths: set[Path]) -> Path | None:
    if not paths:
        return None
    return max(paths, key=lambda path: path.stat().st_mtime)


def _snapshot_outputs(out_dir: Path) -> tuple[set[Path], set[Path]]:
    return set(out_dir.glob("*.eml")), set(out_dir.glob("*.json"))


def _resolve_from_address(value: str | None) -> str:
    from_value = value or os.getenv("NICEMAIL_FROM") or os.getenv("NICEMAIL_EMAIL")
    if not from_value:
        raise ValueError("from address is required; provide --from or set NICEMAIL_FROM.")
    return from_value


def _resolve_required(value: str | None, env_name: str, label: str) -> str:
    resolved = value or os.getenv(env_name)
    if not resolved:
        raise ValueError(f"{label} is required; provide --{label} or set {env_name}.")
    return resolved


def _resolve_passphrase() -> str | None:
    return os.getenv("NICEMAIL_PASSPHRASE")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nicemail", description="Nicemail command-line interface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dry_run = subparsers.add_parser("dry-run", help="Write .eml and metadata files without sending")
    dry_run.add_argument("--to", required=True, help="Recipient email address (comma-separated allowed)")
    dry_run.add_argument("--subject", required=True, help="Email subject")
    dry_run.add_argument("--body", required=True, help="Plain-text body")
    dry_run.add_argument("--from", dest="from_address", help="From email address")
    dry_run.add_argument("--out-dir", help="Directory for dry-run output files")

    send_cmd = subparsers.add_parser("send", help="Send a real email via a provider backend")
    send_cmd.add_argument("--backend", required=True, choices=["ms_graph", "google"], help="Provider backend")
    send_cmd.add_argument("--to", required=True, help="Recipient email address (comma-separated allowed)")
    send_cmd.add_argument("--subject", required=True, help="Email subject")
    send_cmd.add_argument("--body", required=True, help="Plain-text body")
    send_cmd.add_argument("--cc", help="CC recipients (comma-separated)")
    send_cmd.add_argument("--bcc", help="BCC recipients (comma-separated)")
    send_cmd.add_argument("--email", help="Sender email address (defaults to NICEMAIL_EMAIL)")
    send_cmd.add_argument("--client-id", help="OAuth client ID (defaults to NICEMAIL_CLIENT_ID)")
    send_cmd.add_argument("--authority", help="MS Graph authority: organization|consumer")
    send_cmd.add_argument("--from", dest="from_address", help="Optional From override")

    return parser


def _run_dry_run(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir) if args.out_dir else resolve_dry_run_out_dir()
    out_dir = out_dir.expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    before_eml, before_json = _snapshot_outputs(out_dir)

    client = EmailClient(
        backend="dry_run",
        out_dir=out_dir,
        passphrase=_resolve_passphrase(),
    )

    from_address = _resolve_from_address(args.from_address)
    to_addresses = _parse_addresses(args.to)

    client.send(
        to=to_addresses,
        subject=args.subject,
        body_text=args.body,
        from_address=from_address,
    )

    after_eml, after_json = _snapshot_outputs(out_dir)
    new_eml = after_eml - before_eml
    new_json = after_json - before_json

    eml_path = _pick_latest(new_eml)
    json_path = _pick_latest(new_json)

    if not eml_path:
        raise RuntimeError("dry-run did not produce a .eml output file.")
    if not json_path:
        raise RuntimeError("dry-run did not produce a metadata output file.")

    print(f"dry-run output dir: {out_dir.resolve()}")
    print(f"eml: {eml_path.resolve()}")
    print(f"metadata: {json_path.resolve()}")

    return 0


def _run_send(args: argparse.Namespace) -> int:
    backend = "google_api" if args.backend == "google" else args.backend

    email_address = _resolve_required(args.email, "NICEMAIL_EMAIL", "email")
    client_id = _resolve_required(args.client_id, "NICEMAIL_CLIENT_ID", "client-id")
    authority = args.authority or os.getenv("NICEMAIL_AUTHORITY")

    client = EmailClient(
        backend=backend,
        passphrase=_resolve_passphrase(),
    )

    if backend == "ms_graph":
        client.update_msal(
            email_address=email_address,
            client_id=client_id,
            authority=authority or "organization",
        )
    else:
        client.update_google_api(
            email_address=email_address,
            client_id=client_id,
        )

    print("This will prompt for device code if needed.")

    client.send(
        to=_parse_addresses(args.to),
        cc=_parse_addresses(args.cc),
        bcc=_parse_addresses(args.bcc),
        subject=args.subject,
        body_text=args.body,
        from_address=args.from_address,
    )

    print("Send complete.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "dry-run":
            return _run_dry_run(args)
        if args.command == "send":
            return _run_send(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
