<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
trigger: always_on
description: OpenSSF Best Practices badge and Security Scorecard regression prevention — DCO sign-off, pinned Action SHAs, least-privilege workflows, and zero-credential persistence.
---

## OpenSSF Compliance Invariants

All code, commits, and GitHub Actions workflows must preserve the project's OpenSSF Best Practices badge tier and Security Scorecard posture. AI-generated changes are a common source of silent supply-chain regressions.

### 1. DCO Sign-Off (MUST — Silver tier)
- Every commit must carry the DCO sign-off trailer: `git commit -s`.
- Never use `git commit -m` alone. The `-s` flag is required.
- The commit-msg hook (`hexaqual-commit-msg`) enforces this automatically.

### 2. Pinned GitHub Action SHAs (Scorecard: `Pinned-Dependencies`)
- Every `uses:` step in `.github/workflows/*.yml` must reference a 40-character immutable commit SHA, **not** a mutable tag.
- Always include a version comment so the intent is human-readable:
  ```yaml
  # ✅ Correct
  uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2

  # ❌ Wrong — mutable tag, Scorecard will flag this as 0/10
  uses: actions/checkout@v4
  ```
- Dependabot (configured in `.github/dependabot.yml` under `package-ecosystem: github-actions`) will propose SHA updates automatically.

### 3. Least-Privilege Workflow Permissions (Scorecard: `Token-Permissions`)
- Every workflow file must declare `permissions: read-all` at the top level, then grant minimum necessary write scopes per job.
- Never rely on ambient `GITHUB_TOKEN` write access inherited from the organization default.
- Never add `permissions: write-all` or omit the `permissions` block entirely.

### 4. Test Coverage Fortification (Best Practices: `test_statement_coverage90`, `test_branch_coverage80`)
- New code must be accompanied by unit tests achieving ≥ 90% statement coverage and ≥ 80% branch coverage.
- Run `uv run hexaqual test run` before committing to verify thresholds locally.
- Do not stub or skip tests to avoid coverage failures — fix the test gap.

### 5. Zero Credential Persistence (Security Invariant)
- Browser sessions, OAuth tokens, cookies, and API keys must never be written to disk.
- Do not save Playwright `storage_state`, `.netrc`, or environment credential files to the repository or developer workstation.
- Enforced by `detect-secrets` pre-commit hook.

### 6. Reproducible Builds (Best Practices: `build_reproducible`)
- `uv.lock` must be committed alongside any `pyproject.toml` dependency changes.
- Never add packages directly to `uv.lock` by hand — run `uv sync` or `uv add` and commit the resulting lockfile.
- Run `uv run hexaqual release reproducible` before any release to verify bit-for-bit wheel reproducibility.

### 7. Compliance Gate Before Merging or Releasing
- Run `uv run hexaqual openssf check` before any merge to `main` or release tag to verify badge level and MUST criteria compliance.
- If the command exits with code 1, diagnose with `uv run hexaqual openssf checklist --unmet-only --format json` and resolve all failures before proceeding.
