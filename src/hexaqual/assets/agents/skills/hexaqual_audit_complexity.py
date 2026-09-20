# Managed by hexaqual - DO NOT EDIT MANUALLY
"""Skill: Fast cognitive complexity linter scoped to specific files or directories.

Notes/Architectural Intent:
    Provides AI coding assistants and developers with an instant CLI helper
    to check whether modified functions comply with the cognitive complexity <= 25 limit
    enforced by complexipy without requiring a full test run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def check_complexity(target_path: str = "src/") -> int:
    """Run complexipy against the target path.

    Args:
        target_path: Path to the Python file or directory to evaluate.

    Returns:
        0 if all functions satisfy complexity <= 25, non-zero exit code otherwise.

    Raises:
        FileNotFoundError: If the target path does not exist on disk.

    Notes/Architectural Intent:
        Delegates directly to complexipy CLI with maximum complexity 25.
    """
    target = Path(target_path)
    if not target.exists():
        msg = f"Target path does not exist: {target_path}"
        raise FileNotFoundError(msg)

    cmd = ["uv", "run", "complexipy", str(target), "--max-complexity-allowed", "25"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        return result.returncode

    sys.stdout.write(f"All functions in {target_path} comply with cognitive complexity <= 25.\n")
    return 0


def main() -> None:
    """CLI entrypoint for complexity audit skill.

    Notes/Architectural Intent:
        Parses optional target argument and exits with complexipy return code.
    """
    target = sys.argv[1] if len(sys.argv) > 1 else "src/"
    try:
        exit_code = check_complexity(target)
        sys.exit(exit_code)
    except FileNotFoundError as err:
        sys.stderr.write(f"Error: {err}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
