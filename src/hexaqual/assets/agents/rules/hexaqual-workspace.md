<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
trigger: always_on
description: Workspace dependency hierarchy, monorepo import boundaries, and __all__ export ordering invariants.
---

## Workspace Hierarchy & API Surface Integrity

For monorepos containing multiple packages (e.g. `hexastack`, `hexaqueue`), maintain strict subpackage isolation:

### 1. Unidirectional Workspace Dependency Direction
- Subpackages may depend on the foundation package (e.g. `*-core`), but foundation packages must **NEVER** import from leaf packages (e.g. `core` must never import from `cqrs`, `server`, `worker`, or `cli`).
- Leaf packages must not import from sibling packages unless explicitly declared as a dependency in their `pyproject.toml`.

### 2. Import Protocol
- Never use relative filesystem traversal (`../../`) across workspace package roots.
- All cross-package imports must use standard top-level package names declared in `pyproject.toml` workspace members (e.g. `from hexaqueue_core.domain.models import JobSpec`).

### 3. Strict `__all__` Ordering & Cleanliness
- Every public module must declare `__all__`.
- The `__all__` list must be **strictly sorted alphabetically (casefold ordering)** and deduplicated.
- Enforced deterministically by `uv run hexaqual statements check` (auto-fixed via `uv run hexaqual statements fix`).
