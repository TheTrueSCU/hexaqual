# 🛠️ Hexaqual CLI Command Catalog

Hexaqual provides a unified Typer CLI organized into domain command groups.

---

## 1. Quality & Governance (`sanity`)

Fast validator executing Ruff, Ty typechecking, complexipy cognitive complexity, `__all__` integrity, test parity, and unit test suites with a Rich dashboard.

```bash
# Check current directory / workspace
hexaqual sanity

# Scope to a specific package or example
hexaqual sanity -p <package-name>
hexaqual sanity -e <example-name>

# Workspace-wide pre-commit check (skips pytest for sub-11s execution)
hexaqual sanity -a --skip-tests

# Skip linter or typechecking steps selectively
hexaqual sanity -p my_pkg --skip-lint --skip-typecheck
```

---

## 2. Parity Governance (`parity`)

Ensures structural symmetry and packaging completeness across monorepos.

```bash
# Validate 1:1 symmetry between src/ modules and tests/unit/ suites
hexaqual parity test

# Validate that all internal packages maintain test_hexagonal_boundaries.py
hexaqual parity architecture

# Audit subpackage optional extras forwarding into umbrella pyproject.toml
hexaqual parity extras

# Generate Mermaid extras dependency graph
hexaqual parity extras --diagram
```

---

## 3. Statement & `__all__` Integrity (`statements`)

Enforces sorted, deduplicated, casefold-ordered `__all__` exports across all Python modules.

```bash
# Check __all__ sorting across the entire workspace
hexaqual statements check

# Auto-fix and alphabetize __all__ lists in-place
hexaqual statements fix

# Auto-fix scoped to a specific package
hexaqual statements fix -p <package-name>
```

---

## 4. Architectural Import Boundaries (`imports`)

Enforces hexagonal layers and import separation via `import-linter`.

```bash
# Check import boundaries defined in .importlinter
hexaqual imports check

# Generate or update .importlinter configuration
hexaqual imports generate
```

---

## 5. Mutation Testing (`mutate`)

Executes mutation testing using `mutmut` and correlates surviving mutants with line coverage data.

```bash
# Run mutation tests for a specific package
hexaqual mutate run -p <package-name>

# Clear mutation cache and re-run from scratch
hexaqual mutate run -p <package-name> -r

# High-level triage summary of surviving mutants (Critical, Equivalent, Ignorable)
hexaqual mutate inspect -s

# Display actionable critical surviving mutants
hexaqual mutate inspect -p <package-name> -act

# Correlate surviving mutants with .coverage to identify covering tests
hexaqual mutate inspect -p <package-name> -act -c
```

---

## 6. Testing Rigor (`test`)

Smart pytest runner supporting dynamic xdist worker sizing, test categories, and property-based fuzzing.

```bash
# Run pytest for a specific package with coverage
hexaqual test run -p <package-name>

# Run only unit tests
hexaqual test run -U

# Run property-based / Hypothesis tests
hexaqual test run -P

# Run only packages affected by the current git diff
hexaqual test run -A

# Audit test suites for branch boundary and edge-case assertions
hexaqual test boundary

# Analyze test execution overlap and flag duplicate paths
hexaqual test redundancy

# Selectively run tests impacted by git changes
hexaqual test impact

# Execute Atheris coverage-guided security fuzz harnesses
hexaqual test fuzz
```

---

## 7. GitHub & PR Intelligence (`gh`)

Live PR health dashboards, check runs, and repository settings queries.

```bash
# Inspect PR dashboard with CI status, review threads, and conclusion
hexaqual gh pr <pr-number>

# Expand inline review threads and comment bodies
hexaqual gh pr <pr-number> -d

# Continuously poll CI status until completion
hexaqual gh pr <pr-number> -w

# List detailed GitHub Actions check runs
hexaqual gh checks <pr-number>

# Inspect GitHub repository settings, Actions permissions, and environments
hexaqual gh repo [owner/repo]

# Summarize Dependabot alerts and security advisories
hexaqual gh security

# Query CodeQL alerts and scanning status
hexaqual gh code-scanning
```

---

## 8. Release Engineering (`release`)

Turnkey wheel build, metadata audit, reproducible build verification, and PyPI release publisher.

```bash
# Build sdist and wheel packages
hexaqual release build

# Validate package build distributions and PyPI release status
hexaqual release check

# Verify byte-for-byte reproducible wheel builds across clean environments
hexaqual release reproducible

# Smart PyPI publisher (skips existing versions, handles rate limits)
hexaqual release publish
```

---

## Output Formatting (`-f / --format`)

All diagnostic commands support uniform `-f / --format` flags:

- `table` (Default in interactive terminals)
- `json` (Machine-readable serialization, automatically selected in pipelines)
- `markdown` (Formatted tables and checklists ready for GitHub PR comments)
- `rich` (Styled Rich console rendering)
- `plain` (Unformatted TSV/text)
