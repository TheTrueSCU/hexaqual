<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
name: hexaqual-openssf
description: Triage and remediate OpenSSF Best Practices badge regressions and Security Scorecard degradations using hexaqual openssf commands.
---

# Workflow: OpenSSF Badge & Scorecard Triage

Execute these steps whenever a possible OpenSSF regression is suspected (after dependency changes, new GitHub Actions, coverage drops, or before any release):

1. **Run the Badge Compliance Gate**:
   ```bash
   uv run hexaqual openssf check --tier passing --project-id <id>
   # Or let it auto-detect from git remote:
   uv run hexaqual openssf check --tier passing
   ```
   - Exit code `0` = all MUST criteria met, score at minimum threshold.
   - Exit code `1` = regression detected. Proceed to Step 2.

2. **Get Machine-Readable Remediation List**:
   ```bash
   uv run hexaqual openssf checklist --tier passing --unmet-only --format json
   # For Silver or Gold regressions:
   uv run hexaqual openssf checklist --tier silver --unmet-only --format json
   ```
   - Each item includes `criterion_id`, `category` (MUST/SHOULD/SUGGESTED), `status`, and `action_required` with `scaffold_command` where applicable.

3. **Audit the Security Scorecard**:
   ```bash
   uv run hexaqual openssf scorecard --details
   ```
   - Focus on any check that dropped below its previous score.
   - Common AI-induced regressions: `Pinned-Dependencies` (mutable `@v4` tags), `Token-Permissions` (missing `permissions` block), `Signed-Releases` (missing attestation).

4. **Scaffold Missing Governance Documents** (if `action_required.scaffold_command` is present):
   ```bash
   uv run hexaqual openssf scaffold security      # SECURITY.md
   uv run hexaqual openssf scaffold governance    # GOVERNANCE.md
   uv run hexaqual openssf scaffold contributing  # CONTRIBUTING.md
   uv run hexaqual openssf scaffold codeql        # .github/workflows/codeql.yml
   ```
   - Review and customize the scaffolded content before committing.

5. **Generate and Submit Proposal URLs** (for badge form updates):
   ```bash
   uv run hexaqual openssf propose --tier passing --open
   uv run hexaqual openssf propose --tier silver --open
   ```
   - Opens pre-filled `bestpractices.dev` form batches in the default browser.
   - Review the yellow-highlighted fields, then click **Save Changes**.

6. **Re-run compliance gate to confirm clean**:
   ```bash
   uv run hexaqual openssf check --tier passing
   ```
   - Must exit `0` before merging or tagging a release.
