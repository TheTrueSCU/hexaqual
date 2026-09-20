<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
name: hexaqual-mutation
description: Run mutation testing, audit actionable surviving mutants, and fortify boundary test coverage.
---

# Workflow: Mutation Testing & Test Fortification

Use mutation testing to find silent coverage holes where code logic can change without breaking tests:

1. **Run Scoped Mutation Testing**:
   ```bash
   uv run hexaqual mutate run -p <package-name>
   ```

2. **Inspect Actionable Critical Mutants**:
   ```bash
   uv run hexaqual mutate inspect -p <package-name> -act -c
   ```

3. **Fortify Test Assertions**:
   - For each surviving mutant, examine the covering test function.
   - Add boundary assertions (e.g. testing `>` vs `>=`) or edge-case error assertions until the mutant is killed.

4. **Re-verify Mutation Coverage**:
   ```bash
   uv run hexaqual mutate run -p <package-name>
   ```
