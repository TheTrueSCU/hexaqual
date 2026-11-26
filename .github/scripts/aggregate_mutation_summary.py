"""Aggregate pytest-gremlins JSON reports across matrix slices into Markdown.

Notes/Architectural Intent:
    Reads all ``gremlins.json`` files under a downloaded artifacts directory,
    sums totals across slices, and emits a single consolidated Markdown report
    for stdout logs, optional ``--output`` files, and ``$GITHUB_STEP_SUMMARY``.
    Uses Python standard library modules exclusively so CI summary jobs require
    zero third-party dependency installation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_SUMMARY_KEYS = (
    "total",
    "zapped",
    "survived",
    "timeout",
    "error",
    "pardoned",
)


def _relative_source_name(raw_path: str) -> str:
    """Normalize an absolute runner path to a repo-relative ``src/...`` path.

    Args:
        raw_path: Raw source file path recorded inside ``gremlins.json``.

    Returns:
        Normalized repo-relative path under ``src/...`` or the file basename.

    Notes/Architectural Intent:
        Strips runner-specific workspace prefixes so identical modules across
        parallel matrix shards merge cleanly under a single table row.
    """
    marker = "/src/"
    if marker in raw_path:
        return "src/" + raw_path.split(marker, 1)[1]
    return Path(raw_path).name


def _coerce_int(value: Any, default: int = 0) -> int:
    """Safely coerce a JSON numeric field to ``int``.

    Args:
        value: Raw value extracted from JSON.
        default: Fallback integer when ``value`` is missing or non-numeric.

    Returns:
        Parsed integer value.

    Notes/Architectural Intent:
        Prevents partial or malformed numeric values in a single slice report
        from crashing cross-slice aggregation.
    """
    if value is None or isinstance(value, bool):
        return default
    return int(value)


def _load_slice_report(report_path: Path) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    """Load and validate numeric totals and per-file stats from one ``gremlins.json``.

    Args:
        report_path: Path to a single slice ``gremlins.json`` file.

    Returns:
        Tuple of ``(slice_totals, slice_file_stats)``.

    Raises:
        OSError: If the file cannot be read.
        json.JSONDecodeError: If the file contains invalid JSON.
        ValueError: If top-level structures or counts are malformed.
        TypeError: If JSON fields have incompatible types.

    Notes/Architectural Intent:
        Isolates JSON parsing and coercion so callers can handle corrupt slice
        artifacts gracefully without losing valid sibling slice summaries.
    """
    data = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {report_path}")

    raw_summary = data.get("summary", {})
    if not isinstance(raw_summary, dict):
        raise ValueError(f"Expected 'summary' mapping in {report_path}")

    slice_totals = {key: _coerce_int(raw_summary.get(key, 0)) for key in _SUMMARY_KEYS}

    raw_files = data.get("files", {})
    if not isinstance(raw_files, dict):
        raise ValueError(f"Expected 'files' mapping in {report_path}")

    slice_files: dict[str, dict[str, int]] = {}
    for raw_file, stats in raw_files.items():
        if not isinstance(stats, dict):
            continue
        rel = _relative_source_name(str(raw_file))
        entry = slice_files.setdefault(rel, {"total": 0, "zapped": 0, "survived": 0})
        entry["total"] += _coerce_int(stats.get("total", 0))
        entry["zapped"] += _coerce_int(stats.get("zapped", 0))
        entry["survived"] += _coerce_int(stats.get("survived", 0))

    return slice_totals, slice_files


def aggregate_reports(artifacts_dir: Path) -> str:
    """Aggregate all ``gremlins.json`` reports under ``artifacts_dir``.

    Args:
        artifacts_dir: Root directory containing downloaded slice artifacts.

    Returns:
        Formatted Markdown summary string.

    Raises:
        None.

    Notes/Architectural Intent:
        Never aborts when ``artifacts_dir`` is missing or individual slice files
        are corrupted; surfaces warnings inline so CI operators always receive a
        diagnostic summary in logs and job summaries.
    """
    totals = dict.fromkeys(_SUMMARY_KEYS, 0)
    file_stats: dict[str, dict[str, int]] = {}
    warnings: list[str] = []
    valid_slices = 0

    if not artifacts_dir.exists():
        warnings.append(f"Artifacts directory `{artifacts_dir}` does not exist.")
        report_paths: list[Path] = []
    elif not artifacts_dir.is_dir():
        warnings.append(f"Artifacts path `{artifacts_dir}` is not a directory.")
        report_paths = []
    else:
        report_paths = sorted(artifacts_dir.rglob("gremlins.json"))

    skipped_reports: list[str] = []
    for report_path in report_paths:
        try:
            slice_totals, slice_files = _load_slice_report(report_path)
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            try:
                rel_report = str(report_path.relative_to(artifacts_dir))
            except ValueError:
                rel_report = str(report_path)
            skipped_reports.append(f"{rel_report} ({exc})")
            sys.stderr.write(f"Warning: skipping malformed mutation report {report_path}: {exc}\n")
            continue

        valid_slices += 1
        for key in totals:
            totals[key] += slice_totals[key]
        for rel, stats in slice_files.items():
            entry = file_stats.setdefault(rel, {"total": 0, "zapped": 0, "survived": 0})
            entry["total"] += stats["total"]
            entry["zapped"] += stats["zapped"]
            entry["survived"] += stats["survived"]

    if skipped_reports:
        warnings.append(
            f"Skipped {len(skipped_reports)} malformed report(s): "
            + ", ".join(f"`{item}`" for item in skipped_reports)
        )

    total = totals["total"]
    score = (totals["zapped"] / total * 100.0) if total else 0.0
    lines = [
        "### Consolidated Mutation Testing Summary",
        "",
        f"- **Slices Aggregated**: {valid_slices}",
        f"- **Total Gremlins**: {total}",
        f"- **Zapped**: {totals['zapped']} ({score:.1f}%)",
        f"- **Survived**: {totals['survived']}",
        (
            f"- **Timeout / Error / Pardoned**: "
            f"{totals['timeout']} / {totals['error']} / {totals['pardoned']}"
        ),
        "",
    ]

    for warning in warnings:
        lines.append(f"> **Warning**: {warning}")
    if warnings:
        lines.append("")

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


def _format_status_header(
    status_discover: str | None,
    status_audit: str | None,
) -> list[str]:
    """Build optional CI upstream job status header lines.

    Args:
        status_discover: Result string for the matrix discovery job.
        status_audit: Result string for the mutation audit matrix job.

    Returns:
        List of Markdown lines to prepend when either status is supplied.

    Notes/Architectural Intent:
        Keeps CI workflow YAML free of brittle multi-command shell redirections
        while preserving ``aggregate_reports`` as a pure aggregation function.
    """
    if status_discover is None and status_audit is None:
        return []
    header = ["### Scheduled Mutation Audit Status", ""]
    if status_discover is not None:
        header.append(f"- **Discover Slices**: {status_discover}")
    if status_audit is not None:
        header.append(f"- **Mutation Audit**: {status_audit}")
    header.append("")
    return header


def _build_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser for ``aggregate_mutation_summary``.

    Returns:
        Configured ``argparse.ArgumentParser`` instance.

    Notes/Architectural Intent:
        Uses stdlib ``argparse`` so the script runs directly in minimal CI jobs.
    """
    parser = argparse.ArgumentParser(
        description="Aggregate pytest-gremlins JSON reports across matrix slices into Markdown."
    )
    parser.add_argument(
        "artifacts_dir",
        nargs="?",
        default="artifacts",
        help="Root directory containing downloaded slice artifacts (default: artifacts).",
    )
    parser.add_argument(
        "--status-discover",
        default=None,
        help="Optional upstream discover-slices job result to include in header.",
    )
    parser.add_argument(
        "--status-audit",
        default=None,
        help="Optional upstream mutation-audit job result to include in header.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output file path to write the rendered Markdown summary.",
    )
    parser.add_argument(
        "--step-summary",
        action="store_true",
        help="Append the rendered Markdown summary directly to $GITHUB_STEP_SUMMARY.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint rendering consolidated mutation summary to stdout and optional sinks.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code (0 on success, 1 if writing a requested output fails).

    Raises:
        None.

    Notes/Architectural Intent:
        Always prints the rendered Markdown to stdout so GitHub Actions job logs
        preserve full visibility even when step-summary UI rendering is delayed
        or unavailable, and flushes writes to ``$GITHUB_STEP_SUMMARY`` explicitly.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    header_lines = _format_status_header(args.status_discover, args.status_audit)
    body = aggregate_reports(Path(args.artifacts_dir))
    markdown = "\n".join([*header_lines, body]).rstrip() + "\n"

    sys.stdout.write(markdown)
    sys.stdout.flush()

    exit_code = 0

    if args.output is not None:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(markdown, encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(f"Error: failed to write summary output to {args.output}: {exc}\n")
            exit_code = 1

    if args.step_summary:
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
        if not summary_path:
            sys.stderr.write(
                "Warning: --step-summary requested but GITHUB_STEP_SUMMARY is unset or empty.\n"
            )
        else:
            try:
                target = Path(summary_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("a", encoding="utf-8") as handle:
                    handle.write(f"\n{markdown}")
                    handle.flush()
                written_bytes = len(markdown.encode("utf-8"))
                sys.stderr.write(
                    f"Appended {written_bytes} bytes to GITHUB_STEP_SUMMARY ({target}).\n"
                )
            except OSError as exc:
                sys.stderr.write(
                    f"Error: failed to append to GITHUB_STEP_SUMMARY ({summary_path}): {exc}\n"
                )
                exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
