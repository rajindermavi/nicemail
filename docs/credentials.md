
# credentials/

This library intentionally favors simplicity and locality over maximal abstraction.

The credentials subsystem is designed for single-user or small-organization workflows, where the same runtime both configures and uses credentials. Models may therefore combine static configuration, cached runtime state, and token metadata in one place to reduce cognitive and persistence overhead.

This is not intended to be a general-purpose secret-management framework.


## Design Principles

- Prefer explicitness over indirection
- Prefer local encrypted storage over remote secret services
- Avoid premature abstraction (no provider registries, no layered adapters)
- Make the security boundary obvious
- Fail safely rather than silently weakening security
- Support headless / CLI / device-code flows
- Library-first: no global singletons, no hidden side effects

---

## Folder Overview

credentials/
├── paths.py
├── models.py
└── store.py



---

## `paths.py`

Defines **where encrypted credential data is stored**.

### Responsibilities

- Provide platform-appropriate storage locations
- Centralize all filesystem paths used by the credentials system
- Avoid OS-specific logic elsewhere in the codebase

### Notes

- Paths are user-scoped
- Derived using `platformdirs`
- No directories are created implicitly

---

## `models.py`

Defines **plain data models** used by the credentials subsystem.

### Design Intent

- Models are dataclasses
- Models may contain:
  - Static configuration
  - Cached runtime state (e.g. tokens, timestamps)
- Models do **not**:
  - Perform I/O
  - Encrypt data
  - Access keyrings

---

### `MSalConfig`

Represents configuration and cached state for Microsoft Graph email access.

Typical contents:

- Username and email address
- Client ID
- Authority (`organization` or `consumer`)
- Cached access token (optional)
- Token timestamp (optional)

A single instance fully describes a mailbox and its current authentication state.

---

### `GoogleAPIConfig`

Represents configuration and cached state for Google email access.

Typical contents:

- Email address
- Client ID
- OAuth scopes
- Cached access token (optional)
- Token timestamp (optional)

As with `MSalConfig`, runtime state is stored alongside static configuration.

---

### `KeyPolicy`

Defines **which of the two supported key strategies is allowed**.

Typical fields:

- `prefer_keyring: bool`
- `allow_passphrase_fallback: bool`

`KeyPolicy` is declarative only.  
It does **not** store keys or perform encryption.

---

## `store.py`

Contains the **only persistence and encryption logic** in the system.

### `SecureConfig`

`SecureConfig` is responsible for:

- Serializing credential models
- Encrypting serialized data
- Writing encrypted data to disk
- Retrieving encryption keys from:
  - System keyring **or**
  - User-supplied passphrase
- Decrypting and restoring models

## Security Notes

- The encrypted file may be readable by the user
- Security relies on:
  - OS account isolation
  - Keyring protections **or** passphrase secrecy
- This protects against:
  - Accidental disclosure
  - Casual inspection
- This does **not** protect against:
  - A fully compromised user account

This threat model is intentional and appropriate for the scope.

---

## Typical Usage Flow

1. Create a credential model (`MSalConfig` or `GoogleAPIConfig`)
2. Define a `KeyPolicy`
3. Initialize `SecureConfig`
4. Encrypt and save credentials
5. Later:
   - Load and decrypt credentials
   - Reuse cached tokens or refresh as needed

---

## Rationale

This design prioritizes:

- Predictability
- Auditability
- Ease of reasoning
- Minimal moving parts

It avoids enterprise-grade complexity while still enforcing **clear security boundaries**.
