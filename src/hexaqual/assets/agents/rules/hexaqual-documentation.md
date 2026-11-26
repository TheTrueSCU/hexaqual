<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
trigger: always_on
description: Mandatory synchronization of READMEs, Zensical documentation, architecture diagrams, and pre-release documentation accuracy verification.
---

## Universal Documentation & Diagram Synchronization

Whenever adding, updating, or refactoring framework features, public APIs, adapters, packages, or optional extras:

### 1. Package & Root README Synchronization
- **`README.md`**: Every newly introduced or modified public API, function, class, or decorator must be documented with runnable code examples.
- **Optional Extras**: All newly available optional extras (e.g. `[mcp]`, `[qdrant]`, `[nats]`) and their installation commands (`pip install "pkg[extra]"`) must be documented in the package README.
- **Monorepo Matrices**: For multi-package repositories, ensure root package catalogs, feature comparison tables, and installation sections reflect new or updated capabilities.

### 2. Zensical Documentation (`docs/`)
- **Guides & References**: Update corresponding documentation pages under `docs/` (e.g. `docs/packages/`, `docs/features/`, `docs/architecture.md`) with accurate usage patterns.
- **Canonical Ecosystem Map (`docs/ecosystem.md`)**: `TheTrueSCU/hexaqual/docs/ecosystem.md` is the canonical, version-free source of truth for the Hexa family diagram and contracts. Whenever adding, removing, or rewiring packages in any `hexa-*` repository (e.g. `hexaqueue-executors`), update `hexaqual/docs/ecosystem.md` first and mirror it identically across sibling repos.
- **Cross-Component Architecture**: When introducing cross-package or multi-service relationships, document the rationale, failure modes, and layer boundaries.

### 3. Diagram & Topology Accuracy
- **Mermaid Diagrams**: Update all embedded sequence, flowchart, and architecture diagrams in docs and READMEs to reflect modified components or message flows.
- **Architecture SVGs**: Ensure architecture diagrams (`docs/assets/pydeps/*.svg`) are up to date (regenerated via `hexaqual sanity -p <pkg> --fix` or pre-commit hooks).
- **Build Validation**: Verify that documentation compiles cleanly without broken internal links or missing anchor targets via `zensical build` (or pre-commit `zensical docs build validation`).

### 4. Pre-Release Documentation Verification Gate (Mandatory Before Any Release)
Before cutting any release tag or publishing packages, agents **MUST** execute and pass the full documentation verification battery:
- **Manifest & Metric Drift**: Run `uv run hexaqual docs drift` to confirm zero drift between documented counts, badges, or file references and source manifests (ADR-005).
- **CLI Usage Freshness**: Run `uv run hexaqual docs usage --check` (or `--fix` if CLI entrypoints changed) to verify generated `USAGE.md` files match live commands.
- **Link Integrity**: Run `uv run hexaqual docs links` to verify zero broken internal markdown links or missing anchors across tracked docs and READMEs.
- **Site Build Compilation**: Run `uv run zensical build` (and clean up untracked `site/` output) to ensure the documentation site compiles with zero broken nav targets or warnings.
- **Semantic Accuracy Audit**: Verify `README.md`, package READMEs, `docs/`, and `CHANGELOG.md` accurately reflect the current codebase — public API signatures/examples, CLI subcommands and flags, optional extras, Python version floor badges (`requires-python`), package catalogs, and version-free prose/diagrams (retain explicit version pins only in copy-pasteable `.pre-commit-config.yaml` / GitHub Actions snippets and dynamic PyPI shields).
- **Ecosystem Map Parity**: When a release adds, removes, or rewires packages in any `hexa-*` repository, verify `TheTrueSCU/hexaqual/docs/ecosystem.md` is updated first and mirrored identically across sibling repos.
