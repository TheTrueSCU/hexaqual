<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
name: hexaqual-scaffold-unit
description: Scaffold a new domain entity, port interface, or concrete adapter alongside its matching 1:1 unit test suite.
---

# Workflow: Scaffold Unit & Test Parity

Follow these steps when creating a new source module to guarantee 1:1 test parity:

1. **Identify Architectural Layer**:
   - `domain/`: Pure business logic, models, entities, or state machines.
   - `ports/`: Abstract ABC interfaces (`@abstractmethod`).
   - `adapters/`: Concrete external technology implementations.
   - `infra/`: Wiring, execution pipelines, registries, or app bootstrap.

2. **Mirror Test File**:
   - For `src/<pkg>/<path>/<name>.py`, create:
     - `tests/unit/<path>/__init__.py` (if absent).
     - `tests/unit/<path>/test_<name>.py`.

3. **Verify Parity Immediately**:
   ```bash
   uv run hexaqual parity test
   ```

4. **Verify Statements & Exports**:
   ```bash
   uv run hexaqual statements check
   ```
