<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
trigger: always_on
description: Standards for authoring tests matching hexagonal architecture, 1:1 test parity, and side-effect-free assertions.
---

## Test Authoring & Symmetry Standards

When writing, refactoring, or extending test suites, adhere strictly to the following invariants:

### 1. Strict 1:1 Test Parity & Symmetry
- Every source file `src/<pkg>/<path>.py` requires an exact mirrored unit test file `tests/unit/<path>/test_<name>.py`.
- Every test directory in `tests/unit/` (and its subdirectories) must contain an `__init__.py` file.
- Enforced deterministically by `uv run hexaqual parity test`.

### 2. Hexagonal Test Isolation
- **Mock ABC Ports, Never Concrete Adapters**: Unit tests for `domain/` and `ports/` must never import from concrete `adapters/` or `infra/`. Use pure Python test stubs or `unittest.mock.create_autospec` against port interfaces.
- **Contract Adherence**: Stubs and mock doubles must adhere strictly to the method signatures and default parameter values of the abstract port definition. Never mock nonexistent methods.

### 3. Side-Effect Free Assertions
- Always assign function or method return values to an intermediate variable before making assertions:
  ```python
  # Correct
  result = service.execute(command)
  assert result.is_success is True

  # Banned (triggers CodeQL assert-with-side-effect and hexaqual warnings)
  assert service.execute(command).is_success is True
  ```

### 4. Dedicated Architectural Boundary Tests
- Every package maintaining internal hexagonal layers requires a dedicated `tests/architecture/test_hexagonal_boundaries.py` test suite verifying layer dependency directions via `pytest-archon` or `import-linter`.
- Enforced deterministically by `uv run hexaqual parity architecture`.
