# Feature Demos & User Journeys

> Visual, narrated walkthroughs recorded automatically via our test suites using `RECORD_DEMO=1`.

---

## 1. Zero-Drift Git Lifecycle Governance (`HQ-01`)

Watch `hexaqual` register native Git hooks across all five lifecycle stages (pre-commit, commit-msg, pre-push, post-merge, post-checkout), auto-sort out-of-order `__all__` export statements, and execute the fast scoped sanity gate in under 11 seconds.

<video controls autoplay loop muted playsinline width="100%" style="border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
  <source src="assets/demos/hexaqual-hooks-and-sanity.webm" type="video/webm">
  <track label="English" kind="subtitles" srclang="en" src="assets/demos/hexaqual-hooks-and-sanity.vtt" default>
</video>

---

## 2. Mutation Testing & Surviving Mutant Triage (`HQ-02`)

Inspect mutation testing execution with decoupled baseline test workers (`pytest-xdist`) and parallel gremlin crunchers. Triage surviving mutants by package and inspect actionable critical mutants correlated with `.coverage` execution contexts.

<video controls autoplay loop muted playsinline width="100%" style="border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
  <source src="assets/demos/hexaqual-mutation-triage.webm" type="video/webm">
  <track label="English" kind="subtitles" srclang="en" src="assets/demos/hexaqual-mutation-triage.vtt" default>
</video>

---

## 3. OpenSSF Best Practices Audit & Security Remediation (`HQ-03`)

Audit OpenSSF badge criteria compliance against Passing, Silver, and Gold criteria, review granular requirement checklists, inspect automated supply chain Security Scorecards, and scaffold standardized compliance policies.

<video controls autoplay loop muted playsinline width="100%" style="border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
  <source src="assets/demos/hexaqual-openssf-audit.webm" type="video/webm">
  <track label="English" kind="subtitles" srclang="en" src="assets/demos/hexaqual-openssf-audit.vtt" default>
</video>

---

## 4. Reproducible Multi-Package Release (`HQ-04`)

Validate package distribution versions against PyPI, build wheel and sdist archives, and verify byte-for-byte reproducible builds across isolated build environments with deterministic timestamp normalization (`SOURCE_DATE_EPOCH`).

<video controls autoplay loop muted playsinline width="100%" style="border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
  <source src="assets/demos/hexaqual-reproducible-release.webm" type="video/webm">
  <track label="English" kind="subtitles" srclang="en" src="assets/demos/hexaqual-reproducible-release.vtt" default>
</video>
