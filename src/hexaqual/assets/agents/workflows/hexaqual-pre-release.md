<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
name: hexaqual-pre-release
description: Comprehensive pre-release audit, documentation freeze, reproducible packaging verification, and PyPI readiness check.
---

# Workflow: Hexaqual Pre-Release Audit & Validation

Execute these steps prior to cutting a release tag and publishing to PyPI:

1. **Documentation & Asset Freeze**:
   - Regenerate and format CLI USAGE documentation:
     ```bash
     uv run hexaqual docs usage --fix
     ```
   - Refresh architecture diagrams (if `docs/assets/pydeps` exists):
     ```bash
     uv run hexaqual deps pydeps --fix
     ```
   - Validate documentation links and references:
     ```bash
     uv run hexaqual docs links
     ```
   - Verify agent assets are synchronized across the workspace:
     ```bash
     uv run hexaqual agents check
     ```

2. **Verify Extras Forwarding**:
   ```bash
   uv run hexaqual parity extras
   ```

3. **Check PyPI Version Availability**:
   ```bash
   uv run hexaqual release check
   ```

4. **Verify Bit-for-Bit Reproducible Wheel Builds**:
   ```bash
   uv run hexaqual release reproducible
   ```

5. **Ensure Workspace Lockstep Versioning**:
   - Verify that all subpackages in `packages/*/pyproject.toml` and root `pyproject.toml` have identical version tags without unpinned local development paths.
   - Update `CHANGELOG.md` with release highlights, features, and fixes.
