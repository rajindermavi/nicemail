# Nicemail
**Nicemail** is a small, explicit email-sending library.

```python
from nicemail import EmailClient
```

Nicemail is the public API; `send` is the internal engine.
Advanced users may import from `send`, but it is not the recommended API.

## Quickstart
```python
from nicemail import EmailClient

client = EmailClient(backend="dry_run", out_dir="dry_run_out")
client.send(
    to="you@example.com",
    subject="Hello from Nicemail",
    body_text="This is a dry-run message.",
    from_address="me@example.com",
)
```

## CLI
```bash
nicemail dry-run --to you@example.com --from me@example.com --subject "Hello" --body "Test" --out-dir ./dry_run_out
nicemail send --backend ms_graph --to you@example.com --subject "Hello" --body "Hello from Nicemail" --email me@example.com --client-id YOUR_CLIENT_ID
```

Keyring note:
If keyring is unavailable, you'll be prompted for a passphrase on first use.
The passphrase is only used to derive the encryption key.
