from email.message import EmailMessage
from typing import Literal

from send.transport.ms_graph import GraphMailClient
#from send.transport.google_api import GoogleMailClient

Backend = Literal["ms_graph", "google_api"]

def send(cfg: dict, msg: EmailMessage, backend: Backend, **kw) -> None:
    if backend == "ms_graph":
        GraphMailClient.send_email(cfg, msg, **kw)
    #elif backend == "google_api":
    #    GoogleMailClient.send_email(cfg, msg, **kw)
    else:
        raise ValueError(f"Unknown backend: {backend}")
