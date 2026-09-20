<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
name: hexaqual-pre-commit
description: Fast pre-commit quality gate (static sanity, formatting, docs freshness, link checks, and agent sync).
---

# Workflow: Hexaqual Pre-Commit Quality Gate

Follow these steps prior to staging and committing changes to ensure local branch health:

1. **Run Static Sanity Battery (Inner Loop, <10s)**:
   ```bash
   uv run hexaqual sanity -a --skip-tests
   ```

2. **Auto-Fix Drift (if failures occur)**:
   - If `__all__` export order failed:
     ```bash
     uv run hexaqual statements fix
     ```
   - If architecture diagrams are stale (and `docs/assets/pydeps` exists):
     ```bash
     uv run hexaqual deps pydeps --fix
     ```
   - If formatting or lint errors occurred:
     ```bash
     uv run ruff check --fix .
     uv run ruff format .
     ```

3. **Verify Documentation & Link Integrity**:
   - Check CLI USAGE documentation freshness:
     ```bash
     uv run hexaqual docs usage --check
     ```
     *(Auto-fix with `uv run hexaqual docs usage --fix` if CLI entrypoints changed)*
   - Validate internal markdown links and anchors:
     ```bash
     uv run hexaqual docs links
     ```

4. **Verify AI Agent Guardrails Synchronization**:
   ```bash
   uv run hexaqual agents check
   ```
   *(If drift detected, run `uv run hexaqual agents sync`)*

5. **Run Impacted Tests**:
   ```bash
   uv run hexaqual test impact
   ```
