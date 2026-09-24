"""CLI help extraction and USAGE.md documentation generator and validator.

Notes/Architectural Intent:
    Executes CLI tools in parallel with --help, strips ANSI escape sequences,
    discovers subcommands via BFS, and builds or validates USAGE.md documents.
"""

from __future__ import annotations

import collections
import concurrent.futures
import difflib
import os
import re
import subprocess
from pathlib import Path

__all__ = [
    "clean_help_output",
    "extract_command_help",
    "extract_command_tree_bfs",
    "extract_commands_parallel",
    "extract_subcommands_from_help",
    "UsageDocsAnalyzer",
]


def clean_help_output(output: str) -> str:
    """Strip ANSI escape sequences, warnings, and trailing whitespace from help text."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    clean = ansi_escape.sub("", output).strip()

    lines = clean.splitlines()
    filtered_lines: list[str] = []
    capture = False

    for line in lines:
        if "Usage:" in line or "usage:" in line or capture or "╭─" in line or "Commands" in line:
            capture = True
            filtered_lines.append(line.rstrip())

    final_lines = filtered_lines if filtered_lines else [line.rstrip() for line in lines]
    return "\n".join(final_lines)


def extract_command_help(
    cmd: list[str],
    timeout: int = 30,
    cwd: Path | str | None = None,
) -> str:
    """Execute a command with --help and capture formatted text output.

    Args:
        cmd: Command and arguments tokens.
        timeout: Subprocess execution timeout in seconds.
        cwd: Optional working directory for command execution.

    Returns:
        Cleaned help text output string.
    """
    env = dict(os.environ, NO_COLOR="1", TERM="dumb")
    try:
        res = subprocess.run(
            ["uv", "run", *cmd, "--help"],
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
        )
        raw = res.stdout if res.stdout.strip() else res.stderr
        return clean_help_output(raw)
    except subprocess.TimeoutExpired:
        try:
            res = subprocess.run(
                ["uv", "run", *cmd, "--help"],
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout,
                cwd=str(cwd) if cwd else None,
            )
            raw = res.stdout if res.stdout.strip() else res.stderr
            return clean_help_output(raw)
        except Exception as e:
            return f"Error running {' '.join(cmd)}: {e}"
    except Exception as e:
        return f"Error running {' '.join(cmd)}: {e}"


def extract_subcommands_from_help(help_text: str) -> list[str]:
    """Parse out subcommand names from Typer or click formatted help text."""
    subcommands: list[str] = []
    in_commands_section = False

    for line in help_text.splitlines():
        if (
            "Commands" in line
            or "subcommands" in line.lower()
            or ("╭─" in line and "Commands" in line)
        ):
            in_commands_section = True
            continue

        if in_commands_section:
            if not line.strip() or line.startswith("╰─"):
                continue

            clean_line = line.strip("│ \t")
            match = re.match(r"^([a-zA-Z0-9_\-]+)\s+", clean_line)
            if match:
                cmd_name = match.group(1)
                if cmd_name not in ("Commands", "Usage", "Options", "Arguments"):
                    subcommands.append(cmd_name)

    return subcommands


def extract_command_tree_bfs(
    root_cmd: list[str],
    max_depth: int = 3,
    max_workers: int = 8,
    timeout: int = 30,
    cwd: Path | str | None = None,
) -> dict[tuple[str, ...], str]:
    """Perform breadth-first traversal discovering and extracting all subcommands."""
    results: dict[tuple[str, ...], str] = {}
    queue: collections.deque[list[str]] = collections.deque([root_cmd])

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        while queue:
            batch: list[list[str]] = []
            while queue:
                batch.append(queue.popleft())

            future_to_cmd = {
                executor.submit(extract_command_help, cmd, timeout, cwd): cmd
                for cmd in batch
                if len(cmd) - len(root_cmd) < max_depth
            }

            for future in concurrent.futures.as_completed(future_to_cmd):
                cmd = future_to_cmd[future]
                help_text = future.result()
                results[tuple(cmd)] = help_text

                subcmds = extract_subcommands_from_help(help_text)
                for sub in subcmds:
                    child_cmd = [*cmd, sub]
                    if tuple(child_cmd) not in results:
                        queue.append(child_cmd)

    return results


def extract_commands_parallel(
    cmd_list: list[list[str]],
    max_workers: int = 8,
    timeout: int = 30,
    cwd: Path | str | None = None,
) -> dict[tuple[str, ...], str]:
    """Extract help text for a batch of independent commands in parallel."""
    results: dict[tuple[str, ...], str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_cmd = {
            executor.submit(extract_command_help, cmd, timeout, cwd): cmd for cmd in cmd_list
        }
        for future in concurrent.futures.as_completed(future_to_cmd):
            cmd = future_to_cmd[future]
            results[tuple(cmd)] = future.result()
    return results


class UsageDocsAnalyzer:
    """Secondary adapter wrapping CLI help extraction and documentation validation."""

    def verify_usage_file(self, usage_path: Path, expected_content: str) -> tuple[bool, str]:
        """Verify that an existing USAGE.md matches expected content.

        Args:
            usage_path: Path to target USAGE.md.
            expected_content: Freshly rendered markdown string.

        Returns:
            Tuple of (in_sync: bool, diff: str).
        """
        if not usage_path.is_file():
            return False, f"File {usage_path} does not exist."

        current_content = usage_path.read_text(encoding="utf-8")
        if current_content.strip() == expected_content.strip():
            return True, ""

        diff_lines = list(
            difflib.unified_diff(
                current_content.splitlines(),
                expected_content.splitlines(),
                fromfile=f"a/{usage_path.name}",
                tofile=f"b/{usage_path.name}",
                lineterm="",
            )
        )
        return False, "\n".join(diff_lines[:40])
