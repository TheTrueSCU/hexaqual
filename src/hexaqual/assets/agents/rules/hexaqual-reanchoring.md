<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
trigger: always_on
description: Architectural re-anchoring, context re-hydration, and evidence receipts to prevent context compaction amnesia and AI drift.
---

## Architectural Re-Anchoring & Context Re-hydration

Context window compaction, session restarts, and long tool-output histories cause AI models to suffer from **context amnesia** — dropping non-obvious constraints, the architectural *why* behind past decisions, and proposing previously rejected designs.

To prevent architectural drift across sessions, autonomous agents and developers must strictly adhere to the **Re-Anchoring Protocol**.

---

### 1. Mandatory Re-Anchoring Triggers

You **MUST** pause and explicitly re-read `docs/decisions.md` and relevant `.agents/rules/` before writing or modifying code whenever ANY of the following four triggers occurs:

1. **Post-Compaction Resume**:
   - The prompt contains a `<CONTEXT_SUMMARY>` block, or the conversation history has been summarized/compacted.
2. **Architectural & Infrastructure Proposals**:
   - Before proposing changes to persistence engines (e.g. SQLite, PostgreSQL, Redis), transport adapters (FastAPI, gRPC, MCP, CLI), dependency injection wiring, or hexagonal layers.
   - Verify that the proposal does not contradict an existing ADR in `docs/decisions.md`.
3. **Unexpected Gate, Hook, or Test Failure**:
   - When `hexaqual sanity`, `import-linter`, pre-commit hooks, or test suites fail unexpectedly.
   - **DO NOT** immediately edit code or patch symptoms. Re-read the rule that failed to understand the invariant before touching code.
4. **Pre-Handoff Quality Gate**:
   - Before concluding a task, opening a pull request, or claiming a feature is complete.

---

### 2. Primary Memory Sources to Inspect

When re-anchoring, consult these canonical sources on disk:
- **`docs/decisions.md`**: The authoritative index of Architectural Decision Records (ADRs), detailing what was chosen, the underlying invariant, and **which alternatives were rejected and why**.
- **`.agents/rules/`**: Active guardrails for hexagonal boundaries, docstrings, testing rigor, and security.
- **`AGENTS.md`**: Monorepo standards, developer commands, and active package inventories.

---

### 3. Architectural Invariant Receipt ("No Evidence = No PASS")

An agent must **never** conclude a substantial task by merely claiming "everything works and tests pass." Every task handoff or PR description must include an explicit **Architectural Invariant Receipt**:

```markdown
### Architectural Invariant Receipt
- **ADR / Rule Checked**: [e.g. ADR-001 (Hexagonal Boundaries), ADR-004 (Anti-Fake-Pass)]
- **Invariant Preserved**: [State the specific invariant, e.g. "Zero external framework imports in domain/"]
- **Evidence Run**: [Exact command, e.g. `uv run hexaqual sanity -a --skip-tests`, exit code, count of passing checks]
- **Rejected Drift Avoided**: [e.g. "Avoided introducing CLI dependencies into domain"]
```

---

### 4. Prohibition of Gate Weakening

- **Weakening a check is changing the rule**: Weakening a linter pattern, removing a gate from CI, widening cognitive complexity thresholds, or adding a file to an exemption list is strictly prohibited as a method of fixing a failing build.
- Any change to architectural rules or quality gates requires explicit human authorization and a corresponding ADR update in `docs/decisions.md`.
