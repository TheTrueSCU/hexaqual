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
      - id: trailing-whitespace

  # 2. Ruff (Fast Linting and Formatting)
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.7
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  # 3. Hexaqual Unified Architecture & Quality Gate
  - repo: https://github.com/TheTrueSCU/hexaqual
    rev: v0.12.1
    hooks:
      - id: hexaqual-sanity
        name: hexaqual sanity check
        entry: uv run hexaqual sanity -a --skip-tests --skip-diagrams
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

Hexaqual exposes 15 specialized Git hooks in `.pre-commit-hooks.yaml` across `pre-commit`, `commit-msg`, `pre-push`, `post-merge`, and `post-checkout` stages:

### 1. `hexaqual-sanity`
The all-in-one fast quality gate (`--skip-tests --skip-diagrams`). Executes Ruff, Ty typechecking, cognitive complexity (`complexipy`), `__all__` integrity, test parity, and `deptry` across workspace packages.

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.12.1
  hooks:
    - id: hexaqual-sanity
```

### 2. `hexaqual-architecture`
Verifies that all internal subpackages maintain dedicated `test_hexagonal_boundaries.py` architectural test suites (`uv run hexaqual parity architecture`).

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.12.1
  hooks:
    - id: hexaqual-architecture
```

### 3. `hexaqual-test-parity`
Guarantees 1:1 structural symmetry between source modules in `src/` and unit test suites in `tests/unit/` (`uv run hexaqual parity test`).

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.12.1
  hooks:
    - id: hexaqual-test-parity
```

### 4. `hexaqual-statements`
Validates that all `__all__` export arrays are sorted alphabetically in casefold order and deduplicated (`uv run hexaqual statements check`).

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.12.1
  hooks:
    - id: hexaqual-statements
```

### 5. `hexaqual-linter`
Validates hexagonal package import boundaries via `import-linter` (`uv run hexaqual deps linter`).

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.12.1
  hooks:
    - id: hexaqual-linter
```

### 6. `hexaqual-extras`
Audits subpackage optional dependencies to ensure they are properly forwarded to umbrella package definitions (`uv run hexaqual parity extras`).

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.12.1
  hooks:
    - id: hexaqual-extras
```

### 7. `hexaqual-usage-docs`
Ensures that CLI `USAGE.md` documentation stays synchronized with actual Typer CLI entrypoints (`uv run hexaqual docs usage --check`).

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.12.1
  hooks:
    - id: hexaqual-usage-docs
```

### 8. `hexaqual-docs-links`
Validates relative markdown links and heading anchors across documentation trees (`uv run hexaqual docs links`).

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.12.1
  hooks:
    - id: hexaqual-docs-links
```

### 9. `hexaqual-diagrams`
Verifies architecture dependency SVG diagrams generated via `pydeps` are fresh and up to date (`uv run hexaqual deps pydeps --check`).

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.12.1
  hooks:
    - id: hexaqual-diagrams
```

### 10. `hexaqual-agents`
Enforces that universal `.agents/` guardrails (rules, workflows, skills) stay synchronized with the installed `hexaqual` package. Rejects commits if managed assets have drifted, instructing the developer to run `uv run hexaqual agents sync`.

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.12.1
  hooks:
    - id: hexaqual-agents
```

### 11. `hexaqual-agents-sync`
Automatically re-synchronizes shared `.agents/` rules, workflows, and skills after `post-merge` and `post-checkout` Git events.

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.12.1
  hooks:
    - id: hexaqual-agents-sync
      stages: [post-merge, post-checkout]
```

### 12. `hexaqual-commit-msg`
Validates Conventional Commits formatting and OpenSSF DCO `Signed-off-by:` trailers during the `commit-msg` stage (`uv run hexaqual hooks commit-msg`).

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.12.1
  hooks:
    - id: hexaqual-commit-msg
      stages: [commit-msg]
```

### 13. `hexaqual-pre-push`
Runs full workspace static sanity (`uv run hexaqual sanity -a --skip-tests --skip-diagrams`) during the `pre-push` stage.

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.12.1
  hooks:
    - id: hexaqual-pre-push
      stages: [pre-push]
```

### 14. `hexaqual-pre-push-tests`
Executes affected unit tests across workspace packages in parallel before pushing (`uv run hexaqual test run -A -U -n auto`).

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.12.1
  hooks:
    - id: hexaqual-pre-push-tests
      stages: [pre-push]
```

### 15. `hexaqual-openssf-check`
Verifies OpenSSF Best Practices badge compliance against the configured required tier (`uv run hexaqual openssf check`).

```yaml
- repo: https://github.com/TheTrueSCU/hexaqual
  rev: v0.12.1
  hooks:
    - id: hexaqual-openssf-check
```

---

## ⚡ Performance Optimization Guidelines

1. **Avoid Duplicate Linting**: If Ruff runs as a dedicated pre-commit hook, pass `--skip-lint` to `hexaqual sanity` to prevent Ruff from executing twice.
2. **Skip Tests in Pre-Commit**: Pre-commit hooks should complete in under 3 seconds. Unit test suites and Hypothesis fuzzing should run during the CI pipeline (`hexaqual test run`), while pre-commit focuses on static analysis (`--skip-tests`).
3. **Use `language: system` with `uv run`**: Invoking `uv run hexaqual sanity` leverages the project's pre-warmed virtualenv and uv cache, avoiding Python environment recreation.
