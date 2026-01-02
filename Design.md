# Project Overview

## Goals

1. Provide a future-proof email sending library supporting Microsoft and Gmail
   - Microsoft: Microsoft Graph 
   - Google: Gmail API 

2. Prefer first-party, officially supported APIs over legacy protocols
   - Treat OAuth-backed REST APIs as the default
   - Avoid long-term reliance on basic auth or deprecated SMTP flows

3. Abstract providers behind a stable transport interface
   - Allow Microsoft and Google implementations to evolve independently
   - Minimize API churn for downstream users when providers change

4. Support modern authentication flows
   - OAuth 2.0 delegated flows as the default
   - Secure token caching and refresh
   - No embedded secrets in code or config files

5. Be suitable for both library and automation use
   - Clean programmatic API
   - Optional CLI usage without coupling core logic to CLI concerns

6. Maximize longevity across enterprise and consumer accounts
   - Work with paid and free Microsoft accounts where supported
   - Work with consumer and Workspace Gmail accounts
   - Degrade gracefully when provider capabilities differ

7. Maintain a strict security posture
   - OS-level secure storage where available
   - Fail closed if secure storage or auth fails
   - Never silently downgrade security guarantees

8. Remain packaging-friendly
   - Compatible with PyInstaller and frozen executables
   - No hard dependency on cloud runtime features

## Non-Goals
- No GUI
- No daemon/background services
- No cloud dependency
- No inbox access or message retrieval
- No email campaign or templating system

## Design Principles
- Library > CLI > App layering
- Side-effect free modules
- Explicit configuration over magic
- OAuth delegated flow preferred over app-only
- SMTP support is considered a compatibility fallback, not a primary transport
- SMTP implementations must not bypass OAuth-based security guarantees

## Security Model
- Tokens stored via OS keyring when possible
- No plaintext secrets on disk
- Fail closed rather than fallback insecurely

## Constraints
- Python >= 3.12
- Must be packagable via PyInstaller
- Must work on Windows Server 2019

## Directory Responsibilities
- credentials/: secure storage, encryption, token persistence
- auth/: OAuth and protocol-level authentication flows
- transport/: provider-specific message delivery (Graph, Gmail, SMTP)
- message/: message normalization and validation (provider-agnostic)

## Stability Contract
- Public APIs are considered stable once introduced
- Provider-specific changes must not affect the public interface
- Breaking changes require explicit version bumps
