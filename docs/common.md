# common/

This folder contains **foundational, provider-agnostic primitives** shared across the library.

The purpose of `common/` is to centralize **stable concepts** that are reused by multiple
subpackages (e.g. `credentials/`, `auth/`, `transport/`, `message/`) without introducing
tight coupling or circular dependencies.

---

## Design Goals

Code in `common/` should:

- Be **stable** and change infrequently
- Be **provider-agnostic** (no Microsoft, Google, SMTP, etc.)
- Be safe to import from **any** other package
- Have **no side effects** at import time
- Favor **clarity over abstraction**

This library is intentionally small-scale and opinionated.
`common/` is not intended to become a generic utility grab-bag.

---

## Allowed Contents

The following kinds of code are appropriate for `common/`:

### Configuration primitives
- Base configuration models
- Shared config validation logic
- Non-provider-specific defaults

### Paths and storage helpers
- Platform-specific storage resolution
- Directory and file layout conventions
- Helpers built on `platformdirs` or similar

### Shared models and types
- Enums
- Literals
- Typed containers
- Protocols or ABCs used across modules

### Errors and exceptions
- Shared exception hierarchy
- Base error types used by multiple packages

### Lightweight helpers
- Serialization helpers (e.g. JSON encoding/decoding)
- Redaction or masking helpers
- Small, pure utility functions

---

## Disallowed Contents

The following **must not** live in `common/`:

- Provider-specific logic (Microsoft Graph, Google API, SMTP, etc.)
- Authentication or credential flow logic
- Business logic or policy decisions
- Code that imports from higher-level packages (e.g. `credentials/`, `auth/`)
- Modules with significant runtime side effects
- Catch-all `helpers.py`, `misc.py`, or similar dumping grounds

> **Rule:** If a module in `common/` needs to import from another package in this library,
> it does not belong in `common/`.

---

## Dependency Direction

Dependencies must flow **outward**, never inward:


- `common/` may not depend on any other internal package
- Other packages may freely depend on `common/`

---

## Naming Guidance

Prefer **descriptive module names** over generic ones:

GOOD: `config.py`, `paths.py`, `errors.py`, `types.py`  
BAD: `utils.py`, `helpers.py`, `misc.py`

If a module grows large or unstable, it should be moved out of `common/`
into a more appropriate package.

---

## Summary

`common/` exists to reduce duplication **without** increasing coupling.

When in doubt:
- Favor duplication over premature abstraction
- Favor clarity over cleverness
- Favor stability over convenience
