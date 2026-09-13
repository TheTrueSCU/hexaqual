"""Unit tests for CommandDispatcher in infra."""

from __future__ import annotations

import pytest

from hexaqual.domain.base import Command
from hexaqual.infra.dispatcher import CommandDispatcher


class DummyCommand(Command):
    """Dummy command for testing dispatcher."""

    payload: str


def test_dispatcher_register_and_dispatch() -> None:
    """Verify CommandDispatcher routes commands correctly."""
    dispatcher = CommandDispatcher()
    dispatcher.register(DummyCommand, lambda cmd: f"handled: {cmd.payload}")

    res = dispatcher.dispatch(DummyCommand(payload="hello"))
    assert res == "handled: hello"

    # Also test execute alias
    res_exec = dispatcher.execute(DummyCommand(payload="world"))
    assert res_exec == "handled: world"


def test_dispatcher_unregistered_command_raises() -> None:
    """Verify dispatching unregistered command raises KeyError."""
    dispatcher = CommandDispatcher()
    with pytest.raises(KeyError, match="No handler registered"):
        dispatcher.dispatch(DummyCommand(payload="missing"))
