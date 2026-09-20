<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
trigger: always_on
description: Mandatory Google-style docstrings with Args, Returns, Raises, and Notes/Architectural Intent sections on all public APIs.
---

## Google-Style Docstrings & Architectural Intent

Every public module, class, method, and function must have a complete, well-formed **Google-style docstring**.

### Required Structure
Docstrings must document:
1. **Summary Line**: Concise imperative summary of the component's responsibility.
2. **`Args:`**: Explicit description of each parameter, its type constraints, and purpose.
3. **`Returns:`**: Description of the return value, structure, and lifecycle state.
4. **`Raises:`**: Every exception explicitly raised within the callable body or its immediate delegation paths.
5. **`Notes/Architectural Intent:`**:
   - **MANDATORY** section explaining the architectural rationale, design decisions, invariants maintained, concurrency guarantees, or hexagonal layer boundaries.
   - Answers *why* the design exists rather than merely repeating what the code does.

### Example
```python
def execute_pipeline(command: SubmitRunCommand) -> RunStatusReport:
    """Execute the batch scheduling pipeline for a run submission.

    Args:
        command: The run submission command containing spec and user credentials.

    Returns:
        RunStatusReport containing run identifier, status, and initial job counts.

    Raises:
        PermissionDeniedError: If caller lacks permissions and did not elevate.
        ValidationError: If the job specifications within the run are malformed.

    Notes/Architectural Intent:
        Enforces positive administrative elevation prior to admitting cross-tenant
        workloads. Dispatches asynchronously into the core priority queue.
    """
```
