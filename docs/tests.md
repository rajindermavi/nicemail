# Testing Guide

This library is designed to be imported by other projects.
Tests focus on public behavior and contracts, not implementation details.

## Goals

- Verify public APIs behave correctly when imported
- Catch regressions in message construction, config storage, and transport logic
- Ensure errors are raised consistently
- Avoid testing external providers (Microsoft, Google)

## Non-Goals

- No live OAuth flows
- No network calls
- No real email delivery
- No keyring dependency in CI

## Testing Strategy

### 1. Unit Tests
- Pure functions
- Dataclasses and validation logic
- Message builders
- Config serialization / encryption logic (with test keys)

### 2. Contract Tests
- Transport interfaces
- Token provider interfaces
- Dry-run behavior

### 3. Integration-Style Tests (Local Only)
- Use temporary directories
- Use fake token providers
- Use DryRunTransport

## Techniques

- pytest
- tmp_path for filesystem isolation
- fakes instead of mocks where possible
- monkeypatch only at boundaries

## Test Structure

tests/
  test_message_builder.py
  test_secure_config.py
  test_dry_run_transport.py
  test_client_send_flow.py

## Rule of Thumb

If a test requires internet access, it is invalid.
If a test requires a real email account, it is invalid.
If a test breaks when refactoring internals, it is invalid.
