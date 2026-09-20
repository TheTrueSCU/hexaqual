<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
name: hexaqual-pre-push
description: Comprehensive pre-push quality gate (auto-formatting, sanity with tests, architecture parity, AST graph update, and pre-commit verification).
---

# Workflow: Hexaqual Pre-Push Full Quality Gate

Execute this full gate sequentially prior to pushing feature branches or opening PRs:

1. **Auto-Format & Sync Drift**:
   ```bash
   uv run hexaqual statements fix
   uv run ruff check --fix . && uv run ruff format .
   uv run hexaqual docs usage --fix
   ```
   *(If `docs/assets/pydeps` exists: `uv run hexaqual deps pydeps --fix`)*

2. **Run Full Sanity with Tests**:
   ```bash
   uv run hexaqual sanity -a
   ```

3. **Verify Hexagonal Architectural Boundaries**:
   ```bash
   uv run hexaqual parity architecture
   ```

4. **Synchronize AST Knowledge Graph (if graphify installed)**:
   ```bash
   graphify update .
   ```

5. **Verify Pre-Commit Quality Gate**:
   ```bash
   uv run pre-commit run --all-files
   ```
