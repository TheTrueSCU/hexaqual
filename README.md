# 🛡️ Hexaqual

[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-Hexaqual%20Quality%20Gate-blue.svg?logo=github&style=flat)](https://github.com/marketplace/actions/hexaqual-quality-gate)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/TheTrueSCU/hexaqual)
[![CI](https://github.com/TheTrueSCU/hexaqual/actions/workflows/ci.yml/badge.svg)](https://github.com/TheTrueSCU/hexaqual/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/github/TheTrueSCU/hexaqual/graph/badge.svg)](https://codecov.io/github/TheTrueSCU/hexaqual)
[![PyPI: hexaqual](https://img.shields.io/pypi/v/hexaqual.svg)](https://pypi.org/project/hexaqual/)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

[![Governs Hexastack](https://img.shields.io/badge/governs-hexastack-blueviolet.svg)](https://dopplereffect.us/hexastack/)
[![Governs Hexaqueue](https://img.shields.io/badge/governs-hexaqueue-blue.svg)](https://dopplereffect.us/hexaqueue/)
[![Governs Hexaflow](https://img.shields.io/badge/governs-hexaflow-0284c7.svg)](https://dopplereffect.us/hexaflow/)
[![Powered by Hexaflow](https://img.shields.io/badge/powered%20by-hexaflow-0284c7.svg)](https://dopplereffect.us/hexaflow/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checker: ty](https://img.shields.io/badge/type%20checker-ty-blueviolet.svg)](https://github.com/astral-sh/ty)

[![OpenSSF Scorecard](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.scorecard.dev%2Fprojects%2Fgithub.com%2FTheTrueSCU%2Fhexaqual&query=%24.score&label=OpenSSF%20Scorecard&color=blue)](https://securityscorecards.dev/viewer/?uri=github.com/TheTrueSCU/hexaqual)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/14749/badge)](https://www.bestpractices.dev/projects/14749)
[![OpenSSF Best Practices: Progress](https://img.shields.io/cii/percentage/14749?label=OpenSSF%20Best%20Practices%3A%20Progress)](https://www.bestpractices.dev/projects/14749)

> 🛡️ **Universal quality & governance engine for [Hexastack](https://dopplereffect.us/hexastack/), [Hexaqueue](https://dopplereffect.us/hexaqueue/), and [Hexaflow](https://dopplereffect.us/hexaflow/)** · 🌊 **Execution DAGs powered by [Hexaflow](https://dopplereffect.us/hexaflow/)**


> **Universal Python quality gates, architectural boundary enforcement, and release engineering toolchain.**

Hexaqual provides an opinionated, high-velocity quality harness designed for modular Python architectures, monorepos, and single-package projects. It unifies linting, type-checking, cognitive complexity enforcement, `__all__` integrity, 1:1 test symmetry, and automated PyPI release workflows into a cohesive, workflow-driven developer CLI.

---

## 🚀 Key Features

* **Workflow-Driven Sanity Checks**: Multi-stage DAG pipeline powered by [Hexaflow](https://pypi.org/project/hexaflow/) for parallel linting, typechecking, and testing.
* **Turnkey GitHub Marketplace Action**: Drop-in composite action setting up Python, `uv`, pre-commit caching, and executing quality checks in CI.
* **Architectural Invariants**: First-class support for hexagonal layer enforcement (`domain`, `ports`, `adapters`, `infra`).
* **Test Parity Enforcement**: 1:1 symmetry verification between source modules and unit test suites.
* **Public API Integrity**: Automatic sorting, deduplication, and AST validation of `__all__` exports.
* **Smart PyPI Publishing**: Dependency-ordered, reproducible builds with automatic skip-if-exists checks.

---

## ⚡ GitHub Marketplace Action

Hexaqual is available on the [GitHub Marketplace](https://github.com/marketplace/actions/hexaqual-quality-gate) as a turnkey composite action that automatically sets up `uv`, Python, caches pre-commit environments, and runs your checks:

```yaml
jobs:
  quality-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: TheTrueSCU/hexaqual@v0.4.0
        with:
          mode: "pre-commit" # options: 'pre-commit', 'sanity', 'setup'
          sync-args: "--all-extras --dev"
```

---

## 📦 Installation

```bash
# Add as a development dependency
uv add --dev hexaqual

# Or install globally
uv tool install hexaqual
```

---

## 🛠️ Unified CLI (`hexaqual`)

Hexaqual subsumes all developer quality tools into a single unified entrypoint (`hexaqual`). It dynamically detects workspace layout:
- **Multi-package workspaces** (`packages/` exists): accepts `-p` / `--package` to filter focus across packages, or `-a` / `--all` for the whole workspace.
- **Single-package projects** (no `packages/`): automatically focuses on the root package without requiring `-p`.
- **Examples support**: if an `examples/` directory exists, `-e` / `--example` allows targeted auditing of example projects.

### Command Overview

| Command | Subcommands | Description |
|---|---|---|
| `hexaqual check` (alias: `sanity`) | — | Run the multi-stage quality pipeline (Ruff, Ty, Complexipy, `__all__`, test parity, pytest). |
| `hexaqual statements` | `check`, `fix` | Audit and auto-format `__all__` exports with strict casefold sorting. |
| `hexaqual parity` | `test`, `extras` | Audit 1:1 symmetry between source modules and unit tests, and optional extras forwarding. |
| `hexaqual test` | `run`, `boundary`, `redundancy`, `impact`, `fuzz`, `snapshot`, `archon` | Run pytest suites, boundary assertion audits, redundancy analysis, git impact tests, fuzzing, and inline snapshots. |
| `hexaqual mutate` | `run`, `inspect` | Dual-engine mutation testing (pytest-gremlins & mutmut) with auto-parallelism and triage inspection. |
| `hexaqual hooks` | `install`, `check`, `uninstall`, `commit-msg` | Multi-stage Git hooks lifecycle management (pre-commit, commit-msg, pre-push, post-merge, post-checkout). |
| `hexaqual release` | `build`, `check`, `publish`, `reproducible` | Build sdist/wheel distributions, verify metadata, and publish to PyPI with smart duplicate skipping. |
| `hexaqual gh` | `pr`, `checks`, `repo`, `security`, `code-scanning`, `codeql` | Inspect PR health dashboards, CI checks, repo governance, Dependabot, and CodeQL alerts. |
| `hexaqual deps` | `audit`, `deptry`, `graph` | Audit dependencies, run deptry checks, and generate dependency graphs via pydeps. |
| `hexaqual imports` | `check`, `generate` | Verify and generate import-linter contracts for hexagonal boundary enforcement. |
| `hexaqual refactor` | `alphabetize`, `rename`, `extract`, `move`, `run` | Automated code refactoring and AST-level symbol alphabetization via Rope. |
| `hexaqual docs` | `usage`, `publish` | Verify/regenerate USAGE.md catalogs and publish Medium articles. |
| `hexaqual agents` | `sync`, `check`, `list` | Synchronize and verify universal `.agents` guardrails (rules, workflows, skills). |
| `hexaqual complexity` | — | Audit cognitive complexity across functions and methods via complexipy. |

```bash
# Run sanity checks on specific packages in a workspace
hexaqual check -p core -p cqrs

# Run sanity check with auto-formatting on a single-package repo
hexaqual check --fix

# Audit __all__ integrity across all packages
hexaqual statements check

# Run pytest on tests impacted by recent git changes
hexaqual test impact

# Examine a GitHub Pull Request dashboard with live polling
hexaqual gh pr 42 --watch

# Verify USAGE.md catalog is up to date
hexaqual docs usage --check
```

For the complete unrolled CLI reference and full option listings for every subcommand, see [USAGE.md](USAGE.md).

---

## 🪝 Git Lifecycle Hooks & Commit Governance

Standard `pre-commit install` only installs the `pre-commit` stage by default. Hexaqual provides a unified hooks manager that configures all **5 critical lifecycle stages** in a single step:

```bash
# Install all 5 hook stages (pre-commit, commit-msg, pre-push, post-merge, post-checkout)
uv run hexaqual hooks install

# Inspect active hook status across all stages
uv run hexaqual hooks check
```

| Hook Stage | Trigger | Purpose |
|---|---|---|
| **`pre-commit`** | `git commit` | Fast static quality checks (Ruff, Ty, complexipy, `__all__`, test symmetry). |
| **`commit-msg`** | `git commit` | Validates Conventional Commits and OpenSSF DCO sign-offs (`Signed-off-by:`). |
| **`pre-push`** | `git push` | Fast regression sanity gate preventing broken builds from reaching remote CI. |
| **`post-merge`** | `git pull` / merge | Auto-syncs dependencies (`uv sync`) and re-synchronizes universal agent rules. |
| **`post-checkout`** | `git switch` | Auto-syncs dependencies and agent guardrails on branch changes. |

### Pre-Commit Configuration (`.pre-commit-config.yaml`)

Hexaqual distributes reusable hooks via GitHub:

```yaml
repos:
  - repo: https://github.com/TheTrueSCU/hexaqual
    rev: v0.8.0
    hooks:
      - id: hexaqual-sanity        # Fast static sanity gate (Ruff, Ty, complexipy, etc.)
      - id: hexaqual-architecture  # Verify test_hexagonal_boundaries.py suites
      - id: hexaqual-agents        # Verify .agents/ assets match installed hexaqual
      - id: hexaqual-agents-sync   # Auto-sync .agents/ on post-merge and post-checkout
      - id: hexaqual-commit-msg    # Enforce Conventional Commits & DCO on commit-msg
      - id: hexaqual-pre-push      # Run fast sanity check on pre-push
```

---

## 🧬 Dual-Engine Mutation Testing

Hexaqual implements a high-velocity **dual-engine mutation testing harness**:

1. **`pytest-gremlins` (Default)**: In-process AST mutation engine targeting executable boundary conditions (`<` vs `<=`, `and` vs `or`, arithmetic, returns). Delivers **100% actionable signal** with decoupled multicore scaling:
   - `-n auto`: Parallel baseline pytest execution via `pytest-xdist`.
   - `-w auto`: Parallel in-process mutation workers (`--gremlin-workers`).
   - `--batch-size 10`: Batched mutant execution (`--gremlin-batch`).
   - `-A` / `--affected`: Scopes mutation testing strictly to packages impacted by `git diff`.
2. **`mutmut`**: Subprocess-isolated deep mutation auditor for literal constants, token shifts, and pre-release audits.

```bash
# High-velocity developer loop: multicore auto-scaled boundary mutations
uv run hexaqual mutate run -p <pkg> -e gremlins -w auto --batch-size 10 -n auto

# Scoped to affected packages only (ideal for PR CI verification)
uv run hexaqual mutate run -A -e gremlins -w auto

# Deep literal constant audit
uv run hexaqual mutate run -p <pkg> -e mutmut

# High-level triage summary of surviving mutants (Critical, Equivalent, Ignorable)
uv run hexaqual mutate inspect -s

# Actionable critical mutants only
uv run hexaqual mutate inspect -p <pkg> -act
```

---

## 🐕 Dogfooding Hexaflow: Workflows as Architecture

Hexaqual serves as the primary real-world dogfooding ground for [Hexaflow](https://pypi.org/project/hexaflow/), demonstrating how lightweight, in-memory workflow DAGs can orchestrate high-performance developer tooling without complexity or latency.

### The Sanity Workflow DAG
Rather than executing checks in a rigid, monolithic sequence or maintaining ad-hoc shell orchestration, `hexaqual sanity` compiles each target's verification into a declarative `hexaflow.Workflow`:

```mermaid
graph LR
    subgraph stage1 ["Stage 1: Leaf Static Checks"]
        Lint["Ruff Lint & Format"]
        Statements["__all__ Integrity"]
        Parity["1:1 Test Symmetry"]
    end

    subgraph stage2 ["Stage 2: Static Analysis"]
        Typecheck["Ty Typecheck"]
        Complexity["Cognitive Complexity <= 25"]
    end

    subgraph stage3 ["Stage 3: Dynamic Verification"]
        Pytest["Pytest Test Suites"]
    end

    Lint --> Typecheck
    Statements --> Typecheck
    Parity --> Complexity
    Typecheck --> Pytest
    Complexity --> Pytest
```

### Why Dogfooding Hexaflow Matters:
1. **Deterministic Staging & Fail-Fast**: Ultra-fast leaf AST checks (Ruff, `__all__`, test symmetry) execute in Stage 1 (~0.05s), providing immediate feedback before heavier static analysis (Ty, complexipy) or test suites run.
2. **Granular Step Checkpoints**: Each verification step executes within a discrete `StepContext`, recording execution metrics, structured findings, and pass/fail states into an `InMemoryStateStore`.
3. **Zero-Latency Overhead**: Hexaflow's minimal runtime footprint adds virtually zero overhead—the entire 5-stage static check pipeline runs in under **0.6 seconds**.
4. **Resilient Error Isolation**: If a step fails, the workflow gracefully preserves partial reports, enabling the Rich presenter to render complete multi-target dashboards showing exact failure context.

---

## 🤖 Universal AI Guardrails & Agent Management (`.agents/`)

Hexaqual acts as the single source of truth for AI pair programming assistants (Antigravity CLI, Cursor, Claude Code, Windsurf) across the entire `hexa-` family (`hexastack`, `hexaqueue`, `hexaflow`, `hexaqual`).

It implements a **Two-Tier Architecture**:
1. **Universal Guardrails (Managed by `hexaqual`)**: Bundled rules (`hexaqual-*.md`), workflows (`hexaqual-*.md`), and skills (`hexaqual_*.py`) that apply universally across every repository.
2. **Family-Member Guardrails (Local to `X`)**: Repository-specific rules (`hexa<X>-*.md`) that define project-specific invariants (e.g., `hexaqueue-elevation.md`, `hexaflow-dag-invariants.md`). These local assets are preserved untouched during synchronizations.

### Bundled Universal Catalog

| Category | File | Description |
|---|---|---|
| **Rule** | `hexaqual-boundaries.md` | Enforce hexagonal layer isolation (`domain/` -> `ports/` -> `adapters/` -> `infra/`). |
| **Rule** | `hexaqual-test-authoring.md` | 1:1 test parity, `__init__.py` mirroring, pure ABC port mocking, side-effect-free assertions. |
| **Rule** | `hexaqual-hermetic-testing.md` | Hermetically sealed test fixtures, `tmp_path`, zero global state or socket pollution. |
| **Rule** | `hexaqual-docstrings.md` | Mandatory Google docstrings with `Args:`, `Returns:`, `Raises:`, and `Notes/Architectural Intent:`. |
| **Rule** | `hexaqual-workspace.md` | Monorepo hierarchy, subpackage import boundaries, casefold-sorted `__all__` exports. |
| **Rule** | `hexaqual-typing.md` | Python 3.13 generic syntax (`class C[T]:`), zero bare `Any` across domain boundaries. |
| **Rule** | `hexaqual-property-testing.md`| Hypothesis stateful fuzzing (`RuleBasedStateMachine`) for state machines and schedulers. |
| **Rule** | `hexaqual-security.md` | Prohibition of `shell=True`, path traversal guards, secret scanning, least-privilege defaults. |
| **Rule** | `hexaqual-sync.md` | Guardrail invariant to execute `hexaqual agents sync` upon dependency upgrades. |
| **Workflow** | `hexaqual-pre-commit.md` | Fast pre-commit gate (`hexaqual sanity -a --skip-tests`, docs freshness, agent sync). |
| **Workflow** | `hexaqual-pre-push.md` | Full pre-push gate: format drift -> sanity with tests -> graphify -> pre-commit hooks. |
| **Workflow** | `hexaqual-pre-release.md`| Pre-release packaging audit, doc freeze, PyPI availability, reproducible wheel check. |
| **Workflow** | `hexaqual-scaffold-unit.md` | Scaffold domain entity, port, adapter, and mirrored unit test file. |
| **Workflow** | `hexaqual-mutation.md` | Targeted mutation analysis and actionable mutant triage. |
| **Workflow** | `hexaqual-sync.md` | Synchronize shared agent guardrails from installed `hexaqual`. |
| **Skill** | `hexaqual_audit_complexity.py`| Fast function cognitive complexity linter (<= 25 via `complexipy`). |
| **Skill** | `hexaqual_audit_docstrings.py`| AST docstring auditor checking for Google docstrings & Architectural Intent. |
| **Skill** | `hexaqual_scaffold_test_parity.py`| Git-aware test mirror and `__init__.py` scaffolding helper. |

### CLI Synchronization & Drift Verification

```bash
# Synchronize universal guardrails to current repository (preserves local hexaX-* rules)
uv run hexaqual agents sync

# Dry-run simulation of synchronization
uv run hexaqual agents sync --dry-run

# Verify repository guardrails match the installed hexaqual version (pre-commit gate)
uv run hexaqual agents check

# List all universal bundled rules, workflows, and skills
uv run hexaqual agents list
```

### Root Pointer (`AGENTS.md`) & Dynamic Reloading

- **Aggregated Index**: `hexaqual agents sync` creates a root `AGENTS.md` indexing all active rules, workflows, and skills (both universal `hexaqual-*` and project-specific `hexa<X>-*` assets). This ensures single-file agent tools (like GitHub Copilot Workspace) maintain full context.
- **VCS Hygiene**: `hexaqual agents sync` ensures `.gitignore` excludes `.agents/*/hexaqual-*` so upstream assets are never committed to git. Maintainers may commit `AGENTS.md` for GitHub visibility or add it to local `.git/info/exclude` to keep the root directory clean.
- **Per-Turn Dynamic Reloading**: In Antigravity CLI/IDE, rule files under `.agents/rules/` and `AGENTS.md` are dynamically reloaded at the start of each user prompt, so synced guardrails take effect immediately on the next interaction.

---

## 🏛️ Architecture & Documentation

- **[Architecture & Design Guide](docs/architecture.md)**: Hexagonal boundaries, CQRS command bus, and architectural invariants.
- **[AI Agent Governance Guide](docs/agents-guide.md)**: Universal `.agents/` rules, SDLC workflows, colocated skills, and VCS hygiene.
- **[CLI Reference Catalog](USAGE.md)**: Full unrolled command and subcommand trees with exhaustive option listings.

---

## 📄 License

Apache-2.0. See [LICENSE](LICENSE) for details.
