"""Aggregate pytest-gremlins JSON reports across matrix slices into Markdown.

Notes/Architectural Intent:
    Reads all ``gremlins.json`` files under a downloaded artifacts directory,
    sums totals across slices, and prints a single consolidated Markdown report
    for ``$GITHUB_STEP_SUMMARY``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _relative_source_name(raw_path: str) -> str:
    """Normalize an absolute runner path to a repo-relative ``src/...`` path."""
    marker = "/src/"
    if marker in raw_path:
        return "src/" + raw_path.split(marker, 1)[1]
    return Path(raw_path).name


def aggregate_reports(artifacts_dir: Path) -> str:
    """Aggregate all ``gremlins.json`` reports under ``artifacts_dir``.

    Args:
        artifacts_dir: Root directory containing downloaded slice artifacts.

    Returns:
        Formatted Markdown summary string.
    """
    report_paths = sorted(artifacts_dir.rglob("gremlins.json"))
    totals = {
        "total": 0,
        "zapped": 0,
        "survived": 0,
        "timeout": 0,
        "error": 0,
        "pardoned": 0,
    }
    file_stats: dict[str, dict[str, int]] = {}

    for report_path in report_paths:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        summary = data.get("summary", {})
        for key in totals:
            totals[key] += int(summary.get(key, 0))
        for raw_file, stats in data.get("files", {}).items():
            rel = _relative_source_name(raw_file)
            entry = file_stats.setdefault(rel, {"total": 0, "zapped": 0, "survived": 0})
            entry["total"] += int(stats.get("total", 0))
            entry["zapped"] += int(stats.get("zapped", 0))
            entry["survived"] += int(stats.get("survived", 0))

    total = totals["total"]
    score = (totals["zapped"] / total * 100.0) if total else 0.0
    lines = [
        "### Consolidated Mutation Testing Summary",
        "",
        f"- **Slices Aggregated**: {len(report_paths)}",
        f"- **Total Gremlins**: {total}",
        f"- **Zapped**: {totals['zapped']} ({score:.1f}%)",
        f"- **Survived**: {totals['survived']}",
        f"- **Timeout / Error / Pardoned**: {totals['timeout']} / {totals['error']} / {totals['pardoned']}",
        "",
    ]

    top_survivors = sorted(
        ((name, s) for name, s in file_stats.items() if s["survived"] > 0),
        key=lambda item: (-item[1]["survived"], item[0]),
    )[:15]
    if top_survivors:
        lines.extend(
            [
                "#### Top Files with Surviving Gremlins",
                "",
                "| File | Total | Zapped | Survived | Score |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for name, stats in top_survivors:
            f_total = stats["total"]
            f_pct = (stats["zapped"] / f_total * 100.0) if f_total else 0.0
            lines.append(
                f"| `{name}` | {f_total} | {stats['zapped']} | {stats['survived']} | {f_pct:.1f}% |"
            )
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    """CLI entrypoint writing aggregated summary to stdout."""
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts")
    print(aggregate_reports(root))


if __name__ == "__main__":
    main()
