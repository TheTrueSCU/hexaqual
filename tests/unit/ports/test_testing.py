"""Unit tests for testing ports ABC contracts.

Notes/Architectural Intent:
    Verifies that TestingRunnerPort and TestingPresenterPort enforce
    subclassing and method implementation contracts.
"""

from __future__ import annotations

import inspect

from hexaqual.ports.testing import TestingPresenterPort, TestingRunnerPort


def test_testing_ports_cannot_be_instantiated_directly():
    """Verify ABC contracts declare abstract methods."""
    assert inspect.isabstract(TestingRunnerPort)
    assert "execute_pytest" in TestingRunnerPort.__abstractmethods__
    assert inspect.isabstract(TestingPresenterPort)
    assert "present_mutation_summary" in TestingPresenterPort.__abstractmethods__
