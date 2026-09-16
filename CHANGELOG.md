# CHANGELOG

## v0.4.0 (2026-09-16)

### Highlights & Features
* **Turnkey Composite GitHub Action (`action.yml`)**: Added turnkey composite GitHub Action supporting `pre-commit`, `sanity`, and `setup` execution modes with automated uv, Python, and pre-commit caching across CI pipelines.
* **Modular Pre-Commit Hooks Menu (`.pre-commit-hooks.yaml`)**: Exposed standalone, reusable pre-commit hooks including `hexaqual-sanity`, `hexaqual-architecture`, `hexaqual-test-parity`, `hexaqual-statements`, `hexaqual-linter`, `hexaqual-extras`, `hexaqual-usage-docs`, and `hexaqual-docs-links`.
* **Documentation Link Integrity Scanner (`hexaqual docs links`)**: Added relative path, cross-file reference, and anchor integrity validation across Markdown documentation trees with table, JSON, and Markdown presentation adapters.
* **Standardized CLI Options & Pipe Detection (`hexaqual.cli.options`)**: Centralized `OutputFormat` enum, `format_option()` factory, and `resolve_format()` with automatic terminal TTY vs pipeline redirection detection across CLI diagnostic commands.
* **Hexaflow v0.3.0 Engine Upgrade**: Upgraded core workflow orchestrator dependency to `hexaflow>=0.3.0`.

## v0.3.0 (2026-09-14)

### Highlights & Features
* **Hexaflow v0.2.0 Integration & Dynamic CLI Binder Dogfooding**: Upgraded to `hexaflow>=0.2.0`, dogfooding `WorkflowCliBinder` to introspect workflow DAGs and dynamically bind CLI options (`--skip-ruff`, `--skip-ty`, `--skip-parity`, `--skip-statements`, `--skip-deptry`, `--skip-complexity`, `--skip-tests`) with `TriggerRule.ALL_SUCCESS_OR_SKIPPED` skip propagation across `hexaqual check` and `hexaqual sanity`.
* **Architecture Test Parity (`hexaqual parity architecture`)**: Introduced `check_architecture_test_parity` and the `hexaqual parity architecture` command to ensure that packages with internal hexagonal architectures maintain dedicated `test_hexagonal_boundaries.py` architectural test suites.
* **Colocated Dynamic Fuzz Harness Discovery**: Enhanced `hexaqual test fuzz` to dynamically discover and execute Atheris coverage-guided and OWASP security fuzz harnesses colocated within individual package test suites (`packages/*/tests/fuzz/test_fuzz_*.py`) alongside root harnesses.

## v0.2.2 (2026-09-14)

### Highlights & Features
* **Full Legacy Tool Subsumption**: Subsumed all 35 former `hexastack-tools` entrypoint scripts into first-class native `hexaqual` CLI commands across 8 sub-apps (`test`, `mutate`, `deps`, `imports`, `parity`, `statements`, `release`, `gh`, `docs`, `refactor`). All operations dispatch directly through the internal CQRS bus with zero legacy script dependencies.
* **Coverage-Guided & Adversarial Fuzzing (`hexaqual test fuzz`)**: Integrated Atheris coverage-guided and OWASP security fuzzing directly into the CLI via `FuzzRunCommand` with multi-format presentation (rich table, json, markdown).
* **Inline Snapshot Management (`hexaqual test snapshot`)**: Added native commands to review, create, and fix `inline-snapshot` assertions across single-process test runs via `UpdateInlineSnapshotsCommand`.
* **Architectural Boundary Testing (`hexaqual test archon`)**: Added automated `pytest-archon` test generation across packages via `GenerateArchonTestsCommand`.
* **Automated Refactoring & Alphabetization (`hexaqual refactor`)**: Introduced `refactor` sub-application powered by Rope (`rename`, `extract`, `move`, `run`) and native AST code symbol alphabetization (`hexaqual refactor alphabetize`).
* **CodeQL SAST Scanning (`hexaqual gh codeql`)**: Wired GitHub CodeQL static analysis scanning into the `gh` sub-application via `ScanCodeQlCommand`.
* **Medium Article Publishing (`hexaqual docs publish`)**: Added automated Markdown article publishing to Medium via `PublishMediumArticlesCommand`.
* **Cognitive Complexity Inspection (`hexaqual complexity`)**: Added direct command to audit functions and methods exceeding cognitive complexity limits ($\le 25$) via `complexipy`.
* **Documentation & Catalog Refresh**: Regenerated full unrolled CLI tree in `USAGE.md`, updated `README.md` Command Overview table, and refined architectural layout in `docs/ARCHITECTURE.md`.

## v0.2.1 (2026-09-13)

### Highlights & Features
* **Deptry Dependency Auditing Integration**: Integrated `deptry` as a first-class check in the `hexaqual sanity` DAG pipeline, verifying that all imports across production packages are cleanly declared in `pyproject.toml`.
* **Dependency Management Commands (`hexaqual deps`)**: Added dedicated `deps` sub-app with `hexaqual deps audit`, `hexaqual deps deptry`, and `hexaqual deps graph` (architecture dependency graphs via `pydeps`).
* **Granular Sanity Check Skipping**: Added CLI options to selectively skip specific checks during sanity verification (`--skip-tests`, `--skip-lint`, `--skip-types`, `--skip-complexity`, `--skip-statements`, `--skip-parity`, `--skip-deptry`).
* **CI Pipeline Gate Fortification**: Updated GitHub Actions release workflow to enforce pre-commit quality gate and unit test suite completion on tagged commits before triggering PyPI publishing.

## v0.2.0 (2026-09-13)

### Highlights & Features
* **Standalone Quality & Governance Engine**: Formal extraction of Hexastack's developer tooling into the standalone `hexaqual` package (`hexaqual[all]>=0.2.0`).
* **Modular Hexagonal Architecture & CQRS Bus**: Built around an in-process synchronous CQRS bus (`create_governance_bus`), domain models, and decoupled presentation/runner ports.
* **Unified Multi-Stage Sanity Check (`hexaqual check` / `sanity`)**: Declarative sanity pipeline orchestrating Ruff linting/formatting, Ty static typing, Complexipy cognitive complexity, AST-level `__all__` casefold sorting, and 1:1 unit test parity verification.
* **Automated Public API Surface Integrity (`hexaqual statements`)**: AST visitor and transformer that validates and automatically formats `__all__` exports with strict casefold ordering and deduplication.
* **1:1 Test Parity & Optional Extras Auditing (`hexaqual parity`)**: Instant verification of source-to-test file symmetry and audit of subpackage optional extras forwarding into umbrella distributions.
* **Mutation Testing Runner & Inspector (`hexaqual mutate`)**: Scoped package mutation testing with cache purging (`--reset`), summary triage, and test coverage correlation via `mutmut`.
* **Selective Impact-Driven Test Runner (`hexaqual test`)**: Workspace pytest runner supporting affected target resolution from git diffs (`-A`), property test targeting (`-P`), boundary assertion audits, and redundancy analysis.
* **GitHub PR & Repo Governance Diagnostics (`hexaqual gh`)**: Interactive pull request dashboard with live polling (`--watch`), check run triage, repository visibility auditing, and security advisories.
* **Smart PyPI Release Tooling (`hexaqual release`)**: Reproducible wheel build verification, metadata validation, and idempotent publishing with duplicate version skipping.
* **Automated CLI Documentation (`hexaqual docs usage`)**: Introspective command tree unrolling and automated `USAGE.md` catalog synchronization.
