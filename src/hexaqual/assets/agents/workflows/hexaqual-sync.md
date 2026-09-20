<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
name: hexaqual-sync
description: Synchronize universal .agents rules, workflows, and skills from the installed hexaqual package.
---

# Workflow: Synchronize Universal Agent Guardrails

Follow these steps when `hexaqual` is updated in `uv.lock` or `pyproject.toml`:

1. **Synchronize Package Environment**:
   ```bash
   uv sync
   ```

2. **Synchronize Agent Guardrails**:
   ```bash
   uv run hexaqual agents sync
   ```

3. **Verify Git Status**:
   - Check which `hexaqual-*` files were updated:
     ```bash
     git status --short .agents/
     ```

4. **Verify Quality Gate**:
   ```bash
   uv run hexaqual sanity -a --skip-tests
   ```
