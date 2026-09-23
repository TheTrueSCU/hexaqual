<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
trigger: always_on
description: Modern Python tooling invariants (uv run, PEP 735, Python 3.13+) and mandatory local verification gate protocol.
---

## Modern Tooling & Local Gate Protocol

All repositories in the Hexa family strictly forbid ad-hoc package management, ambient global interpreter mutations, or declaring tasks complete without executing the local verification gate.

### 1. Modern Tooling Invariants
* **Strict Runner Prefix**: Prefix every CLI invocation with `uv run` (e.g. `uv run hexaqual sanity`, `uv run pytest`). Never invoke unmanaged system binaries (`python`, `pip`, `pytest` directly).
* **Zero Ad-Hoc Package Installation**: Never run `pip install <pkg>` or mutate the active environment imperatively. All dependencies must be tracked in `pyproject.toml` and locked via `uv lock`.
* **PEP 735 Dependency Groups**: Development and testing dependencies must be declared under `[dependency-groups]` (e.g. `dev = [...]`) rather than legacy `[tool.uv.dev-dependencies]` or `[project.optional-dependencies]`.
* **Modern Python 3.13+ Targets**: Leverage modern Python 3.13 standard library capabilities, modern type parameter syntax (`[T]`), and native exception groups.

---

### 2. Mandatory Verification Gate Protocol (Definition of Done)
Autonomous agents must **NEVER** state or report that a task, refactoring, or feature is complete without executing the standardized local verification gate and confirming that all checks pass:

1. **Scoped Sanity Gate**:
   - For single-package or focused modifications:
     ```bash
     uv run hexaqual sanity -p <pkg>
     ```
   - For monorepo-wide or cross-cutting changes:
     ```bash
     uv run hexaqual sanity -a --skip-tests
     ```
2. **Targeted Test Execution**:
   - Run the unit, integration, and property test suites covering the modified area:
     ```bash
     uv run pytest tests/unit/path/to/test_modified.py
     ```
3. **Clean Workspace State**:
   - Confirm git working tree cleanliness and ensure no extraneous scratch files or side-effects remain:
     ```bash
     git status --short
     ```
