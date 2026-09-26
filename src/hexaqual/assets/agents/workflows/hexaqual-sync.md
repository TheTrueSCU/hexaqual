<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
name: hexaqual-sync
description: Synchronize universal .agents rules, workflows, and skills from the installed hexaqual package.
---

# Workflow: Synchronize Universal Agent Guardrails

Follow these steps when `git pull`, merge, or branch checkout updates `.agents/` or when `hexaqual` is updated in `uv.lock` or `pyproject.toml`:

1. **Synchronize Package Environment**:
   ```bash
   uv sync
   ```

2. **Synchronize Agent Guardrails**:
   ```bash
   uv run hexaqual agents sync
   ```

3. **Verify Git Status & Re-Read Guardrails (AI Assistants)**:
   - Check which `hexaqual-*` files were updated:
     ```bash
     git status --short .agents/
     ```
   - **Crucial**: Inspect and re-read any modified rules in `.agents/rules/` into active context to prevent operating under stale invariants.

4. **Verify Quality Gate**:
   ```bash
   uv run hexaqual sanity -a --skip-tests
   ```
