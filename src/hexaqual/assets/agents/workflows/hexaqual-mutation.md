<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
name: hexaqual-mutation
description: Run dual-engine mutation testing (pytest-gremlins & mutmut), triage surviving mutants, and fortify boundary test coverage.
---

# Workflow: Mutation Testing & Test Fortification

Use dual-engine mutation testing to find silent coverage holes where code logic can change without breaking tests:

## 1. Select the Mutation Engine

Hexaqual provides two complementary mutation engines:
- **`pytest-gremlins`** (Default, AST-targeted): Extremely fast AST-aware mutation runner with decoupled parallelism. Ideal for CI and rapid test fortification cycles.
- **`mutmut`** (Deep token/constant audit): Exhaustive literal constant and token mutation engine with SQLite cache.

## 2. Run Mutation Testing

- **Scoped to a single package (gremlins default with parallel workers)**:
  ```bash
  uv run hexaqual mutate run -p <pkg> -e gremlins -w auto --batch-size 10 -n 2
  ```

- **Targeting only packages affected by git diff (PR CI & fast local checks)**:
  ```bash
  uv run hexaqual mutate run -A -e gremlins -w auto --batch-size 10 -n 2
  ```

- **Deep audit with mutmut**:
  ```bash
  uv run hexaqual mutate run -p <pkg> -e mutmut
  ```

- **Reset cache and rerun**:
  ```bash
  uv run hexaqual mutate run -p <pkg> -r
  ```

- **Across all workspace packages**:
  ```bash
  uv run hexaqual mutate run -a -e gremlins -w auto --batch-size 10 -n 2
  ```

## 3. Inspect & Triage Surviving Mutants

- **High-level triage summary (Critical, Equivalent, Ignorable)**:
  ```bash
  uv run hexaqual mutate inspect -s -e gremlins
  uv run hexaqual mutate inspect -s -e mutmut
  ```

- **Actionable critical mutants correlated with test coverage**:
  ```bash
  uv run hexaqual mutate inspect -p <pkg> -act -c -e gremlins
  uv run hexaqual mutate inspect -p <pkg> -act -c -e mutmut
  ```

## 4. Fortify Test Assertions

1. For each surviving mutant, examine the covering test functions identified by `-c / --correlated`.
2. Add boundary assertions (e.g. testing `>` vs `>=`, `<` vs `<=`, off-by-one indices) or edge-case error assertions until the mutant is killed.
3. Re-verify mutation coverage:
   ```bash
   uv run hexaqual mutate run -p <pkg> -e gremlins -w auto --batch-size 10 -n 2
   ```
