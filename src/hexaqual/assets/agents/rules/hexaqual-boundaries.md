<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
trigger: always_on
description: Enforce strict hexagonal architecture layer isolation across domain, ports, adapters, and infra.
---

## Hexagonal Boundary Isolation

All code in this repository strictly adheres to Hexagonal Architecture (Ports and Adapters). The dependency flow is strictly unidirectional inward toward the domain.

### Layer Isolation Invariants
1. **`domain/` (Pure Business Logic)**:
   - Contains pure business logic, value objects, domain models, and state machines.
   - **ZERO external framework or I/O dependencies** (e.g. no SQLAlchemy, FastAPI, gRPC, Click, Typer, Redis, NATS, or filesystem operations).
   - Domain code may only depend on standard library primitives, pure helper dataclasses, or `hexastack-core` domain models.
2. **`ports/` (Abstract ABC Interfaces)**:
   - Defines abstract ABC interfaces (`@abstractmethod`) specifying the contracts required by the domain.
   - Ports must never import from `adapters/` or `infra/`.
3. **`adapters/` (Concrete Technology Implementations)**:
   - Implements abstract port interfaces using concrete external technologies (e.g. SQLModel, Redis, NATS, FastAPI, NiceGUI, Typer).
   - Adapters **must never import from `infra/`**. Adapters interact exclusively with ports and domain models.
4. **`infra/` (Wiring, Pipelines & Bootstrap)**:
   - Orchestrates dependency injection, execution pipelines, registries, middleware, and application bootstrapping.
   - Glues adapters and ports together.

### Verification
- Boundary violations are strictly prohibited and checked by `uv run hexaqual imports check` (or `import-linter`).
