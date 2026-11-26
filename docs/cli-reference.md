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

## 4. Dependencies & Import Boundaries (`deps`)

Audits dependency hygiene (`deptry`), enforces hexagonal layer contracts (`[tool.importlinter]` in `pyproject.toml`), and validates architecture SVG diagrams (`pydeps`).

```bash
# Audit declared vs imported dependencies
hexaqual deps audit

# Run deptry unused/missing dependency checks
hexaqual deps deptry

# Verify import boundaries configured in [tool.importlinter]
hexaqual deps linter

# Generate or update [tool.importlinter] contract configuration
hexaqual deps linter-generate

# Verify or regenerate pydeps architecture dependency SVG diagrams
hexaqual deps pydeps --check
```

---

## 5. Mutation Testing (`mutate`)

Executes dual-engine mutation testing using `pytest-gremlins` (default) or `mutmut`, plans capacity-capped LPT CI slices, and correlates surviving mutants with `.coverage` execution contexts.

```bash
# Run mutation tests for a specific package (default engine: pytest-gremlins)
hexaqual mutate run -p <package-name>

# Run pytest-gremlins with parallel baseline (-n) and mutation workers (-w)
hexaqual mutate run -p <package-name> -e gremlins -w auto --batch-size 10 -n auto

# Run mutmut on affected workspace packages
hexaqual mutate run -A -e mutmut

# Clear mutation cache and re-run from scratch
hexaqual mutate run -p <package-name> -r

# Plan AST-weighted LPT mutation slices for GitHub Actions matrices
hexaqual mutate plan --mode affected --slices 12 --github-output

# High-level triage summary of surviving mutants (Critical, Equivalent, Ignorable)
hexaqual mutate inspect -s

# Display actionable critical surviving mutants correlated with .coverage
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

# Summarize review discussions and security comments on a specific PR
hexaqual gh security <pr-number>

# Query CodeQL alerts and scanning status
hexaqual gh code-scanning
hexaqual gh codeql

# Inspect inline PR review threads or resolve stale threads; measure CI duration trends
hexaqual gh resolve
hexaqual gh ci-duration
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

## 9. AI Guardrails & Agent Governance (`agents`)

Manages, synchronizes, and audits universal `.agents/` guardrails across repositories while preserving local domain rules.

```bash
# Synchronize managed guardrails to the target repository (default: current working directory)
hexaqual agents sync

# Target an explicit repository or .agents directory
hexaqual agents sync --target /path/to/repo

# Simulate synchronization without writing files to disk
hexaqual agents sync --dry-run

# Check for drift between local .agents/ and installed hexaqual (exits 1 if drifted)
hexaqual agents check

# List all bundled universal rules, workflows, and skills
hexaqual agents list
```

### Root `AGENTS.md` & Reload Lifecycle

1. **Root Pointer (`AGENTS.md`)**:
   - `hexaqual agents sync` generates an aggregated `AGENTS.md` at the repository root indexing all active rules, workflows, and skills (both universal `hexaqual-*` and local `hexa<X>-*` assets).
   - This ensures tools that only inspect a single root file (such as GitHub Copilot Workspace or Claude Code) immediately see the full guardrails suite.
2. **VCS Hygiene (`.gitignore`)**:
   - `hexaqual agents sync` appends managed ignore patterns (`.agents/rules/hexaqual-*`, `.agents/workflows/hexaqual-*`, `.agents/skills/hexaqual_*`) to `.gitignore` if missing.
   - Whether `AGENTS.md` is committed or added to `.git/info/exclude` is left to maintainer preference.
3. **Dynamic Reloading**:
   - **Antigravity CLI / IDE**: Re-reads `.agents/rules/*.md` and `AGENTS.md` at the start of each conversation turn; the `hexaqual-agents` pre-commit hook enforces sync.

---

## 10. Infrastructure-as-Code Quality & Security (`iac`)

Auto-detects OpenTofu/Terraform modules, Dockerfiles, Kubernetes/Helm manifests, and shell scripts, running formatting, static linting, and misconfiguration scanning gates while skipping cleanly on repositories without matching IaC assets.

```bash
# Discover IaC assets and inspect external tool binary readiness
hexaqual iac discover

# Run auto-detecting IaC formatting, linting, and misconfiguration scans
hexaqual iac check

# Run targeted tools, apply formatting fixes, or enforce strict binary presence
hexaqual iac check --fix --tool tofu-fmt --tool tofu-validate
hexaqual iac check --strict --format json --summary

# Check or apply HCL formatting directly
hexaqual iac fmt --check
hexaqual iac fmt --fix
```

---

## 11. Additional Command Groups (`hooks`, `openssf`, `docs`, `refactor`, `complexity`, `version`)

See the unrolled [CLI Reference Catalog (`USAGE.md`)](https://github.com/TheTrueSCU/hexaqual/blob/main/USAGE.md) for full option listings across every subcommand:

- **`hexaqual hooks`** (`install`, `uninstall`, `check`, `commit-msg`): Manage the 5 Git hook stages and validate Conventional Commits + OpenSSF DCO `Signed-off-by:` trailers.
- **`hexaqual openssf`** (`audit`, `propose`, `checklist`, `scorecard`, `scaffold`, `check`): Audit OpenSSF Best Practices badge criteria (Passing/Silver/Gold), evaluate Security Scorecards, scaffold compliance docs, and propose updates.
- **`hexaqual docs`** (`usage`, `drift`, `links`, `publish`, `blog medium`): Audit or regenerate `USAGE.md`, check documentation metric drift, validate relative markdown links/anchors, publish Dev.to articles, and record Medium syndication links.
- **`hexaqual refactor`** (`alphabetize`, `rename`, `extract`, `move`, `run`): Rope-powered refactoring and AST-level symbol alphabetization.
- **`hexaqual complexity`** / **`hexaqual version`**: Run `complexipy` cognitive complexity audits or print the installed `hexaqual` version.

---

## Output Formatting (`-f / --format`)

Supported format values depend on the command group (see `USAGE.md` for exact per-command options):

- **Governance, parity, deps, docs, openssf, refactor, test-audit commands**: Typically support `table` (default), `json`, and `markdown` (`docs` and `openssf` use `resolve_format`, switching `auto` from `table` on a TTY to `json` when piped).
- **`gh` inspection commands** (`pr`, `checks`, `repo`, `security`, `code-scanning`): Default to `auto`, supporting `rich`, `json`, and `plain` (TSV). (`gh codeql` uses `table`, `json`, `markdown`.)
- **`mutate inspect` & `release` commands**: Default to `rich`.
- **Exceptions**: `hooks check`, `hooks install`, `hooks uninstall`, `hooks commit-msg`, and `mutate plan` use dedicated status output or GitHub Actions output without `-f / --format`.
