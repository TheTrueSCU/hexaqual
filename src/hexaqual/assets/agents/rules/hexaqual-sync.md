<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
trigger: always_on
description: Ensure shared .agents rules, workflows, and skills stay in sync with the installed hexaqual version.
---

## Shared Agent Guardrails Synchronization

This repository relies on universal guardrails packaged and distributed via `hexaqual`.

### Invariants & Triggers
1. **Post-Pull & Branch Switch Re-Synchronization**:
   - Whenever executing `git pull`, checking out a branch, or pulling upstream changes where `uv.lock`, `pyproject.toml`, or `.agents/` are modified:
     ```bash
     uv sync
     uv run hexaqual agents sync
     ```
2. **Context Re-Anchoring (Crucial for AI Assistants)**:
   - After synchronization, the AI assistant must inspect any modified rule files in `.agents/rules/` and re-read them into active working memory before proposing changes or executing workflows.
   - Ensures memory never operates on stale invariants (e.g. updated mutation flags, testing thresholds, or hexagonal boundary rules).
3. **Dependency Upgrades**:
   - Whenever `hexaqual` is updated in `uv.lock` or `pyproject.toml`, run:
     ```bash
     uv run hexaqual agents sync
     ```
4. **Managed File Protection**:
   - Files managed by `hexaqual` start with `hexaqual-*` (or `hexaqual_*` for skills) and contain the header:
     `<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->`.
   - Never edit managed files manually in downstream repositories. Submit improvements upstream in `hexaqual`.
   - Repository-specific rules (e.g. `hexaqueue-*.md`, `hexaflow-*.md`) are unmanaged and preserved untouched during syncs.
5. **Drift Enforcement**:
   - Pre-commit runs `uv run hexaqual agents check`. If shared assets have drifted or `.gitignore` is missing required exclusions, the commit is rejected until `uv run hexaqual agents sync` is executed.
6. **VCS & Git Hygiene**:
   - Every repository must include the following exclusions in its `.gitignore`:
     ```gitignore
     .agents/rules/hexaqual-*
     .agents/workflows/hexaqual-*
     .agents/skills/hexaqual_*
     ```
   - Repository-specific domain rules (e.g. `hexaqueue-*.md`, `hexaflow-*.md`, `graphify.md`) must remain committed to version control in their respective repositories.
   - Root pointers (`AGENTS.md`, `GEMINI.md`) may either be committed to version control or excluded locally via `.git/info/exclude`, depending on project maintainer preference.
