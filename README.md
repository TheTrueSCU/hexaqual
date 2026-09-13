# 🛡️ Hexaqual

[![PyPI version](https://img.shields.io/pypi/v/hexaqual.svg)](https://pypi.org/project/hexaqual/)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

> **Universal Python quality gates, architectural boundary enforcement, and release engineering toolchain.**

Hexaqual provides an opinionated, high-velocity quality harness designed for modular Python architectures, monorepos, and single-package projects. It unifies linting, type-checking, cognitive complexity enforcement, `__all__` integrity, 1:1 test symmetry, and automated PyPI release workflows into a cohesive, workflow-driven developer CLI.

---

## 🚀 Key Features

* **Workflow-Driven Sanity Checks**: Multi-stage DAG pipeline powered by [Hexaflow](https://pypi.org/project/hexaflow/) for parallel linting, typechecking, and testing.
* **Architectural Invariants**: First-class support for hexagonal layer enforcement (`domain`, `ports`, `adapters`, `infra`).
* **Test Parity Enforcement**: 1:1 symmetry verification between source modules and unit test suites.
* **Public API Integrity**: Automatic sorting, deduplication, and AST validation of `__all__` exports.
* **Smart PyPI Publishing**: Dependency-ordered, reproducible builds with automatic skip-if-exists checks.

---

## 📦 Installation

```bash
# Add as a development dependency
uv add --dev hexaqual

# Or install globally
uv tool install hexaqual
```

---

## 🛠️ Basic Usage

```bash
# Run the complete sanity check pipeline
hexaqual check

# Audit and auto-format __all__ statements
hexaqual statements fix

# Audit test suite parity
hexaqual parity check
```

---

## 📄 License

Apache-2.0. See [LICENSE](LICENSE) for details.
