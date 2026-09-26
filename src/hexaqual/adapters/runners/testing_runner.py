"""Subprocess and SQLite execution adapter for testing, mutation, and coverage tools.

Notes/Architectural Intent:
    Encapsulates mutmut runner execution, git diff extraction, coverage data queries,
    and pytest subprocess invocations behind the TestingRunnerPort boundary.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

from coverage import CoverageData

from hexaqual.adapters.code_analysis.coverage import parse_git_diff_hunks
from hexaqual.domain.testing import MutationEngine
from hexaqual.ports.testing import TestingRunnerPort

__all__ = [
    "SubprocessTestingRunnerAdapter",
]


class SubprocessTestingRunnerAdapter(TestingRunnerPort):
    """Subprocess and database execution adapter for test diagnostics."""

    def run_mutation_testing(
        self,
        package_dir: Path,
        engine: MutationEngine = MutationEngine.GREMLINS,
        reset_cache: bool = False,
        workers: int | str | None = None,
        numprocesses: int | str | None = None,
        batch_size: int | None = None,
        report_file: Path | None = None,
    ) -> int:
        """Run mutation testing on a specific package directory using the specified engine.

        Args:
            package_dir: Package directory path.
            engine: Mutation engine to use.
            reset_cache: Whether to clear incremental analysis cache.
            workers: Number of mutation workers (or 'auto') during mutation phase.
            numprocesses: Pytest-xdist worker count for baseline test execution.
            batch_size: Number of gremlins per worker batch.
            report_file: Path to write the JSON report.

        Returns:
            Exit code of mutation process.

        Notes/Architectural Intent:
            Dispatches to engine-specific runners while presenting a uniform mutation
            execution port contract.
        """
        if engine == MutationEngine.GREMLINS or str(engine).lower() == "gremlins":
            return self._run_gremlins(
                package_dir=package_dir,
                reset_cache=reset_cache,
                workers=workers,
                numprocesses=numprocesses,
                batch_size=batch_size,
                report_file=report_file,
            )
        return self._run_mutmut(package_dir=package_dir, reset_cache=reset_cache)

    def _run_mutmut(self, package_dir: Path, reset_cache: bool = False) -> int:
        """Execute mutmut runner process."""
        cache_file = package_dir / ".mutmut-cache"
        if reset_cache and cache_file.exists():
            cache_file.unlink()

        cmd = ["mutmut", "run"]
        res = subprocess.run(cmd, cwd=package_dir)
        return res.returncode

    def _run_gremlins(
        self,
        package_dir: Path,
        reset_cache: bool = False,
        workers: int | str | None = None,
        numprocesses: int | str | None = None,
        batch_size: int | None = None,
        report_file: Path | None = None,
    ) -> int:
        """Execute pytest-gremlins mutation runner."""
        cmd = [
            "pytest",
            "--rootdir=.",
            "-o",
            "addopts=",
            "--cov=src",
            "--cov-fail-under=0",
            "--gremlins",
        ]
        if reset_cache:
            cmd.append("--gremlin-clear-cache")
        if workers is not None:
            cmd.append(f"--gremlin-workers={workers}")
        else:
            cmd.append("--gremlin-parallel")
        if batch_size is not None:
            cmd.append(f"--gremlin-batch-size={batch_size}")
            cmd.append("--gremlin-batch")
        if numprocesses is not None:
            cmd.extend(["-n", str(numprocesses)])
        if report_file is not None:
            cmd.append(f"--gremlins-html-dir={report_file.parent}")
            cmd.append("--gremlin-report=json,console")
        else:
            cmd.append("--gremlin-report=json,console")

        res = subprocess.run(cmd, cwd=package_dir)
        return res.returncode

    def run_mutmut(self, package_dir: Path, reset_cache: bool = False) -> int:
        """Run mutmut on a specific package directory.

        Args:
            package_dir: Package directory path.
            reset_cache: Whether to remove package .mutmut-cache prior to execution.

        Returns:
            Exit code of mutmut process.
        """
        return self._run_mutmut(package_dir, reset_cache=reset_cache)

    def run_gremlins(
        self,
        package_dir: Path,
        reset_cache: bool = False,
        workers: int | str | None = None,
        numprocesses: int | str | None = None,
        batch_size: int | None = None,
        report_file: Path | None = None,
    ) -> int:
        """Run pytest-gremlins mutation runner on a specific package directory.

        Args:
            package_dir: Package directory path.
            reset_cache: Whether to clear incremental analysis cache.
            workers: Number of mutation workers (or 'auto') during mutation phase.
            numprocesses: Pytest-xdist worker count for baseline test execution.
            batch_size: Number of gremlins per worker batch.
            report_file: Path to write the JSON report.

        Returns:
            Exit code of pytest process.
        """
        return self._run_gremlins(
            package_dir=package_dir,
            reset_cache=reset_cache,
            workers=workers,
            numprocesses=numprocesses,
            batch_size=batch_size,
            report_file=report_file,
        )

    def read_mutation_records(
        self,
        path: Path,
        engine: MutationEngine = MutationEngine.GREMLINS,
        package_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Read surviving and timeout mutants from cache database or report.

        Args:
            path: Path to cache file (.mutmut-cache) or report file (JSON).
            engine: Mutation engine corresponding to the cache or report format.
            package_filter: Optional package name filter.

        Returns:
            List of mutant records as raw dictionaries.

        Notes/Architectural Intent:
            Dispatches to internal parser helpers (_read_gremlins_report or _read_mutmut_cache)
            to extract normalized mutant dictionaries for triage.
        """
        if engine == MutationEngine.GREMLINS or str(engine).lower() == "gremlins":
            return self._read_gremlins_report(path, package_filter=package_filter)
        return self._read_mutmut_cache(path, package_filter=package_filter)

    def _read_mutmut_cache(
        self, cache_file: Path, package_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """Read surviving and timeout mutants from SQLite cache."""
        if not cache_file.is_file():
            return []

        con = sqlite3.connect(cache_file)
        try:
            cur = con.cursor()
            query = """
            SELECT m.id, sf.filename, l.line, m.status
            FROM Mutant m
            JOIN Line l ON m.line = l.id
            JOIN SourceFile sf ON l.sourcefile = sf.id
            WHERE m.status IN ('bad_survived', 'bad_timeout')
            """
            rows = cur.execute(query).fetchall()
            results: list[dict[str, Any]] = []
            for m_id, fname, line, status in rows:
                if package_filter and package_filter not in fname:
                    continue
                results.append(
                    {
                        "id": str(m_id),
                        "filename": fname,
                        "line": line,
                        "status": status,
                    }
                )
            return results
        finally:
            con.close()

    def _read_gremlins_report(
        self, report_file: Path, package_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """Read surviving and timeout mutants from pytest-gremlins JSON report."""
        if not report_file.is_file():
            return []

        try:
            data = json.loads(report_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        results = data.get("results", [])
        records: list[dict[str, Any]] = []

        for item in results:
            status = str(item.get("status", "")).lower()
            if status not in ("survived", "timeout", "error"):
                continue

            file_path = str(item.get("file_path", ""))
            if package_filter and package_filter not in file_path:
                continue

            line_no = int(item.get("line_number", 1))
            line_content = ""
            try:
                src_path = Path(file_path)
                if src_path.is_file():
                    lines = src_path.read_text(encoding="utf-8").splitlines()
                    if 1 <= line_no <= len(lines):
                        line_content = lines[line_no - 1]
            except OSError:
                pass

            if not line_content:
                line_content = str(item.get("description", ""))

            records.append(
                {
                    "id": str(item.get("gremlin_id", "unknown")),
                    "filename": file_path,
                    "line_number": line_no,
                    "line": line_content,
                    "status": status,
                    "operator": str(item.get("operator", "")),
                    "description": str(item.get("description", "")),
                }
            )

        return records

    def read_mutmut_cache(
        self, cache_file: Path, package_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """Read surviving and timeout mutants from SQLite cache.

        Args:
            cache_file: Path to .mutmut-cache file.
            package_filter: Optional package name filter.

        Returns:
            List of mutant records as raw dictionaries.
        """
        return self._read_mutmut_cache(cache_file, package_filter=package_filter)

    def read_gremlins_report(
        self, report_file: Path, package_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """Read surviving and timeout mutants from pytest-gremlins JSON report.

        Args:
            report_file: Path to gremlins JSON report file.
            package_filter: Optional package name filter.

        Returns:
            List of mutant records as raw dictionaries.
        """
        return self._read_gremlins_report(report_file, package_filter=package_filter)

    def get_changed_lines(
        self, repo_root: Path, base_ref: str | None = None
    ) -> dict[Path, set[int]]:
        """Extract added and modified lines per file using git diff.

        Args:
            repo_root: Root workspace directory.
            base_ref: Optional git commit/ref to compare against.

        Returns:
            Mapping of absolute Path to set of modified 1-based line numbers.
        """
        cmd = ["git", "diff", "-U0"]
        if base_ref:
            cmd.append(base_ref)

        result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)
        return parse_git_diff_hunks(result.stdout, repo_root)

    def find_impacted_tests(
        self, changed_lines: dict[Path, set[int]], cov_path: Path | None = None
    ) -> set[str]:
        """Map changed lines to test contexts in .coverage database.

        Args:
            changed_lines: Mapping of file Path to modified line numbers.
            cov_path: Optional path to .coverage database.

        Returns:
            Set of pytest test node IDs.
        """
        if not cov_path or not cov_path.is_file():
            return set()

        cov_data = CoverageData(str(cov_path))
        cov_data.read()

        measured_files = {Path(p).resolve(): p for p in cov_data.measured_files()}
        impacted_tests: set[str] = set()

        for file_path, lines in changed_lines.items():
            cov_key = measured_files.get(file_path.resolve())
            if not cov_key:
                continue

            contexts_by_line = cov_data.contexts_by_lineno(cov_key)
            for lineno in lines:
                for test_context in contexts_by_line.get(lineno, []):
                    if test_context:
                        impacted_tests.add(test_context)

        return impacted_tests

    def get_tests_covering_line(
        self, file_path: str | Path, line_number: int, cov_path: Path | None = None
    ) -> list[str]:
        """Find non-empty test contexts covering a specific file line.

        Args:
            file_path: Source file path.
            line_number: 1-based line number.
            cov_path: Optional path to .coverage database.

        Returns:
            List of covering test context strings.
        """
        if not cov_path or not cov_path.is_file():
            return []

        cov_data = CoverageData(str(cov_path))
        cov_data.read()

        target_resolved = Path(file_path).resolve()
        for measured in cov_data.measured_files():
            if Path(measured).resolve() == target_resolved:
                contexts = cov_data.contexts_by_lineno(measured).get(line_number, [])
                return sorted([c for c in contexts if c])

        return []

    def audit_layer_boundary_leaks(self, cov_path: Path | None = None) -> list[tuple[str, str]]:
        """Query .coverage database for domain tests executing infra/adapter files.

        Args:
            cov_path: Optional path to .coverage database.

        Returns:
            List of (test_context, leaked_path) tuples.
        """
        if not cov_path or not cov_path.is_file():
            return []

        con = sqlite3.connect(cov_path)
        try:
            cur = con.cursor()
            query = """
            SELECT DISTINCT
                c.context,
                f.path
            FROM line_bits lb
            JOIN file f ON lb.file_id = f.id
            JOIN context c ON lb.context_id = c.id
            WHERE c.context LIKE '%test_domain%'
              AND (f.path LIKE '%/infra/%' OR f.path LIKE '%/adapters/%' OR f.path LIKE '%/infrastructure/%')
            ORDER BY c.context
            """
            return cur.execute(query).fetchall()
        except Exception:
            return []
        finally:
            con.close()

    def audit_redundant_tests(self, cov_path: Path | None = None) -> list[str]:
        """Query .coverage branch arcs for tests with zero unique branch coverage.

        Args:
            cov_path: Optional path to .coverage database.

        Returns:
            List of redundant test context strings.
        """
        if not cov_path or not cov_path.is_file():
            return []

        con = sqlite3.connect(cov_path)
        try:
            cur = con.cursor()
            query = """
            WITH ArcCoverage AS (
                SELECT file_id, from_line, to_line, context_id
                FROM arc
                WHERE context_id != (SELECT id FROM context WHERE context = '')
            ),
            UniqueCoverage AS (
                SELECT file_id, from_line, to_line
                FROM ArcCoverage
                GROUP BY file_id, from_line, to_line
                HAVING COUNT(DISTINCT context_id) = 1
            )
            SELECT DISTINCT
                c.context
            FROM context c
            WHERE c.id NOT IN (
                SELECT DISTINCT ac.context_id
                FROM ArcCoverage ac
                JOIN UniqueCoverage uc
                  ON ac.file_id = uc.file_id
                 AND ac.from_line = uc.from_line
                 AND ac.to_line = uc.to_line
            )
            AND c.context != ''
            ORDER BY c.context
            """
            rows = cur.execute(query).fetchall()
            return [r[0] for r in rows]
        except Exception:
            return []
        finally:
            con.close()

    def execute_pytest(
        self,
        test_nodes: list[str],
        extra_args: list[str] | None = None,
        cwd: Path | None = None,
    ) -> int:
        """Run pytest with specific test node IDs.

        Args:
            test_nodes: List of pytest test node targets.
            extra_args: Extra flags passed to pytest.
            cwd: Working directory.

        Returns:
            Exit code of pytest execution.
        """
        cmd = ["pytest"] + sorted(test_nodes) + (extra_args or [])
        res = subprocess.run(cmd, cwd=cwd)
        return res.returncode
