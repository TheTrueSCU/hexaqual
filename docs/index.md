# Hexaqual

> **Universal Python quality gates, architectural boundary enforcement, and release engineering toolchain.**

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green.svg)](https://github.com/TheTrueSCU/hexaqual/blob/main/LICENSE)
[![Architecture: Hexagonal](https://img.shields.io/badge/architecture-hexagonal-emerald.svg)](architecture.md)
[![Sanity: <11s](https://img.shields.io/badge/sanity--gate-11s-purple.svg)](cli-reference.md)

---

## 🌟 Why Hexaqual?

Standard formatters and linters (Ruff, Flake8, Black) ensure syntactic style, but they cannot detect **architectural erosion**:
- Did a core domain model accidentally import a database adapter?
- Did a developer add a 500-line service module without a matching unit test suite?
- Are optional extras declared in subpackages failing to forward into the umbrella package?
- Is `__all__` unsorted or leaking private symbols?
- Can your wheel distribution packages build byte-for-byte reproducibly?

**Hexaqual** provides unified governance and automated architectural assertions across monorepos and standalone Python packages in a fast, turnkey CLI and pre-commit toolsuite:

```mermaid
graph TD
    subgraph primary_adapters ["Driving Adapters (Inbound)"]
        CLI["Typer CLI (hexaqual ...)"]
        Hooks["Pre-Commit Hooks (.pre-commit-hooks.yaml)"]
        Action["GitHub Action (TheTrueSCU/hexaqual@v1)"]
    end

    subgraph orchestration ["Orchestration & Governance Core"]
        Sanity["Sanity Gate (Ruff + Ty + Complexipy + Tests)"]
        Parity["Parity Verifier (Test Symmetry, Extras, Boundaries)"]
        Statements["__all__ Integrity & Casefold Sorter"]
        Imports["Import-Linter Boundary Enforcer"]
        Mutate["Mutation Testing & Coverage Correlation"]
        Release["Reproducible Release Engine & PyPI Publisher"]
        GH["GitHub PR & CI Diagnostics Dashboard"]
    end

    subgraph driven_adapters ["Driven Adapters (Outbound)"]
        RichUI["Rich Terminal Dashboards"]
        Formats["JSON & Markdown Presenters"]
        Subproc["Subprocess Runners (Ty, Ruff, Mutmut, Pytest)"]
        GhAPI["GitHub REST & GraphQL API"]
        PyPiAPI["PyPI Publishing & Verification"]
    end

    CLI --> orchestration
    Hooks --> CLI
    Action --> CLI

    orchestration --> RichUI
    orchestration --> Formats
    orchestration --> Subproc
    orchestration --> GhAPI
    orchestration --> PyPiAPI
```

---

## ⚡ Core Capabilities

- **🚀 Sub-11s Monorepo Sanity**: Validates code style, static types (`ty`), cognitive complexity (`complexipy`), `__all__` sorting, test parity, and unit test suites across 17 packages in seconds.
- **📐 Architectural Boundary Enforcement**: Verifies strict hexagonal layers (`domain` never imports `adapters`; `adapters` never import `infra`) via `import-linter`.
- **🧪 1:1 Test Parity**: Guarantees that every `src/<pkg>/<path>.py` file has a matching `tests/unit/<path>/test_<name>.py` and dedicated `test_hexagonal_boundaries.py` architectural suites.
- **🧬 Mutation Testing & Coverage Correlation**: Drives `mutmut` mutation testing and correlates surviving mutants directly with line coverage data.
- **📦 Reproducible Packaging**: Builds sdist/wheels, audits metadata integrity, verifies byte-for-byte reproducibility, and publishes to PyPI skipping existing releases.
- **🔍 GitHub & PR Intelligence**: Live PR inspection dashboards, check-run summaries, CodeQL scanning alert triage, and Dependabot security audits.

---

## 🚀 Quickstart

Install Hexaqual with `uv`:

```bash
# Add as dev dependency
uv add --dev hexaqual[all]

# Or run instantly with uvx
uvx hexaqual sanity
```

Run a fast scoped sanity check on a specific package:

```bash
uv run hexaqual sanity -p my_package
```

Or run the full workspace quality gate:

```bash
uv run hexaqual sanity -a --skip-tests
```

---

## 📖 Explore the Documentation

- [Architecture & Design](architecture.md) — Hexagonal layers, CQRS dispatching, and design invariants.
- [CLI Command Catalog](cli-reference.md) — Comprehensive command and flag documentation.
- [AI Agent Governance](agents-guide.md) — Universal `.agents/` rules, workflows, skills, and VCS hygiene.
- [Pre-Commit Integration](pre-commit-guide.md) — Setting up fast pre-commit hooks.
- [CI/CD & GitHub Actions](ci-cd-integration.md) — Automated PR quality gates, reproducible builds, and OpenSSF Gold workflows.
