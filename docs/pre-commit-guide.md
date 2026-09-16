# ⚡ Pre-Commit Quality Gate Integration

Hexaqual provides first-class pre-commit hooks that shift architectural enforcement, test symmetry validation, and typechecking left to developer machines before commits reach GitHub.

---

## 🚀 Quick Setup

In your repository root, configure `.pre-commit-config.yaml`:

```yaml
repos:
  # 1. Standard Git & Syntax Hooks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-added-large-files
      - id: check-case-conflict
      - id: check-merge-conflict
      - id: check-yaml
      - id: check-toml
      - id: end-of-file-fixer
      - id: trim-trailing-whitespace

  # 2. Ruff (Fast Linting and Formatting)
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.7
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  # 3. Hexaqual Unified Architecture & Quality Gate
  - repo: https://github.com/TheTrueSCU/hexaqual
    rev: v0.3.0
    hooks:
      - id: hexaqual-sanity
        name: hexaqual sanity check
        entry: uv run hexaqual sanity -a --skip-tests --skip-lint
        language: system
        pass_filenames: false
```

Install and run pre-commit:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

---

## 🧰 Modular Hook Menu

Hexaqual provides specialized, granular pre-commit hooks that can be invoked individually:

### 1. `hexaqual-sanity`
The all-in-one fast quality gate. Evaluates Ty typechecking, cognitive complexity (`complexipy`), `__all__` integrity, and test parity in parallel.

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.3.0
  hooks:
    - id: hexaqual-sanity
```

### 2. `hexaqual-statements`
Validates that all `__all__` export arrays are sorted alphabetically in casefold order and deduplicated.

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.3.0
  hooks:
    - id: hexaqual-statements
```

### 3. `hexaqual-test-parity`
Guarantees 1:1 structural symmetry between source modules in `src/` and unit test suites in `tests/unit/`.

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.3.0
  hooks:
    - id: hexaqual-test-parity
```

### 4. `hexaqual-architecture`
Verifies that all internal subpackages maintain dedicated `test_hexagonal_boundaries.py` architectural test suites.

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.3.0
  hooks:
    - id: hexaqual-architecture
```

### 5. `hexaqual-extras`
Audits subpackage optional dependencies to ensure they are properly forwarded to umbrella package definitions.

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.3.0
  hooks:
    - id: hexaqual-extras
```

### 6. `hexaqual-usage-docs`
Ensures that CLI `USAGE.md` documentation stays synchronized with actual Typer CLI entrypoints.

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.3.0
  hooks:
    - id: hexaqual-usage-docs
```

---

## ⚡ Performance Optimization Guidelines

1. **Avoid Duplicate Linting**: If Ruff runs as a dedicated pre-commit hook, pass `--skip-lint` to `hexaqual sanity` to prevent Ruff from executing twice.
2. **Skip Tests in Pre-Commit**: Pre-commit hooks should complete in under 3 seconds. Unit test suites and Hypothesis fuzzing should run during the CI pipeline (`hexaqual test run`), while pre-commit focuses on static analysis (`--skip-tests`).
3. **Use `language: system` with `uv run`**: Invoking `uv run hexaqual sanity` leverages the project's pre-warmed virtualenv and uv cache, avoiding Python environment recreation.
