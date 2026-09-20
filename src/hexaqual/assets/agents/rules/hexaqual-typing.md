<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
trigger: always_on
description: Modern Python 3.13 typing standards, PEP 695 generic syntax, and boundary contract rigor.
---

## Modern Python Typing Contracts

This ecosystem targets Python 3.13+. Keep type contracts expressive, precise, and strictly validated by `ty` / `mypy`.

### Directives & Idioms
1. **PEP 695 Type Parameter Syntax**:
   - Use modern generic syntax: `class Repository[T: Entity]:` or `def transform[T](item: T) -> T:`.
   - Avoid legacy `TypeVar("T")` definitions unless interfacing with legacy third-party runtime frameworks.

2. **No Bare `Any` Across Domain Boundaries**:
   - Forbid bare `Any` or unstructured `dict[str, Any]` across domain and port boundaries.
   - Use strongly typed Pydantic models, immutable `@dataclass(frozen=True)` value objects, or `TypedDict`.

3. **Explicit Union & Optional Handling**:
   - Use `A | B` syntax rather than `Union[A, B]` or `Optional[A]`.
   - Do not use implicit optional types. Always default explicitly (e.g. `val: str | None = None`).

4. **Self-Documenting Custom Exception Hierarchies**:
   - Never raise generic `RuntimeError`, `ValueError`, or `Exception` for domain violations.
   - Define expressive exception hierarchies rooted in a package base error (e.g. `class HexaqueueError(Exception):`).
