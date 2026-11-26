"""Unit tests for IaC port interface contracts.

Notes/Architectural Intent:
    Verifies that IacAuditorPort and IacPresenterPort remain pure ABC
    contracts declaring the expected abstract method surfaces.
"""

from __future__ import annotations

from abc import ABC
from typing import Any

import pytest

from hexaqual.ports.iac import IacAuditorPort, IacPresenterPort


def test_iac_ports_are_abstract() -> None:
    """Verify IacAuditorPort and IacPresenterPort cannot be instantiated directly."""
    assert issubclass(IacAuditorPort, ABC)
    assert issubclass(IacPresenterPort, ABC)

    expected_auditor_methods = {
        "discover_assets",
        "check_tool_availability",
        "run_tofu_fmt",
        "run_tofu_validate",
        "run_tflint",
        "run_trivy",
        "run_checkov",
        "run_hadolint",
        "run_shellcheck",
    }
    assert IacAuditorPort.__abstractmethods__ == expected_auditor_methods

    expected_presenter_methods = {
        "present_iac_audit",
        "present_iac_inventory",
    }
    assert IacPresenterPort.__abstractmethods__ == expected_presenter_methods

    auditor_cls: Any = IacAuditorPort
    with pytest.raises(TypeError):
        auditor_cls()

    presenter_cls: Any = IacPresenterPort
    with pytest.raises(TypeError):
        presenter_cls()
