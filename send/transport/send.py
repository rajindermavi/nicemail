from email.message import EmailMessage
from pathlib import Path

from send.common.config import Backend
from send.transport.dry_run_transport import DryRunTransport
from send.transport.google_transport import GoogleTransport
from send.transport.ms_graph_transport import MSGraphTransport


def send(
    cfg: dict,
    msg: EmailMessage,
    backend: Backend,
    *,
    out_dir: Path | None = None,
    access_token: str | None = None,
    write_metadata: bool = True,
) -> None:
    if backend == "ms_graph":
        with MSGraphTransport.connect_with_oauth(cfg, access_token=access_token) as transport:
            transport.send_email(msg)
    elif backend == "google_api":
        with GoogleTransport.connect_with_oauth(cfg, access_token=access_token) as transport:
            transport.send_email(msg)
    elif backend == "dry_run":
        if out_dir is None:
            raise ValueError("dry_run backend requires 'out_dir'.")
        with DryRunTransport(out_dir, write_metadata=write_metadata) as transport:
            transport.send_email(msg)
    else:
        raise ValueError(f"Unknown backend: {backend}")
