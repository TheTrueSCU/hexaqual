<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
trigger: always_on
description: Mandatory invariants for hermetically sealed test fixtures, zero filesystem/socket pollution, and teardown symmetry.
---

## Hermetic Testing & Fixture Discipline

Tests must execute in complete isolation with zero global side-effects, zero socket pollution, and zero mutation of user configuration or developer home directories.

### Invariants & Directives
1. **Isolated Filesystem Roots (`tmp_path`)**:
   - Tests must never create, read, or mutate files in `~/.hexaqueue`, `~/.hexaflow`, or real user directories.
   - Always inject and configure storage directories using pytest's `tmp_path` fixture or in-memory virtual adapters.
   - Any test writing to disk must clean up its files or run within a temporary directory.

2. **Zero Network Socket Pollution**:
   - Unit tests must never bind to live external sockets or make real HTTP/gRPC network calls.
   - Use in-memory event buses, test transport channels, or local stubs.

3. **Environment & Global State Teardown**:
   - Any fixture that mutates `os.environ`, alters system clock, or registers global singleton providers must use a `yield` fixture that resets state on teardown:
     ```python
     @pytest.fixture
     def hermetic_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
         monkeypatch.setenv("HOME", str(tmp_path))
         yield
         # monkeypatch cleans up automatically on fixture exit
     ```

4. **Single-Purpose Fixtures**:
   - Keep test fixtures focused on a single responsibility. Avoid sprawling monolithic fixtures with branching conditional logic.
   - Compose fine-grained fixtures together rather than creating mega-fixtures.
