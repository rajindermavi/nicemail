# Nicemail
**Nicemail** is a small, explicit email-sending library.

```python
from nicemail import EmailClient
```

Nicemail is the public API; `send` is the internal engine.
Advanced users may import from `send`, but it is not the recommended API.

Keyring note:
If keyring is unavailable, you'll be prompted for a passphrase on first use.
The passphrase is only used to derive the encryption key.
