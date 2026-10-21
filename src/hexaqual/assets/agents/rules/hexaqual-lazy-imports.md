<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
# Hexagonal Lazy Imports & Layer Integrity Guardrails

> This repository adheres to strict directional hexagonal import boundaries and lazy import hygiene.

---

## 1. Zero Layer Boundary Bypasses

1. **Directional Invariants**:
   - `adapters/` must **never** import from `infra/`, whether at the module top-level or inside functions, methods, or callbacks ([ADR-001](docs/decisions.md#adr-001-strict-hexagonal-layer-boundaries--import-linter-enforcement)).
   - `domain/` contains pure business models and entities and must **never** import from `ports/`, `adapters/`, or `infra/`.
   - `ports/` defines abstract ABC interfaces and must **never** import from `adapters/` or `infra/`.

2. **Prohibition of In-Function Evasion**:
   - Using in-function or in-method `import ...` statements to circumvent `.importlinter` boundaries, architecture diagram tests, or AST quality gates is strictly prohibited.
   - Any presentation or diagnostic component requiring registration inspection must interact via abstract ports (e.g. `RegistryInspectorPort`) or standard DI container resolution rather than directly importing runtime registries from `infra/`.

---

## 2. Prohibition of Standard Library Lazy Imports

- Standard library modules (`os`, `json`, `asyncio`, `datetime`, `subprocess`, `shutil`, `inspect`, `functools`, `logging`, `concurrent.futures`, `importlib.util`, `time`, `uuid`, etc.) must **always** reside at module top-level.
- In-function lazy imports of standard library modules are prohibited. They degrade execution performance on hot code paths and obscure module dependencies.

---

## 3. Strict Permissibility Criteria for Lazy Imports

A lazy import inside a function or method is **only** permitted if ALL three criteria are satisfied:

1. **Optional Package Extra**:
   - The imported package is an optional third-party extra (e.g. `nicegui`, `sqlalchemy`, `grpc`, `strawberry`, `nats`, `confluent_kafka`, `sentry_sdk`) that is not guaranteed to be installed in minimalist runtime environments.
2. **Standardized Dependency Utility**:
   - The import is guarded using canonical dependency helpers:
     - `require_dependency("module", extra="...", package="...")`: When the dependency is mandatory for the requested operation, raising a structured `MissingDependencyError` with actionable installation guidance.
     - `optional_dependency("module", default=...)`: When the feature offers graceful progressive degradation.
3. **Hexagonal Boundary Compliance**:
   - The imported module belongs to an allowed layer according to Hexagonal Architecture constraints.

---

## 4. Automated Verification

- Run the AST lazy import audit skill prior to commits:
  ```bash
  uv run python .agents/skills/hexaqual_audit_lazy_imports.py src/
  ```
- Any detected standard library in-function import or hexagonal boundary bypass triggers a non-zero exit code and fails the quality gate.
