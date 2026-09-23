<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
trigger: always_on
description: Four-tier testing pyramid standards (Unit, Integration, Property-Based, and Fuzzing) across all ecosystem packages.
---

## Four-Tier Testing Pyramid

All projects in this ecosystem mandate a comprehensive, tiered testing strategy. Every code contribution must include the appropriate testing tiers to guarantee behavioral veracity, boundary stability, and regression immunity.

```
                  ┌──────────────────────┐
                  │    Tier 4: Fuzzing    │  Atheris / OWASP
                  │  (Untrusted Inputs)  │  Coverage-guided security
                  ├──────────────────────┤
                  │ Tier 3: Property     │  Hypothesis (@given)
                  │ (Parsers, Algorithms)│  Invariants & state machines
                  ├──────────────────────┤
                  │ Tier 2: Integration  │  tests/integration/
                  │ (Workflows & CLI)    │  tmp_path, MockTransport
                  ├──────────────────────┤
                  │    Tier 1: Unit      │  1:1 parity (tests/unit/)
                  │  (100% Core Logic)   │  Hermetic, mock ABC ports
                  └──────────────────────┘
```

---

### Tier 1: Unit Testing (100% Mandatory)

* **Scope**: Every public function, class, and method across all layers (`domain/`, `ports/`, `adapters/`, `infra/`, `cli/`).
* **Location**: `tests/unit/<path>/test_<name>.py` mirroring `src/<pkg>/<path>.py`.
* **1:1 Parity**: Enforced deterministically by `uv run hexaqual parity test`.
* **Hexagonal Isolation**: Mock abstract ABC ports only (`unittest.mock.create_autospec` or in-memory stubs). Never mock concrete database adapters or external third-party libraries.
* **Side-Effect-Free Assertions**: Assign return values to an intermediate variable before making assertions (`result = service.call(); assert result.is_success is True`) to prevent CodeQL SAST warnings.

---

### Tier 2: Integration Testing (Workflows & Presentation Boundaries)

* **Scope**: Mandatory for:
  - CLI command entry points and dispatchers (`cli/`).
  - Multi-component coordinators and CQRS pipelines.
  - File system operations, code generators, and AST/CST transformers.
  - Persistent repository adapters and external API publishers.
* **Location**: `tests/integration/test_<workflow>.py`.
* **Hermetic Environment**:
  - Use pytest's `tmp_path` to build realistic synthetic project or workspace fixtures.
  - Zero live network calls: mock HTTP transports using `httpx.MockTransport` or `respx`.
  - Assert end-to-end output contracts, process exit codes, and real file modifications on disk.

---

### Tier 3: Property-Based Testing (Parsers, Serializers & Invariants)

* **Scope**: Mandatory for:
  - Configuration, front-matter, and document parsers.
  - Serializers and deserializers (CloudEvent envelopes, JSON/YAML schemas, binary encoders).
  - Graph algorithms (topological sorts, DAG cycle detection, dependency trees).
  - State machines and transition invariants.
* **Location**: `tests/properties/test_<component>_properties.py`.
* **Engine**: Powered by **Hypothesis** (`@given(st...)`).
* **Directives**:
  - Test round-trip identity: `assert deserialize(serialize(val)) == val`.
  - Probe extreme boundary inputs: empty strings, null bytes, surrogate pairs, deep recursion, cyclic graphs.
  - Verify idempotency: `assert transform(transform(val)) == transform(val)`.

---

### Tier 4: Coverage-Guided Fuzzing (Security & Untrusted Boundaries)

* **Scope**: Mandatory for public endpoints, deserialization boundaries, and parsers handling user-supplied or external input.
* **Location**: `tests/fuzz/` or `packages/<pkg>/tests/fuzz/`.
* **Engine**: Discoverable Atheris / OWASP security fuzz harnesses.
* **Execution**: Executed dynamically via `uv run hexaqual test fuzz`.
* **Directives**: Ensure inputs cannot cause unhandled memory spikes, unhandled crashes, or regular expression Denial of Service (ReDoS).
