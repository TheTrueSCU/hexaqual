# CHANGELOG

## v0.12.0 (2026-11-23)

### Highlights & Performance
* **Clean `PRIVATE`-Mode `pytest-gremlins` Execution & Operator Sharding (#64)**:
  - Dropped redundant `--cov=src` and `--cov-fail-under=0` flags from `SubprocessTestingRunnerAdapter._run_gremlins` and `HexaqueueClusterRunnerAdapter._build_gremlins_args` so `pytest-gremlins` runs cleanly in `PRIVATE` coverage mode under `-n auto` without `cov_contexts=0` or sharded pre-scan timeouts.
  - Added `--operators`, `--mutant-timeout` (default `120`s), `--prescan-workers` (`min(4, CPUs)` / `4` on cluster), and `--coverage-timeout` (default `300`s) CLI options and forwarded them through `RunMutationTestsCommand`, `TestingRunnerPort`, and `RunMutationTestsHandler`.
  - Stopped emitting `--gremlin-batch`/`--gremlin-batch-size` when `batch_size <= 1`.
  - Added intra-file AST operator sub-sharding (`GREMLIN_OPERATORS`, `DEFAULT_OPERATOR_SHARD_WEIGHT = 250`, `DEFAULT_MAX_OPERATOR_SHARDS = 4`, `estimate_file_operator_weights`, `partition_operators_lpt`) in `hexaqual.utils.mutation_slicing` so heavy modules fan out across cluster workers (`-op0`..`-op3`).
* **Pre-Release Hardening & Dependency Updates (#65, #63)**:
  - Required `pytest-gremlins>=1.14.3` in `hexaqual[gremlins]` and `dev` dependencies for `--gremlin-prescan-workers` and the AST parent-link hang fix (#65).
  - Enabled operator sub-sharding for multi-file cluster slices containing any file with AST weight `>= 250`, and added an explicit stderr/logger warning when `pytest-hexaqueue` (`hexaqual[cluster]`) is missing during remote collateral staging (#65).
  - Updated workspace dependencies via Dependabot (#63).

## v0.11.0 (2026-11-19)

### Highlights & Features
* **AST-Weighted, Capacity-Capped LPT Mutation Slicing & `hexaqual mutate plan` CLI**:
  - Added shared pure-stdlib `hexaqual.utils.mutation_slicing` module implementing AST mutable-site weighting (ignoring docstrings/comments), heavy-file solo isolation, dynamic slice expansion under a configurable per-slice weight cap (`DEFAULT_MAX_SLICE_WEIGHT = 450`, up to `16` cluster slices), and heaviest-first LPT dispatch ordering.
  - Upgraded `HexaqueueClusterRunnerAdapter._partition_targets` and `_build_mutation_job_specs` from fixed 4-slice alphabetical round-robin to dynamic AST-weighted LPT bin packing.
  - Added `hexaqual mutate run --targets` (`-t`) to scope mutation runs to comma-separated relative file paths.
  - Added `hexaqual mutate plan` CLI command (`--mode affected|all|slices|changed-slices`, `--slices`, `--max-weight`, `--github-output`) and updated `.github/actions/mutate-plan` to invoke it (with a bare-Python `fallback.py` shim).
* **Cluster Cancellation & Dependency Updates**:
  - Cancelled remote Hexaqueue runs cleanly on `SIGINT`/`SIGTERM` (#61).
  - Required `pytest-gremlins>=1.13.2` for `--gremlin-mutant-timeout` (#59).
  - Updated workspace dependencies via Dependabot (#53) and set `src = ["src"]` in `[tool.ruff]` to prevent root artifacts from skewing import sorting.

## v0.10.7 (2026-11-18)

### Fixes & Improvements
* **Mutation Testing Scoping, Matrix Sharding & CI Guardrails**:
  - Excluded `demo`, `e2e`, and `integration` pytest markers (`-m "not demo and not e2e and not integration"`) from `SubprocessTestingRunnerAdapter._run_gremlins` and `HexaqueueClusterRunnerAdapter._build_pytest_args`.
  - Guarded `HexaqueueClusterRunnerAdapter._emit_step_summary` to skip writing to `$GITHUB_STEP_SUMMARY` when `PYTEST_CURRENT_TEST` is active so unit tests never pollute CI job summaries.
  - Added LPT greedy bin-packing matrix sharding (`.github/scripts/discover_mutation_slices.py`) and consolidated summary aggregation (`.github/scripts/aggregate_mutation_summary.py`) for `mutation_scheduled.yml`.
  - Fortified `tests/unit/domain/test_openssf.py` (`CRITERIA_CATALOG` `met_url_required` set and defaults), raising `domain/openssf.py` mutation score from 4.5% to 96%.

## v0.10.6 (2026-11-17)

### Fixes & Improvements
* **Hexaqueue Cluster Runner Observability**:
  - Timestamped (`UTC`) and 30s-throttled `[Hexaqueue ...]` SSE/poll status heartbeats in `HexaqueueClusterRunnerAdapter`.
  - Appended `hq status <run_id>`, `hq top`, and `hq logs <job_id>` inspection commands to `GITHUB_STEP_SUMMARY` upon remote run submission.
* **Mutation Testing Scoping & Guardrails**:
  - Scoped `pytest-gremlins` invocations in `SubprocessTestingRunnerAdapter._run_gremlins` and `HexaqueueClusterRunnerAdapter._build_pytest_args` to `tests/unit` when present, avoiding e2e, demo, integration, and benchmark suites during mutation sweeps.
  - Enabled `--gremlin-cache` and `--gremlin-mutant-timeout=30` to prevent runaway mutant loops.

## v0.10.5 (2026-11-10)

### Highlights & Features
* **Multi-Package Mutation Run DAG & Direct-Only Scoping**:
  - Upgraded `TestingRunnerPort.run_mutation_testing` and `TestingRunnerAdapter` to accept `Sequence[Path]` for unified multi-package testing.
  - Implemented single unified `RunSpec` DAG submission across all affected packages in `HexaqueueClusterRunnerAdapter`, staging CAS workspace collateral once and packing constituent package jobs concurrently into worker pools.
  - Added `--direct` / `--direct-only` flag to `hexaqual mutate run` and `direct_only: bool` in `WorkspaceAdapter.resolve_affected_packages` to restrict mutation testing impact strictly to directly changed packages, bypassing transitive package sweeps during PR CI workflows.
  - Fortified test suites and verified $\le 25$ cognitive complexity.

## v0.10.4 (2026-11-10)

### Highlights & Features
* **Hexaqueue Cluster Extra, Workspace Collateral Staging & Targeted Mutation Slicing**:
  - Added `cluster` optional extra (`pytest-hexaqueue>=0.9.1`) and bundled into `hexaqual[all]`.
  - Added `require_dependency` in `hexaqual.domain.imports` with actionable installation hints (`uv add 'hexaqual[cluster]'`).
  - Integrated `GitWorkspaceArchiver` from `pytest-hexaqueue` via optional dependency to eliminate duplicate workspace archiving logic.
  - Implemented automatic Content-Addressable Storage (CAS) workspace collateral staging via Hexaqueue's `/api/v1/collateral/checksum/{sha256}` and `/api/v1/collateral/stage` endpoints.
  - Implemented multi-slice mutation batch partitioning across cluster workers using `pytest-gremlins --gremlin-targets` attached to individual slice `JobSpec`s.

## v0.10.3 (2026-11-09)

### Highlights & Features
* **Standardized GitHub Step Summaries (`$GITHUB_STEP_SUMMARY`)**:
  - Implemented `append_step_summary` and `summary_option` in `hexaqual.cli.options` to append Markdown summaries directly to `$GITHUB_STEP_SUMMARY`.
  - Added `--step-summary` option to `hexaqual mutate inspect` to output triage tables and surviving mutant summaries directly to GitHub job summaries.
  - Decoupled terminal output from Markdown rendering with explicit `render_*_markdown` methods on `MarkdownGovernancePresenterAdapter` and `MarkdownTestingPresenterAdapter`.
* **Standard Library Lazy Import Elimination**:
  - Eliminated in-function stdlib lazy imports (`import os`) in `hexaqual.cli.gh` and `hexaqual.cli.test` in compliance with hexagonal import guardrails.

## v0.10.2 (2026-11-09)

### Highlights & Features
* **Configurable Cluster Workload Timeout (`HEXAQUEUE_TIMEOUT` & `--cluster-timeout`)**:
  - `HexaqueueClusterRunnerAdapter` now reads `HEXAQUEUE_TIMEOUT` from the environment with a 1800.0s (30m) default (replacing the hardcoded 300s limit).
  - Exposes `--cluster-timeout` across `hexaqual mutate run` and `hexaqual test run`.

## v0.10.1 (2026-11-09)

### Highlights & Features
* **Standardized Optional Dependency Verification (`hexaqual.domain.imports`)**:
  - Introduced `optional_dependency` module helper providing clean, progressive feature degradation without static package import dependencies.
  - Replaced ad-hoc `try ... except ImportError` blocks with standardized optional dependency inspection.
* **Cluster Runner Pytest-Hexaqueue Auto-Delegation (`hexaqual.adapters.runners.hexaqueue_cluster`)**:
  - `HexaqueueClusterRunnerAdapter.execute_pytest` now detects `optional_dependency("pytest_hexaqueue")` and delegates to `--hexaqueue --hq-server` transparently.
* **Graceful Target Scope Resolution (`hexaqual.adapters.code_analysis.pytest_runner`)**:
  - Resolves non-existent package test subdirectories cleanly (returning `None`) and skips execution with exit code 0 when targeted scopes (e.g. `-P` for property tests) have no matching test directory.

## v0.10.0 (2026-11-01)

### Highlights & Features
* **Profile-Driven Distributed Test Slicing (`hexaqual test run --profile <name>`)**:
  - Added single-option `--profile` (with `--hq-profile` alias) to `hexaqual test run` CLI and `pytest_runner` adapter.
  - Seamlessly integrates with `pytest-hexaqueue` and `pyproject.toml [tool.hexaqueue.profiles.<name>]`, delegating test partitioning, remote slice dispatch, and coverage aggregation across cloud-agnostic worker nodes or Multi-CSP Free-Tier meshes.
  - Adheres to Zero-Spend Default ($0.00 ceiling) guardrails unless explicitly overridden in named profile definitions.

## v0.9.10 (2026-10-26)

### Highlights & Features
* **In-Place PR Status Dashboard Comments (`--pr`)**:
  - Implemented single-comment PR status reporting in `hexaqual gh ci-duration --pr <number>`, updating via idempotent HTML marker `<!-- hexaqual-ci-dashboard -->`.
  - Dispatches `PATCH` (or initial `POST`) via GitHub CLI REST API, avoiding notification spam across review threads.
  - Supports dual-outcome failure reporting: updates PR status comments on both success and failure before final upstream failure exit.

## v0.9.9 (2026-10-26)

### Highlights & Features
* **Topological Executed Workflow Graph**:
  - Generates color-coded Mermaid flowcharts (`flowchart TD`) in `$GITHUB_STEP_SUMMARY` and PR comments depicting actual executed pipeline topology with `:::passed` (green), `:::failed` (red), `:::skipped` (gray), and `:::running` (yellow).
  - Annotates job nodes with real elapsed execution durations (e.g. `Pre-Commit Quality Gate<br/><b>31s</b>`).
  - Implemented dynamic duration calculation for running jobs (e.g. `ci-success` accurately calculates elapsed execution time instead of reporting 0s / Pending).
  - Normalized job names to cleanly split multi-version runtime matrices into distinct execution nodes.

## v0.9.8 (2026-10-26)

### Highlights & Features
* **CI Execution Duration Breakdown & Historical Trend Charts (`hexaqual gh ci-duration`)**:
  - Implemented `gh ci-duration` driving adapter querying GitHub Actions API for per-job runtimes and historical execution trends.
  - Generates rich Markdown tables and Mermaid line charts (`xychart-beta`) visualizing workflow runtime evolution across runs.
* **Benchmark Trend Reporting (`hexaqual test benchmark-report`)**:
  - Added CLI reporter transforming `pytest-benchmark` JSON outputs into historical performance line charts.
* **Scheduled Deep Governance Workflows**:
  - Configured weekly scheduled full-workspace mutation audits (`mutation_scheduled.yml`) via pytest-gremlins.
  - Configured weekly automated benchmark tracking (`benchmark_scheduled.yml`).
  - Added coverage-guided security fuzzing (`fuzz.yml`) with Atheris.
* **Shift-Left Pre-Commit Latency Optimization**:
  - Added `--skip-diagrams` option to `hexaqual-pre-push` git hook and relocated heavy network audits to pre-push.
  - Added multi-core parallel unit test gate (`hexaqual test run -A -U -n auto`).

## v0.9.7 (2026-10-23)

### Highlights & Features
* **Python 3.12+ Universal Support Matrix**:
  - Broadened `requires-python` from `>=3.13` to `>=3.12`, officially supporting Python 3.12, 3.13, 3.14, and 3.15.
  - Updated upstream DAG workflow engine dependency to `hexaflow>=0.5.2`.
* **Native CLI Testing & Demo Narration Engine (`hexaqual.adapters.testing`)**:
  - Migrated `CliNarrator`, `TerminalEvent`, and `render_cli_demo_video` directly into `hexaqual.adapters.testing`, eliminating all downstream dependencies on `hexastack-cli` across the toolchain.
  - Decoupled e2e narrative test recording and terminal video rendering into standalone adapter components.

## v0.9.6 (2026-10-22)

### Highlights & Features
* **Universal Lazy Import Guardrails & AST Auditor (`hexaqual-lazy-imports`)**:
  - Bundled universal agent rule `hexaqual-lazy-imports.md` defining strict directional hexagonal layer invariants (`domain` purity, `adapters ↛ infra`) and permissible criteria for lazy imports.
  - Bundled AST auditor skill `hexaqual_audit_lazy_imports.py` providing sub-second static inspection of function scopes for unauthorized standard library imports, domain purity leaks, and layer bypasses.
  - Added unit test suite `test_hexaqual_audit_lazy_imports.py` validating AST detection, exclusion rules, and CLI exit codes.
* **Abstract Port Test Introspection (`inspect.isabstract`)**:
  - Refactored port test suite generators and assertions to inspect `inspect.isabstract` across port verification suites for robust structural conformance.
* **Security & Vulnerability Remediation**:
  - Updated `certifi >= 2026.10.19` resolving the eMudhra / emSign CA security advisory (GHSA-6q48-6c7w-9gw2).

## v0.5.1 (2026-09-20)

### Fixes & Reliability
* **GitHub Action `skip-hooks` Input (`action.yml`)**: Added `skip-hooks` input (default: `hexaqual-agents`) to the reusable `TheTrueSCU/hexaqual` GitHub Action. The `SKIP` environment variable is now passed to `pre-commit run --all-files` in CI, preventing the `hexaqual-agents` hook from failing on clean checkouts where synced agent assets are absent from `.gitignore` by design. Consumers requiring no-skip behaviour can pass `skip-hooks: ""` explicitly.

## v0.5.0 (2026-09-19)

### Highlights & Features
* **Universal AI Guardrails & Agent Management (`hexaqual agents`)**: Introduced a first-class subsystem to bundle, synchronize, audit, and inspect shared `.agents/` rules, workflows, and skills across repositories (`sync`, `check`, `list`).
* **Bundled Universal Assets**: Packaged 9 universal rules (`hexaqual-boundaries`, `hexaqual-test-authoring`, `hexaqual-hermetic-testing`, `hexaqual-docstrings`, `hexaqual-workspace`, `hexaqual-typing`, `hexaqual-property-testing`, `hexaqual-security`, `hexaqual-sync`), 6 SDLC-aligned workflows (`hexaqual-pre-commit`, `hexaqual-pre-push`, `hexaqual-pre-release`, `hexaqual-scaffold-unit`, `hexaqual-mutation`, `hexaqual-sync`), and 3 agent skills (`hexaqual_audit_complexity.py`, `hexaqual_audit_docstrings.py`, `hexaqual_scaffold_test_parity.py`).
* **Repo-Specific Asset Preservation**: Strict preservation of local unmanaged rules (`hexa<X>-*.md`, `graphify.md`), ensuring individual family members can layer domain constraints without clobbering upstream standards.
* **Modular Pre-Commit Hook (`hexaqual-agents`)**: Added pre-commit gate verifying that managed assets in `.agents/` remain byte-for-byte identical to the installed `hexaqual` distribution.
* **Root `AGENTS.md` Index & Git Exclusion**: Automatically generates and refreshes an aggregated `AGENTS.md` index at repository root and registers it in `.git/info/exclude` to support single-file agent tools without git clutter.
* **SDLC-Aligned Gate Names**: Renamed pre-flight workflows to `hexaqual-pre-commit`, `hexaqual-pre-push`, and `hexaqual-pre-release` to create intuitive symmetry with git hook lifecycles.

### Fixes & Reliability
* **Fast Pre-Commit Sanity Execution**: Fixed CLI wrapper argument forwarding so `--skip-tests` dynamically bypasses pytest in `hexaqual sanity -a --skip-tests`, reducing pre-commit runtime from ~97s to <1s.
* **Documentation Link Checking in Code Spans**: Filtered out inline backtick code spans in `hexaqual docs links` to prevent false positive link parsing on Python generic syntax like `[T](item: T)`.

## v0.4.2 (2026-09-17)

### Fixes & Reliability
* **Graceful Graphviz Skip in Diagram Checks**: Gracefully skip diagram verification (`hexaqual deps pydeps --check`, `GeneratePydepsHandler`, `check_package_diagram`, `check_overview_diagram`, `check_all_diagrams`) with `SKIP` status and exit code 0 when Graphviz `dot` executable is absent from the host environment, preventing pre-commit and CI crashes on minimal containers.

## v0.4.1 (2026-09-17)

### Highlights & Features
* **Architecture Diagram Freshness Gate (`hexaqual-diagrams`)**: Introduced automated architecture diagram verification and synchronization via `hexaqual deps pydeps --check` / `--fix`, integrated into `hexaqual sanity` static checks and exposed as a modular pre-commit hook (`hexaqual-diagrams`).
* **Conditional Diagram Skip**: Automatically skips diagram verification cleanly (`CheckStatus.SKIP`) if Graphviz `dot` is absent or if no `docs/assets/pydeps/` directory exists.
* **Sanity Step Control (`--skip-diagrams`)**: Added dynamic `--skip-diagrams` workflow option to `hexaqual check` and `hexaqual sanity`.

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
