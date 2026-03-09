# System Contracts

Authoritative source for behavioral guarantees across all subsystems.
For design intent and rationale, see the per-module docs.

---

## Transport

All transports expose:

    send_email(msg: EmailMessage) -> None

- The message is assumed to be complete and valid.
- The transport must not mutate the `EmailMessage`.
- Each `send_email` call is independent; callers should not assume shared state between calls.
- Transports do not acquire tokens; callers supply them explicitly.
- On failure, raises `TransportError` (or a subclass). Provider-specific exceptions may be wrapped.
- Transports do not retry internally.

---

## Message

The output of `message/` is always:

    email.message.EmailMessage

- The message handed to a transport is assumed to be complete, valid, and ready to send.
- No transport should modify message contents.

---

## Auth

Each token provider exposes a single entry point:

    acquire_token(self) -> str

- Returns a valid access token string.
- Initiates device-code authentication if no valid token exists.
- Refreshes an expired token when possible.
- Raises on unrecoverable authentication failure.
- Token cache loading/saving is injected; providers do not hard-code persistence.

---

## Credentials

### Key Modes

Exactly two key strategies are supported:

**1. Keyring mode** — when `prefer_keyring == True` and a system keyring is available and writable:
- A random encryption key is generated and stored in the OS keyring.
- The encrypted config file is written to disk.

**2. User-supplied key mode** — when `prefer_keyring == False` or keyring access fails, and `allow_passphrase_fallback == True`:
- The user must provide a key or passphrase at runtime.
- A cryptographic key is derived in memory; no key material is persisted.
- The encrypted config file is written to disk.

### Failure Condition

If keyring is unavailable and `allow_passphrase_fallback == False`:
- `SecureConfig` raises an explicit error.
- No data is written.
- There is no silent fallback.

If keyring is unavailable and `allow_passphrase_fallback` is not explicitly set, passphrase fallback is enabled with a warning so first-run does not fail silently.

### Explicitly Unsupported Modes

- Plaintext credential storage
- Encrypted file + key stored in a file
- Automatic downgrade from keyring to file-based keys
- Backup key files
- Mixed or hybrid key storage schemes

If neither of the two supported modes is possible, the operation fails.

---

## Common / Dependency Direction

`common/` may not depend on any other internal package in this library.

Dependencies must flow outward only:
- `common/` → no internal dependencies
- All other packages may freely depend on `common/`

Code in `common/` must not import from `credentials/`, `auth/`, `transport/`, `message/`, or any other internal package.

---

## Testing

Tests verify public contracts, not implementation details.

- A test that requires internet access is invalid.
- A test that requires a real email account is invalid.
- A test that breaks when refactoring internals is invalid.
