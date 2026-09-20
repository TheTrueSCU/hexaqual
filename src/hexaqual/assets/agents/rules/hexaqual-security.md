<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
trigger: always_on
description: Mandatory security standards, prohibition of shell=True, credential detection, and least-privilege defaults.
---

## Security Invariants & Injection Defense

All code authored in this ecosystem must adhere to zero-trust design, injection defense, and least-privilege defaults.

### Security Invariants
1. **Strict Prohibition of `shell=True`**:
   - `subprocess.run`, `Popen`, or `asyncio.create_subprocess_exec` must NEVER be called with `shell=True`.
   - All external command arguments must be passed as an array of strictly validated strings to eliminate command injection vulnerabilities.

2. **Path Traversal Defense**:
   - Resolve and validate file paths against canonical base roots using `.resolve()`. Reject inputs containing un-sanitized `../` traversal sequences before performing disk operations.

3. **Zero Hardcoded Secrets**:
   - API tokens, passwords, and private keys must never be hardcoded into source files, test fixtures, or documentation.
   - Enforced by `detect-secrets` in pre-commit hooks.

4. **Default Least Privilege**:
   - All users, sessions, and CLI commands act in unprivileged user context by default.
   - Any action mutating cross-tenant state, inspecting other users' workloads, or connecting to infrastructure bastions requires positive, explicit elevation.
