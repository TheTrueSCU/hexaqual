# Hexaqual Quality Suite & CLI Catalog (`hexaqual`)

> Canonical developer command reference and CLI catalog automatically generated from the complete command hierarchy.

---

## 🏛️ Dogfooding Hexagonal Architecture

`hexaqual` is built strictly according to Hexagonal Architecture design principles:
- **`domain/`**: Pure data contracts (`PrSummary`, `CheckRunFinding`, `ReviewThread`, `OutputFormat`).
- **`ports/`**: Clean interface contracts (`GitHubApiPort`, `GovernancePresenterPort`, `ToolRunnerPort`, `PyPiClientPort`).
- **`adapters/`**: Pluggable presenters (`rich`, `json`, `plain`), subcommands, and runners.
- **`cli/`**: Unified Typer CLI driving adapter (`hexaqual`).
- **`infra/`**: Command dispatchers, handlers, and execution orchestration.
- **`utils/`**: Workspace discovery, AST parsing, and package graph resolvers.

---

## ⚙️ Output Presentation Formats

All inspection commands support `--format / -f`:
- **`auto` (default)**: Automatically outputs interactive ANSI tables/panels when attached to a terminal TTY, and switches to clean, tab-delimited plain text (`TSV`) when standard output is piped into Unix filters (`grep`, `awk`, `cut`, `xargs`, etc.).
- **`rich`**: Interactive Rich tables and color-coded status badges.
- **`json`**: Structured JSON for automation, CI scripts, and AI agents.
- **`plain`**: Machine-readable TSV stream.

---

## 🚀 Unified Root Entrypoint (`hexaqual`)

```text
Usage: hexaqual [OPTIONS] COMMAND [ARGS]...

 Hexaqual - Universal Python Quality, Governance, and Release Engineering
 Suite.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.      │
│ --show-completion             Show completion for the current shell, to copy │
│                               it or customize the installation.              │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ check       Execute the sanity check pipeline.                               │
│ sanity      Execute the sanity check pipeline (alias for 'check').           │
│ complexity  Audit cognitive complexity using complexipy.                     │
│ version     Display the current Hexaqual version.                            │
│ statements  Audit and format __all__ statements.                             │
│ parity      Audit test symmetry and optional extras parity.                  │
│ test        Test execution, coverage audits, and architecture verification.  │
│ deps        Audit dependencies, generate import diagrams, and check          │
│             architectural boundaries.                                        │
│ mutate      Mutation testing execution and triage inspection.                │
│ release     Distribution package building, validation, and PyPI publishing.  │
│ gh          GitHub repository, PR, and security examination.                 │
│ docs        Documentation generation and verification.                       │
│ refactor    AST symbol alphabetization and Python code refactoring.          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

---

## 🛠️ Complete Subcommand Tree Reference

### `hexaqual architectural`

```text
Usage: hexaqual [OPTIONS] COMMAND [ARGS]...
Try 'hexaqual --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such command 'architectural'.                                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexaqual check`

```text
Usage: hexaqual check [OPTIONS] [files]...

 Execute the sanity check pipeline.

 Args:
     packages: Optional sequence of package names to audit.
     examples: Optional sequence of example project names to audit.
     all_targets: Whether to audit all packages unconditionally.
     fix: Whether to auto-apply formatting and lint fixes.
     skip_tests: Whether to skip test suites.
     skip_deptry: Whether to skip deptry audits.
     skip_typecheck: Whether to skip type checking.
     skip_complexity: Whether to skip complexity audits.
     skip_parity: Whether to skip test parity checks.
     skip_statements: Whether to skip __all__ statements check.
     skip: Optional list of explicit step names to skip.
     max_complexity: Cognitive complexity ceiling.
     format_type: Output presentation format.
     files: Optional explicit file or directory targets.

 Raises:
     typer.Exit: If any sanity checks fail.

 Notes/Architectural Intent:
     Primary entrypoint for local pre-commit verification and CI pipelines.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   files      <str>  Specific files or directories to verify.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --package                   -p       <str>  Target package(s).               │
│ --example                   -e       <str>  Target example(s).               │
│ --all                       -a              Run across all packages.         │
│ --fix                                       Automatically apply autofixes.   │
│ --skip-tests                                Skip pytest suites.              │
│ --skip-deptry                               Skip deptry dependency audits.   │
│ --skip-typecheck,--skip-ty                  Skip static type analysis.       │
│ --skip-complexity                           Skip cognitive complexity audit. │
│ --skip-parity                               Skip 1:1 test parity check.      │
│ --skip-statements                           Skip __all__ integrity check.    │
│ --skip                               <str>  Specific pipeline step(s) to     │
│                                             skip (repeatable).               │
│ --max-complexity            -mx      <int>  Cognitive complexity ceiling.    │
│                                             [default: 25]                    │
│ --format                    -f       <str>  Output format (table, json,      │
│                                             markdown).                       │
│                                             [default: table]                 │
│ --help                                      Show this message and exit.      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexaqual complexity`

```text
Usage: hexaqual complexity [OPTIONS] [files]...

 Audit cognitive complexity using complexipy.

 Args:
     max_complexity: Maximum allowed cognitive complexity score.
     packages: Target packages to check.
     files: Target files or directories.

 Raises:
     typer.Exit: If complexity violations are detected.

 Notes/Architectural Intent:
     Driving adapter invoking ToolRunnerPort.run_complexipy across targets.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   files      <str>  Target file(s) or directories.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --max-complexity  -mx      <int>  Maximum cognitive complexity ceiling.      │
│                                   [default: 25]                              │
│ --package         -p       <str>  Target package(s).                         │
│ --help                            Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexaqual deps`

```text
Usage: hexaqual deps [OPTIONS] COMMAND [ARGS]...

 Audit dependencies, generate import diagrams, and check architectural
 boundaries.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ audit            Execute unified audit across dependencies, optional extras, │
│                  and tools.                                                  │
│ pydeps           Generate architecture dependency diagrams using pydeps.     │
│ linter           Evaluate hexagonal architecture contract boundaries using   │
│                  import-linter.                                              │
│ linter-generate  Generate default hexagonal  contracts in pyproject.toml     │
│                  files.                                                      │
│ deptry           Run deptry dependency analysis across workspace packages.   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual deps and`

```text
Usage: hexaqual deps [OPTIONS] COMMAND [ARGS]...
Try 'hexaqual deps --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such command 'and'.                                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual deps audit`

```text
Usage: hexaqual deps audit [OPTIONS]

 Execute unified audit across dependencies, optional extras, and tools.

 Args:
     diagrams: Whether to regenerate Pydeps SVGs and Mermaid diagrams.
     deptry_only: Whether to restrict execution to deptry source import audits.
     extras_only: Whether to restrict execution to extras parity validation.
     format_type: Output presentation format.

 Raises:
     typer.Exit: If dependency or extras auditing detects violations.

 Notes/Architectural Intent:
     Dispatches RunUnifiedDepsAuditCommand across the governance bus.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --diagrams                    Regenerate all Pydeps SVG import graphs and    │
│                               Mermaid diagrams.                              │
│ --deptry-only                 Only run deptry source import audits.          │
│ --extras-only                 Only run optional extras parity checks.        │
│ --format       -f      <str>  Output representation format (table, json,     │
│                               markdown).                                     │
│                               [default: table]                               │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual deps deptry`

```text
Usage: hexaqual deps deptry [OPTIONS]

 Run deptry dependency analysis across workspace packages.

 Args:
     format_type: Output presentation format.

 Raises:
     typer.Exit: If unused or missing dependencies are detected.

 Notes/Architectural Intent:
     Driving adapter dispatching RunDeptryAuditCommand across all workspace
 packages.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format  -f      <str>  Output presentation format (table, json, markdown). │
│                          [default: table]                                    │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual deps linter`

```text
Usage: hexaqual deps linter [OPTIONS] [files]...

 Evaluate hexagonal architecture contract boundaries using import-linter.

 Args:
     packages: Optional sequence of package names to check.
     all_packages: Whether to verify all workspace packages.
     format_type: Output presentation format.
     files: Optional sequence of file paths to determine affected packages.

 Raises:
     typer.Exit: If import boundary contracts are broken.

 Notes/Architectural Intent:
     Enforces clean hexagonal dependencies between domain, ports, adapters, and
 infra.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   files      <str>  Optional changed files list.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --package  -p      <str>  Target package(s).                                 │
│ --all      -a             Run across all packages unconditionally.           │
│ --format   -f      <str>  Output presentation format (table, json,           │
│                           markdown).                                         │
│                           [default: table]                                   │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual deps linter-generate`

```text
Usage: hexaqual deps linter-generate [OPTIONS]

 Generate default hexagonal  contracts in pyproject.toml files.

 Args:
     packages: Optional sequence of packages for which to generate contracts.

 Notes/Architectural Intent:
     Generates standard forbidden-contract configurations forbidding adapters
 from
     importing infra, ports from importing adapters/infra, and domain from
 importing any layer.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --package  -p      <str>  Target package(s).                                 │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual deps pydeps`

```text
Usage: hexaqual deps pydeps [OPTIONS]

 Generate architecture dependency diagrams using pydeps.

 Args:
     packages: Optional sequence of packages to graph.
     format_type: Output presentation format.

 Raises:
     typer.Exit: If diagram generation encounters errors.

 Notes/Architectural Intent:
     Ensures pydeps availability and dispatches GeneratePydepsCommand.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --package  -p      <str>  Target package(s).                                 │
│ --format   -f      <str>  Output presentation format (table, json,           │
│                           markdown).                                         │
│                           [default: table]                                   │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexaqual docs`

```text
Usage: hexaqual docs [OPTIONS] COMMAND [ARGS]...

 Documentation generation and verification.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ usage    Generate or verify USAGE.md documentation catalogs.                 │
│ publish  Syndicate or publish documentation articles to DEV.to / Medium.     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual docs publish`

```text
Usage: hexaqual docs publish [OPTIONS]

 Syndicate or publish documentation articles to DEV.to / Medium.

 Args:
     manifest: Optional path to article markdown files.
     dry_run: Validate without network writes.
     publish: Publish live articles.
     format_type: Output presentation format.

 Raises:
     typer.Exit: If publication fails.

 Notes/Architectural Intent:
     Driving adapter dispatching PublishMediumArticlesCommand across the
 governance bus.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --manifest  -m      <path>  Path to articles manifest or directory.          │
│ --dry-run                   Validate without making live HTTP requests.      │
│ --publish                   Publish live articles (otherwise draft upload    │
│                             mode).                                           │
│ --format    -f      <str>   Output presentation format (table, json,         │
│                             markdown).                                       │
│                             [default: table]                                 │
│ --help                      Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual docs usage`

```text
Usage: hexaqual docs usage [OPTIONS]

 Generate or verify USAGE.md documentation catalogs.

 Args:
     check_only: Check freshness without writing files.
     fix: Regenerate USAGE.md on disk.
     package: Target package name.
     root: Workspace root directory.

 Raises:
     typer.Exit: If documentation is stale in check mode.

 Notes/Architectural Intent:
     Driving adapter executing usage documentation generator.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --check                    Verify USAGE.md is up to date.                    │
│ --fix                      Regenerate USAGE.md.                              │
│ --package  -p      <str>   Target package.                                   │
│ --root             <path>  Workspace root directory.                         │
│ --help                     Show this message and exit.                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexaqual gh`

```text
Usage: hexaqual gh [OPTIONS] COMMAND [ARGS]...

 GitHub repository, PR, and security examination.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ pr             Examine a Pull Request health dashboard.                      │
│ checks         Inspect CI status checks for a given PR number or Git ref.    │
│ repo           Inspect GitHub repository settings and permissions.           │
│ security       Summarize GitHub security advisories and Dependabot alerts.   │
│ code-scanning  Query CodeQL alerts and scanning status.                      │
│ codeql         Run local CodeQL security and quality analysis with           │
│                auto-detection.                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual gh checks`

```text
Usage: hexaqual gh checks [OPTIONS] {ref_or_pr}

 Inspect CI status checks for a given PR number or Git ref.

 Args:
     ref_or_pr: PR number or branch/ref.
     format_type: Output format.

 Raises:
     typer.Exit: If status checks failed or query errors.

 Notes/Architectural Intent:
     Lists detailed GitHub Actions status checks and run conclusions.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    ref_or_pr      <str>  Pull request number or commit ref/branch name.    │
│                            [required]                                        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format  -f      <str>  Output format. [default: auto]                      │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual gh code-scanning`

```text
Usage: hexaqual gh code-scanning [OPTIONS]

 Query CodeQL alerts and scanning status.

 Args:
     format_type: Output format.

 Raises:
     typer.Exit: If scanning alerts found or query fails.

 Notes/Architectural Intent:
     Queries GitHub CodeQL code scanning alerts.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format  -f      <str>  Output format. [default: auto]                      │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual gh codeql`

```text
Usage: hexaqual gh codeql [OPTIONS]

 Run local CodeQL security and quality analysis with auto-detection.

 Args:
     suite: CodeQL query suite or pack name.
     output: Optional destination path for SARIF report.
     threads: Number of analysis threads (0 for auto).
     format_type: Output presentation format.

 Raises:
     typer.Exit: If CodeQL analysis detects critical violations.

 Notes/Architectural Intent:
     Driving adapter dispatching ScanCodeQlCommand across the governance bus.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --suite    -s      <str>   CodeQL query suite or pack.                       │
│                            [default: codeql/python-queries]                  │
│ --output   -o      <path>  Optional destination path for generated SARIF     │
│                            report.                                           │
│ --threads  -t      <int>   Number of analysis threads (0 for auto).          │
│                            [default: 0]                                      │
│ --format   -f      <str>   Output presentation format (table, json,          │
│                            markdown).                                        │
│                            [default: table]                                  │
│ --help                     Show this message and exit.                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual gh pr`

```text
Usage: hexaqual gh pr [OPTIONS] {pr_number}

 Examine a Pull Request health dashboard.

 Args:
     pr_number: Pull request number.
     details: Display full comments and review threads.
     watch: Poll until checks finish.
     format_type: Output format.

 Raises:
     typer.Exit: If examination fails.

 Notes/Architectural Intent:
     Single-step PR dashboard inspecting CI check runs and reviews.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    pr_number      <str>  Pull request number to examine. [required]        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --details  -d             Display full comment discussions.                  │
│ --watch    -w             Continuously poll until checks finish.             │
│ --format   -f      <str>  Output format (auto, rich, json, plain).           │
│                           [default: auto]                                    │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual gh repo`

```text
Usage: hexaqual gh repo [OPTIONS] [repo_name]

 Inspect GitHub repository settings and permissions.

 Args:
     repo_name: Optional repo identifier.
     format_type: Output format.

 Raises:
     typer.Exit: If query fails.

 Notes/Architectural Intent:
     Inspects repository settings, Actions permissions, and environments.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   repo_name      <str>  Repository name (owner/repo).                        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format  -f      <str>  Output format. [default: auto]                      │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual gh security`

```text
Usage: hexaqual gh security [OPTIONS]

 Summarize GitHub security advisories and Dependabot alerts.

 Args:
     format_type: Output format.

 Raises:
     typer.Exit: If security alerts found or query fails.

 Notes/Architectural Intent:
     Queries Dependabot security alerts and advisories.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format  -f      <str>  Output format. [default: auto]                      │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexaqual mutate`

```text
Usage: hexaqual mutate [OPTIONS] COMMAND [ARGS]...

 Mutation testing execution and triage inspection.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ run      Run mutation testing scoped to package or workspace.                │
│ inspect  Triage and inspect mutation testing results cache.                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual mutate inspect`

```text
Usage: hexaqual mutate inspect [OPTIONS]

 Triage and inspect mutation testing results cache.

 Args:
     package: Filter by package.
     all_mutants: Display all surviving mutants.
     actionable: Display actionable critical mutants.
     correlated: Correlate with .coverage test context.
     summary: Display triage summary.
     format_type: Output format.

 Raises:
     typer.Exit: If inspect fails.

 Notes/Architectural Intent:
     Provides high-level triage and actionable surviving mutant analysis.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --package     -p        <str>  Filter by package.                            │
│ --all         -a               Inspect all mutants.                          │
│ --actionable  -act             Show actionable critical mutants.             │
│ --correlated  -c               Correlate with .coverage.                     │
│ --summary     -s               Triage summary.                               │
│ --format      -f        <str>  Output format. [default: rich]                │
│ --help                         Show this message and exit.                   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual mutate run`

```text
Usage: hexaqual mutate run [OPTIONS]

 Run mutation testing scoped to package or workspace.

 Args:
     package: Target package name.
     all_packages: Whether to run across all workspace packages.
     reset: Clear mutmut cache and re-run.

 Raises:
     typer.Exit: If mutation testing fails.

 Notes/Architectural Intent:
     Executes mutmut mutation runner across targeted components.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --package  -p      <str>  Target package name.                               │
│ --all      -a             Run across all workspace packages.                 │
│ --reset    -r             Clear cache and re-run.                            │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexaqual parity`

```text
Usage: hexaqual parity [OPTIONS] COMMAND [ARGS]...

 Audit test symmetry and optional extras parity.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ test    Verify 1:1 symmetry between src modules and unit tests.              │
│ extras  Audit optional extras parity across workspace subpackages and        │
│         umbrella.                                                            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual parity extras`

```text
Usage: hexaqual parity extras [OPTIONS]

 Audit optional extras parity across workspace subpackages and umbrella.

 Args:
     diagram: Whether to generate Mermaid extras graph.
     format_type: Output presentation format.

 Raises:
     typer.Exit: If extras parity violations are found.

 Notes/Architectural Intent:
     Driving adapter validating subpackage extras forwarding into umbrella
 packaging.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --diagram                 Generate Mermaid dependency diagram.               │
│ --format   -f      <str>  Output format (table, json, markdown).             │
│                           [default: table]                                   │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual parity test`

```text
Usage: hexaqual parity test [OPTIONS]

 Verify 1:1 symmetry between src modules and unit tests.

 Args:
     format_type: Output presentation format.

 Raises:
     typer.Exit: If parity violations are found.

 Notes/Architectural Intent:
     Driving adapter verifying src/ and tests/unit/ parity and __init__.py
 presence.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format  -f      <str>  Output format (table, json, markdown).              │
│                          [default: table]                                    │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexaqual refactor`

```text
Usage: hexaqual refactor [OPTIONS] COMMAND [ARGS]...

 AST symbol alphabetization and Python code refactoring.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ alphabetize  Sort functions and class methods alphabetically using LibCST.   │
│ rename       Rename a symbol project-wide using Rope.                        │
│ extract      Extract code block into a new function or method using Rope.    │
│ move         Move a symbol or class to another module project-wide using     │
│              Rope.                                                           │
│ run          Run interactive or advanced Rope refactoring operations.        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual refactor alphabetize`

```text
Usage: hexaqual refactor alphabetize [OPTIONS] [files]...

 Sort functions and class methods alphabetically using LibCST.

 Args:
     packages: Optional sequence of target package names.
     all_packages: Whether to format all workspace packages.
     dry_run: Preview reordering without modifying disk.
     format_type: Output presentation format.
     files: Optional sequence of files or directories to format.

 Raises:
     typer.Exit: If alphabetization fails or detects errors.

 Notes/Architectural Intent:
     Dispatches AlphabetizeCodeCommand across the governance bus.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   files      <str>  Specific files or directories to format.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --package  -p      <str>  Target package(s).                                 │
│ --all      -a             Format across all packages.                        │
│ --dry-run                 Preview reordering without modifying disk.         │
│ --format   -f      <str>  Output presentation format (table, json,           │
│                           markdown).                                         │
│                           [default: table]                                   │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual refactor extract`

```text
Usage: hexaqual refactor extract [OPTIONS]

 Extract code block into a new function or method using Rope.

 Args:
     file: Target python file.
     start_line: 1-based start line.
     end_line: 1-based end line.
     extracted_name: Name for the extracted function/method.
     root: Optional root directory.
     dry_run: Preview only.

 Raises:
     typer.Exit: If extraction fails.

 Notes/Architectural Intent:
     Executes method extraction via Rope AST refactoring.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --file        -f      <path>  Target python file. [required]              │
│ *  --start-line  -s      <int>   1-based start line. [required]              │
│ *  --end-line    -e      <int>   1-based end line. [required]                │
│ *  --name        -n      <str>   Name for the extracted function/method.     │
│                                  [required]                                  │
│    --root        -r      <path>  Project root directory.                     │
│    --dry-run                     Preview extraction without saving.          │
│    --help                        Show this message and exit.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual refactor move`

```text
Usage: hexaqual refactor move [OPTIONS]

 Move a symbol or class to another module project-wide using Rope.

 Args:
     source_file: Source python file.
     dest_file: Destination python file.
     line: 1-based line number.
     col: 1-based column offset.
     root: Optional root directory.
     dry_run: Preview only.

 Raises:
     typer.Exit: If move fails.

 Notes/Architectural Intent:
     Executes symbol relocation across module boundaries via Rope.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --source-file  -s      <path>  Source python file. [required]             │
│ *  --dest-file    -d      <path>  Destination python file. [required]        │
│ *  --line         -l      <int>   1-based line number of symbol to move.     │
│                                   [required]                                 │
│ *  --col          -c      <int>   1-based column offset of symbol.           │
│                                   [required]                                 │
│    --root         -r      <path>  Project root directory.                    │
│    --dry-run                      Preview move without saving.               │
│    --help                         Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual refactor rename`

```text
Usage: hexaqual refactor rename [OPTIONS]

 Rename a symbol project-wide using Rope.

 Args:
     file: Target python file.
     line: 1-based line number.
     col: 1-based column offset.
     new_name: New symbol name.
     root: Optional root directory.
     dry_run: Preview only.

 Raises:
     typer.Exit: If refactoring fails.

 Notes/Architectural Intent:
     Executes AST symbol renaming via Rope project engine.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --file      -f      <path>  Target python file containing the symbol.     │
│                                [required]                                    │
│ *  --line      -l      <int>   1-based line number of symbol. [required]     │
│ *  --col       -c      <int>   1-based column offset of symbol. [required]   │
│ *  --new-name  -n      <str>   New identifier name. [required]               │
│    --root      -r      <path>  Project root directory.                       │
│    --dry-run                   Preview rename without saving.                │
│    --help                      Show this message and exit.                   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual refactor run`

```text
Usage: hexaqual refactor run [OPTIONS]

 Run interactive or advanced Rope refactoring operations.

 Args:
     ctx: Typer context capturing extra positional and option arguments.

 Raises:
     typer.Exit: If refactoring fails.

 Notes/Architectural Intent:
     Passes CLI arguments directly to the Rope refactoring command dispatcher.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexaqual release`

```text
Usage: hexaqual release [OPTIONS] COMMAND [ARGS]...

 Distribution package building, validation, and PyPI publishing.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ build         Build distribution packages (sdist and wheel).                 │
│ check         Validate package build distributions and PyPI release          │
│               versions.                                                      │
│ publish       Build and publish packages to PyPI, skipping existing          │
│               releases.                                                      │
│ reproducible  Verify bit-for-bit reproducible wheel package builds.          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual release build`

```text
Usage: hexaqual release build [OPTIONS]

 Build distribution packages (sdist and wheel).

 Args:
     dist_dir: Destination directory.
     format_type: Output format.

 Raises:
     typer.Exit: If build fails.

 Notes/Architectural Intent:
     Builds reproducible distribution packages.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --dist-dir          <path>  Output directory (default: dist/).               │
│ --format    -f      <str>   Output format. [default: rich]                   │
│ --help                      Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual release check`

```text
Usage: hexaqual release check [OPTIONS]

 Validate package build distributions and PyPI release versions.

 Args:
     package: Optional specific package name to check.
     format_type: Output format.

 Raises:
     typer.Exit: If validation fails.

 Notes/Architectural Intent:
     Queries PyPI to verify current version status.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --package  -p      <str>  Target package name (default: all).                │
│ --format   -f      <str>  Output format. [default: rich]                     │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual release publish`

```text
Usage: hexaqual release publish [OPTIONS]

 Build and publish packages to PyPI, skipping existing releases.

 Args:
     dist_dir: Directory containing packages.
     build: Whether to build packages before upload.
     token: PyPI upload token.
     delay: Delay between package uploads.
     force: Force upload even if exists.
     format_type: Output format.

 Raises:
     typer.Exit: If publishing fails.

 Notes/Architectural Intent:
     Smart publisher skipping published versions and respecting rate limits.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --dist-dir                    <path>   Directory containing packages.        │
│ --build         --no-build             Build before publishing.              │
│                                        [default: build]                      │
│ --token                       <str>    PyPI upload token.                    │
│ --delay                       <float>  Delay between uploads. [default: 2.0] │
│ --force                                Force upload.                         │
│ --format    -f                <str>    Output format. [default: rich]        │
│ --help                                 Show this message and exit.           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual release reproducible`

```text
Usage: hexaqual release reproducible [OPTIONS]

 Verify bit-for-bit reproducible wheel package builds.

 Args:
     format_type: Output format.

 Raises:
     typer.Exit: If reproducible build check fails.

 Notes/Architectural Intent:
     Builds twice in clean isolated environments and compares SHA256 hashes.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format  -f      <str>  Output format. [default: rich]                      │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexaqual sanity`

```text
Usage: hexaqual sanity [OPTIONS] [files]...

 Execute the sanity check pipeline (alias for 'check').

 Args:
     packages: Optional sequence of package names to audit.
     examples: Optional sequence of example project names to audit.
     all_targets: Whether to audit all packages unconditionally.
     fix: Whether to auto-apply formatting and lint fixes.
     skip_tests: Whether to skip test suites.
     skip_deptry: Whether to skip deptry audits.
     skip_typecheck: Whether to skip type checking.
     skip_complexity: Whether to skip complexity audits.
     skip_parity: Whether to skip test parity checks.
     skip_statements: Whether to skip __all__ statements check.
     skip: Optional list of explicit step names to skip.
     max_complexity: Cognitive complexity ceiling.
     format_type: Output presentation format.
     files: Optional explicit file or directory targets.

 Raises:
     typer.Exit: If any sanity checks fail.

 Notes/Architectural Intent:
     Convenience alias matching legacy sanity-check naming.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   files      <str>  Specific files or directories to verify.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --package                   -p       <str>  Target package(s).               │
│ --example                   -e       <str>  Target example(s).               │
│ --all                       -a              Run across all packages.         │
│ --fix                                       Automatically apply autofixes.   │
│ --skip-tests                                Skip pytest suites.              │
│ --skip-deptry                               Skip deptry dependency audits.   │
│ --skip-typecheck,--skip-ty                  Skip static type analysis.       │
│ --skip-complexity                           Skip cognitive complexity audit. │
│ --skip-parity                               Skip 1:1 test parity check.      │
│ --skip-statements                           Skip __all__ integrity check.    │
│ --skip                               <str>  Specific pipeline step(s) to     │
│                                             skip (repeatable).               │
│ --max-complexity            -mx      <int>  Cognitive complexity ceiling.    │
│                                             [default: 25]                    │
│ --format                    -f       <str>  Output format (table, json,      │
│                                             markdown).                       │
│                                             [default: table]                 │
│ --help                                      Show this message and exit.      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexaqual statements`

```text
Usage: hexaqual statements [OPTIONS] COMMAND [ARGS]...

 Audit and format __all__ statements.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ check  Validate __all__ declarations across targeted files.                  │
│ fix    Format __all__ declarations in target Python files.                   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual statements check`

```text
Usage: hexaqual statements check [OPTIONS] [files]...

 Validate __all__ declarations across targeted files.

 Args:
     packages: Optional sequence of package names to inspect.
     format_type: Output presentation format.
     files: Optional explicit list of files or directories.

 Raises:
     typer.Exit: If validation errors are encountered.

 Notes/Architectural Intent:
     Driving adapter delegating to AST statement inspection and governance
 presenter.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   files      <str>  Target files or directories.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --package  -p      <str>  Target package(s).                                 │
│ --format   -f      <str>  Output format (table, json, markdown).             │
│                           [default: table]                                   │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual statements fix`

```text
Usage: hexaqual statements fix [OPTIONS] [files]...

 Format __all__ declarations in target Python files.

 Args:
     packages: Optional sequence of package names to inspect.
     format_type: Output presentation format.
     files: Optional explicit list of files or directories.

 Notes/Architectural Intent:
     Driving adapter sorting, deduplicating, and formatting __all__ statements.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   files      <str>  Target files or directories.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --package  -p      <str>  Target package(s).                                 │
│ --format   -f      <str>  Output format (table, json, markdown).             │
│                           [default: table]                                   │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexaqual test`

```text
Usage: hexaqual test [OPTIONS] COMMAND [ARGS]...

 Test execution, coverage audits, and architecture verification.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ run         Run pytest suite with dynamic worker allocation and coverage.    │
│ boundary    Audit test suites for branch boundary and edge-case assertions.  │
│ impact      Selectively run tests impacted by current git diff changes.      │
│ redundancy  Analyze test execution overlap and flag duplicate test paths.    │
│ fuzz        Run coverage-guided and adversarial security fuzz harnesses.     │
│ snapshot    Update or review inline snapshots across test suites.            │
│ archon      Generate pytest-archon boundary tests for packages.              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual test archon`

```text
Usage: hexaqual test archon [OPTIONS]

 Generate pytest-archon boundary tests for packages.

 Args:
     packages: Target package(s) for test generation.
     force: Overwrite existing test files.
     format_type: Output presentation format.

 Raises:
     typer.Exit: If generation fails.

 Notes/Architectural Intent:
     Driving adapter dispatching GenerateArchonTestsCommand across the
 governance bus.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --package  -p      <str>  Target package(s).                                 │
│ --force                   Overwrite existing boundary test files.            │
│ --format   -f      <str>  Output presentation format (table, json,           │
│                           markdown).                                         │
│                           [default: table]                                   │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual test boundary`

```text
Usage: hexaqual test boundary [OPTIONS]

 Audit test suites for branch boundary and edge-case assertions.

 Args:
     format_type: Output format.

 Raises:
     typer.Exit: If boundary audit detects defects.

 Notes/Architectural Intent:
     Audits branch coverage assertions across test suites.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format  -f      <str>  Output presentation format. [default: table]        │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual test fuzz`

```text
Usage: hexaqual test fuzz [OPTIONS]

 Run coverage-guided and adversarial security fuzz harnesses.

 Args:
     target: Target fuzz harness to execute.
     runs: Number of fuzzed runs per harness.
     engine: Fuzzing engine to use.
     format_type: Output presentation format.

 Raises:
     typer.Exit: If any fuzz harness fails.

 Notes/Architectural Intent:
     Driving adapter dispatching FuzzRunCommand across the governance bus.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --target  -t      <str>  Target fuzz harness (all, sanitizer, proto, owasp). │
│                          [default: all]                                      │
│ --runs    -n      <int>  Number of fuzzed runs per harness. [default: 1000]  │
│ --engine  -e      <str>  Fuzzing engine (auto, atheris, standalone).         │
│                          [default: auto]                                     │
│ --format  -f      <str>  Output presentation format (table, json, markdown). │
│                          [default: table]                                    │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual test impact`

```text
Usage: hexaqual test impact [OPTIONS]

 Selectively run tests impacted by current git diff changes.

 Args:
     format_type: Output format.

 Raises:
     typer.Exit: If impacted tests fail.

 Notes/Architectural Intent:
     Accelerates local feedback loops by running only affected test paths.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format  -f      <str>  Output presentation format. [default: table]        │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual test redundancy`

```text
Usage: hexaqual test redundancy [OPTIONS]

 Analyze test execution overlap and flag duplicate test paths.

 Args:
     format_type: Output format.

 Raises:
     typer.Exit: If redundancy exceeds configured thresholds.

 Notes/Architectural Intent:
     Identifies duplicate test execution paths to optimize CI test efficiency.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format  -f      <str>  Output presentation format. [default: table]        │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual test run`

```text
Usage: hexaqual test run [OPTIONS]

 Run pytest suite with dynamic worker allocation and coverage.

 Args:
     ctx: Command execution context capturing extra CLI options.
     package: Optional sequence of target package names.
     example: Optional sequence of target example project names.
     all_packages: Whether to run across all packages unconditionally.
     affected: Whether to run only packages affected by git diff.
     unit: Whether to restrict execution to unit tests.
     properties: Whether to restrict execution to property tests.
     with_context: Whether to capture test context in coverage.

 Raises:
     typer.Exit: If tests fail.

 Notes/Architectural Intent:
     Driving adapter delegating to pytest runner adapter and forwarding
     any additional unknown options or flags directly to pytest.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --package       -p      <str>  Target package(s).                            │
│ --example       -e      <str>  Target example project(s).                    │
│ --all           -a             Run across all workspace packages.            │
│ --affected      -A             Run only affected packages.                   │
│ --unit          -U             Run only unit tests.                          │
│ --properties    -P             Run only property tests.                      │
│ --with-context                 Capture test context in coverage.             │
│ --help                         Show this message and exit.                   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexaqual test snapshot`

```text
Usage: hexaqual test snapshot [OPTIONS] [files]...

 Update or review inline snapshots across test suites.

 Args:
     mode: Snapshot update mode.
     packages: Target package(s).
     format_type: Output presentation format.
     files: Target file paths.

 Raises:
     typer.Exit: If snapshot update command fails.

 Notes/Architectural Intent:
     Driving adapter dispatching UpdateInlineSnapshotsCommand across packages.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   files      <str>  Target file paths.                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mode     -m      <str>  inline-snapshot mode (create, fix, review).        │
│                           [default: fix]                                     │
│ --package  -p      <str>  Target package(s).                                 │
│ --format   -f      <str>  Output presentation format (table, json,           │
│                           markdown).                                         │
│                           [default: table]                                   │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexaqual version`

```text
Usage: hexaqual version [OPTIONS]

 Display the current Hexaqual version.

 Notes/Architectural Intent:
 Quick diagnostic command to confirm package installation and version info.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```
