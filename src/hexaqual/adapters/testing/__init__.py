"""Testing utilities, narrative demo recorders, and terminal event capture."""

from hexaqual.adapters.testing.events import TerminalEvent
from hexaqual.adapters.testing.narrator import CliNarrator
from hexaqual.adapters.testing.terminal import render_cli_demo_video

__all__ = [
    "CliNarrator",
    "render_cli_demo_video",
    "TerminalEvent",
]
