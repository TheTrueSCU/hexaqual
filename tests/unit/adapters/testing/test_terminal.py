"""Unit tests for terminal testing helpers."""

from hexaqual.adapters.testing.terminal import render_cli_demo_video


def test_render_cli_demo_video_callable() -> None:
    """Verify render_cli_demo_video helper is exported and callable."""
    assert callable(render_cli_demo_video)
