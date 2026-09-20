<!-- Managed by hexaqual - DO NOT EDIT MANUALLY -->
---
trigger: always_on
description: Mandatory property-based testing and stateful Hypothesis fuzzing for state machines, parsers, and scheduling engines.
---

## Hypothesis Property-Based Testing & Invariant Fuzzing

Complex algorithms, state machines, topological sorts, and serialization channels must be validated beyond static unit examples using property-based fuzz testing with **Hypothesis**.

### Invariants & Directives
1. **State Machine Verification**:
   - Any lifecycle state machine (e.g. job transitions, preemption recovery, split/join barriers) requires a `hypothesis.stateful.RuleBasedStateMachine` suite.
   - Assert that no sequence of operations can place an entity into an invalid state, violate conservation of resources, or cause an unhandled deadlock.

2. **Parsing, Serialization & Inversion Properties**:
   - Serializers and deserializers (CloudEvent envelopes, CLI argument parsers, YAML/JSON configs) must satisfy round-trip equality:
     ```python
     @given(st.from_type(CommandPayload))
     def test_roundtrip_serialization(payload: CommandPayload):
         encoded = serialize(payload)
         decoded = deserialize(encoded)
         assert decoded == payload
     ```

3. **Deterministic Fuzz Execution**:
   - Keep Hypothesis generation deterministic and reasonably bounded (`max_examples=50`–`100` in CI) to ensure fast developer iteration.
