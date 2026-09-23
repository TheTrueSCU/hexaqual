<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
trigger: always_on
description: Mandatory blast-radius limits, atomic diff constraints, and prohibition of code placeholder truncation.
---

## Minimal Diff & Blast Radius Constraints

When generating, refactoring, or editing code within this ecosystem, autonomous agents must adhere to strict modification hygiene to preserve readability, reviewability, and git history veracity.

### 1. Minimal Blast Radius
- Modify **ONLY** the lines and symbols strictly necessary to fulfill the prompt or solve the issue.
- Do not make gratuitous changes to untouched functions, classes, or configuration files.
- Do not reformat untouched code blocks or alter whitespace in adjacent sections.

### 2. Absolute Ban on Placeholder Truncation
- **NEVER** output placeholder comments that omit existing implementation logic, such as:
  - `# ... existing code remains unchanged ...`
  - `# ... rest of class implementation goes here ...`
  - `/* TODO: keep earlier methods */`
- Any file edited or replaced must retain 100% of its existing functionality, comments, and architectural docstrings.

### 3. Preservation of Comments & Docstrings
- Existing architectural rationale, `Notes/Architectural Intent` sections, and inline explanations must be preserved.
- When refactoring logic, update corresponding docstring sections (`Args:`, `Returns:`, `Raises:`, `Notes/Architectural Intent:`) to match the new behavior.

### 4. Atomic & Self-Verifying Edits
- Keep diffs cohesive and logically isolated.
- Immediately verify that edits did not break static typing (`uv run ty check`) or linting (`uv run ruff check`) before declaring a step complete.
