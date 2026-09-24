<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
trigger: always_on
description: Mandatory synchronization of READMEs, Zensical documentation, and architecture diagrams on feature and API changes.
---

## Universal Documentation & Diagram Synchronization

Whenever adding, updating, or refactoring framework features, public APIs, adapters, packages, or optional extras:

### 1. Package & Root README Synchronization
- **`README.md`**: Every newly introduced or modified public API, function, class, or decorator must be documented with runnable code examples.
- **Optional Extras**: All newly available optional extras (e.g. `[mcp]`, `[qdrant]`, `[nats]`) and their installation commands (`pip install "pkg[extra]"`) must be documented in the package README.
- **Monorepo Matrices**: For multi-package repositories, ensure root package catalogs, feature comparison tables, and installation sections reflect new or updated capabilities.

### 2. Zensical Documentation (`docs/`)
- **Guides & References**: Update corresponding documentation pages under `docs/` (e.g. `docs/packages/`, `docs/features/`, `docs/architecture.md`) with accurate usage patterns.
- **Cross-Component Architecture**: When introducing cross-package or multi-service relationships, document the rationale, failure modes, and layer boundaries.

### 3. Diagram & Topology Accuracy
- **Mermaid Diagrams**: Update all embedded sequence, flowchart, and architecture diagrams in docs and READMEs to reflect modified components or message flows.
- **Architecture SVGs**: Ensure architecture diagrams (`docs/assets/pydeps/*.svg`) are up to date (regenerated via `hexaqual sanity -p <pkg> --fix` or pre-commit hooks).
- **Build Validation**: Verify that documentation compiles cleanly without broken internal links or missing anchor targets via `zensical build` (or pre-commit `zensical docs build validation`).
