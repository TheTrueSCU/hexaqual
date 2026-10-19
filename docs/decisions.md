# Architectural Decision Records (ADRs) & Infrastructure Invariants

> **Scope**: Authoritative historical log of foundational architectural decisions, structural constraints, and quality invariants governing **Hexaqual** and its developer governance toolchain.
>
> This document captures **why** specific paradigms were chosen, **what was rejected**, and the **machine gates** that physically prevent architectural drift. It serves as persistent memory across release cycles and AI pair-programming sessions.

---

## Decision Index

| ADR ID | Title | Date / Milestone | Status | Key Invariant |
|---|---|---|---|---|
| [**ADR-001**](#adr-001-pure-hexagonal-layer-isolation--zero-io-domain-logic) | Pure Hexagonal Layer Isolation & Zero-I/O Domain Logic | 2026-08-25 (`v0.1.0`) | **Accepted** | `domain/` has 0 external dependencies and 0 disk I/O; enforced via `import-linter`. |
| [**ADR-002**](#adr-002-dynamic-multi-format-presenter-decoupling-rich-json-markdown) | Dynamic Multi-Format Presenter Decoupling (Rich, JSON, Markdown) | 2026-09-01 (`v0.2.0`) | **Accepted** | Core analyzers return pure domain reports; formatters decoupled into dedicated presenter ports. |
| [**ADR-003**](#adr-003-hexaflow-dag-orchestration-for-multi-stage-quality-pipelines) | Hexaflow DAG Orchestration for Multi-Stage Quality Pipelines | 2026-09-10 (`v0.2.5`) | **Accepted** | Complex multi-stage checks (`sanity`, `release`) orchestrated via acyclic dependency graphs. |
| [**ADR-004**](#adr-004-anti-fake-pass-exercise-gates--boundary-mutation-auditing) | Anti-Fake-Pass Exercise Gates & Boundary Mutation Auditing | 2026-10-18 (`v0.9.1`) | **Accepted** | Zero test collection is a fatal failure; mutation testing audits assertion efficacy. |
| [**ADR-005**](#adr-005-anti-drift-prose-linting--zero-token-knowledge-graph-guardrails) | Anti-Drift Prose Linting & Zero-Token Knowledge Graph Guardrails | 2026-10-19 (`v0.9.1`) | **Accepted** | Documentation metrics must match code truth via `hexaqual docs drift`; graphify tracks AST. |

---

### ADR-001: Pure Hexagonal Layer Isolation & Zero-I/O Domain Logic

- **Date & Milestone**: 2026-08-25 (`v0.1.0`)
- **Status**: Accepted
- **Context & Problem Statement**:
  Quality assurance, linter runners, and AST-parsing tools frequently mix terminal output formatting, subprocess invocations, and filesystem traversal directly into core analysis logic. This results in brittle, untestable tools where testing an analysis check requires spinning up mock directories and inspecting stdout strings.
- **Decision**:
  Enforce strict 4-tier Hexagonal layer boundaries:
  - `domain/`: Pure business models, data objects, and logic with **0** external framework dependencies and **0** disk/subprocess I/O.
  - `ports/`: Pure abstract base interfaces (`abc.ABC`) defining analyzers, runners, publishers, and presenters.
  - `adapters/`: Concrete technological implementations (AST parsing, Git interactions, Rich formatting, PyPI HTTP client, pytest/ruff runners).
  - `infra/`: Dispatchers, bootstrap orchestration, and handler registries.
  - `cli/`: Typer command dispatchers that parse arguments and invoke application handlers.
- **The Invariant ("The Why")**:
  Domain models must remain completely decoupled from how code is parsed, how git commits are retrieved, and how results are styled in terminal emulators.
- **Alternatives Considered & Rejected**:
  - *Direct CLI-to-subprocess execution*: Putting `subprocess.run(["ruff", ...])` directly in Typer functions. Rejected because it precludes reusability, programmatic testing, and multi-format outputs.
- **Enforcement Mechanism**:
  - Enforced by `[tool.importlinter]` via `uv run hexaqual deps linter`.
  - Directional dependency checks verified by pre-commit hooks.

---

### ADR-002: Dynamic Multi-Format Presenter Decoupling (Rich, JSON, Markdown)

- **Date & Milestone**: 2026-09-01 (`v0.2.0`)
- **Status**: Accepted
- **Context & Problem Statement**:
  Developers working locally require interactive, beautifully formatted terminal tables with color and icons (via Rich), whereas CI runners and autonomous agents require structured JSON or Markdown summaries for pull request comments and automated triage. Hardcoding Rich tables in analysis routines prevents machine consumption.
- **Decision**:
  Decouple all presentation logic into dedicated Presenter ports (`GeneratorPresenterPort`, `GovernancePresenterPort`, etc.). Analysis commands return structured domain reports (`DocDriftReport`, `GateInventoryReport`, `SanityReport`). Presenter adapters format these reports into Rich tables, JSON payloads, or Markdown tables based on user-supplied flags (`--json`, `--markdown`).
- **The Invariant ("The Why")**:
  Core analysis engines never emit ANSI escape codes or print directly; they return structured domain reports consumed by dedicated presenters.
- **Alternatives Considered & Rejected**:
  - *Regex scraping CLI stdout for JSON*: Rejected due to high fragility and terminal encoding corruption.
- **Enforcement Mechanism**:
  - 1:1 unit test parity for all presenters across Rich, JSON, and Markdown.

---

### ADR-003: Hexaflow DAG Orchestration for Multi-Stage Quality Pipelines

- **Date & Milestone**: 2026-09-10 (`v0.2.5`)
- **Status**: Accepted
- **Context & Problem Statement**:
  End-to-end quality checks (`hexaqual sanity`, pre-commit gates, and release verifications) require orchestrating multiple independent tools (Ruff, Ty, complexipy, statement sorter, test parity, and pytest). Sequential imperative scripts become unwieldy, difficult to time, and incapable of structured failure handling.
- **Decision**:
  Compose multi-stage pipelines as directed acyclic graphs (DAGs) using `hexaflow>=0.4.0`. Each check or task is a distinct step in the DAG with explicit input/output contracts.
- **The Invariant ("The Why")**:
  Complex quality workflows must be declaratively modeled, observable, and independently introspectable without procedural script spaghetti.
- **Alternatives Considered & Rejected**:
  - *Ad-hoc bash scripts or procedural Python functions*: Rejected due to lack of standard telemetry, dependency visualization, and structured compensation handling.
- **Enforcement Mechanism**:
  - `tests/integration/test_cli_sanity.py` and Hexaflow step validation suites.

---

### ADR-004: Anti-Fake-Pass Exercise Gates & Boundary Mutation Auditing

- **Date & Milestone**: 2026-10-18 (`v0.9.1`)
- **Status**: Accepted
- **Context & Problem Statement**:
  Test runners frequently succeed erroneously when a filter or path mistake causes pytest to collect zero tests, returning exit code 5. In CI pipelines, this results in a green checkmark despite zero tests executing. Furthermore, unit tests often achieve 100% line coverage while containing zero meaningful assertions ("fake pass").
- **Decision**:
  Enforce two strict exercise gates:
  1. `hexaqual test run` treats pytest exit code 5 (0 tests collected) as an immediate fatal error unless `--allow-empty` is explicitly passed.
  2. `hexaqual mutate run` executes mutation testing (via `pytest-gremlins` and `mutmut`) to audit whether test suites actively assert boundary conditions and reject mutants.
- **The Invariant ("The Why")**:
  A test suite that runs zero tests or fails to kill boundary mutants must not pass CI. Line coverage alone is insufficient; assertion efficacy is mandatory.
- **Alternatives Considered & Rejected**:
  - *Ignoring pytest exit code 5*: Rejected because silent test skips have repeatedly allowed critical regressions to slip into production.
- **Enforcement Mechanism**:
  - Pytest runner interceptor in `hexaqual.adapters.code_analysis.pytest_runner`.
  - Mutation test auditing via `hexaqual mutate inspect`.

---

### ADR-005: Anti-Drift Prose Linting & Zero-Token Knowledge Graph Guardrails

- **Date & Milestone**: 2026-10-19 (`v0.9.1`)
- **Status**: Accepted
- **Context & Problem Statement**:
  As repositories scale and undergo frequent refactorings, documentation inevitably lies. Version badges lag behind `pyproject.toml`, cited subpackage inventories become stale, and dead file links accumulate. In AI-assisted workflows, hallucinated documentation causes severe context amnesia and agent drift.
- **Decision**:
  Implement automated documentation verification and knowledge graph synchronization:
  1. `hexaqual docs drift`: Performs AST-level deterministic scanning across all repository markdown files to verify that version badges, package counts, and file references match source manifests.
  2. `graphify`: Maintains a persistent AST knowledge graph (`graphify-out/`) updated with 0 LLM token cost on each code change to preserve ground-truth topological call paths.
- **The Invariant ("The Why")**:
  Documentation is code. If documentation asserts a package count, version badge, or architecture invariant that contradicts the codebase, the build must fail.
- **Alternatives Considered & Rejected**:
  - *Manual markdown review*: Rejected as completely ineffective across fast-moving multi-package codebases.
- **Enforcement Mechanism**:
  - `hexaqual docs drift` executed in CI.
  - Pre-push hook verification and gate inventory audit.
