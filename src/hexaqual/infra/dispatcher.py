"""Lightweight command dispatcher for Hexaqual.

Notes/Architectural Intent:
    Provides a decoupled command-to-handler routing mechanism without framework dependencies,
    allowing single-shot commands to be dispatched cleanly while complex multi-step pipelines
    run as native hexaflow.Workflow DAGs.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from hexaqual.domain.base import Command

C = TypeVar("C", bound=Command)
Handler = Callable[[Any], Any]


class CommandDispatcher:
    """Synchronous registry and router mapping Command types to their handler functions."""

    def __init__(self) -> None:
        self._handlers: dict[type[Command], Handler] = {}

    def register(self, command_type: type[C], handler: Callable[[C], Any]) -> None:
        """Register a handler for a specific Command type."""
        self._handlers[command_type] = handler

    def dispatch(self, command: Command) -> Any:
        """Route a Command instance to its registered handler and return result."""
        handler = self._handlers.get(type(command))
        if handler is None:
            raise KeyError(f"No handler registered for command '{type(command).__name__}'")
        return handler(command)

    def execute(self, command: Command) -> Any:
        """Alias for dispatch to ensure full drop-in compatibility."""
        return self.dispatch(command)


__all__ = [
    "CommandDispatcher",
]
