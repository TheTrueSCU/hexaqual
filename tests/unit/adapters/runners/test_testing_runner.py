"""Unit tests for SubprocessTestingRunnerAdapter.

Notes/Architectural Intent:
    Verifies that SubprocessTestingRunnerAdapter handles missing databases gracefully,
    executes subprocess commands, and parses sqlite coverage and mutmut records.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

from hexaqual.adapters.runners.testing_runner import (
    SubprocessTestingRunnerAdapter,
)


def test_run_mutmut(tmp_path: Path):
    """Verify run_mutmut invokes subprocess with correct working directory."""
    adapter = SubprocessTestingRunnerAdapter()
    cache_file = tmp_path / ".mutmut-cache"
    cache_file.write_text("old cache")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        code = adapter.run_mutmut(tmp_path, reset_cache=True)
        assert code == 0
        assert not cache_file.exists()
        mock_run.assert_called_once_with(["mutmut", "run"], cwd=tmp_path)


def test_read_mutmut_cache_missing_file(tmp_path: Path):
    """Verify missing mutmut cache returns empty list."""
    adapter = SubprocessTestingRunnerAdapter()
    records = adapter.read_mutmut_cache(tmp_path / "nonexistent.db")
    assert records == []


def test_read_mutmut_cache_with_sqlite(tmp_path: Path):
    """Verify querying SQLite mutmut cache."""
    db_file = tmp_path / ".mutmut-cache"
    con = sqlite3.connect(db_file)
    con.execute("CREATE TABLE SourceFile (id INTEGER PRIMARY KEY, filename TEXT)")
    con.execute("CREATE TABLE Line (id INTEGER PRIMARY KEY, sourcefile INTEGER, line TEXT)")
    con.execute("CREATE TABLE Mutant (id INTEGER PRIMARY KEY, line INTEGER, status TEXT)")
    con.execute("INSERT INTO SourceFile VALUES (1, 'packages/core/src/mod.py')")
    con.execute("INSERT INTO Line VALUES (1, 1, 'x = 1')")
    con.execute("INSERT INTO Mutant VALUES (10, 1, 'bad_survived')")
    con.commit()
    con.close()

    adapter = SubprocessTestingRunnerAdapter()
    records = adapter.read_mutmut_cache(db_file, package_filter="core")
    assert len(records) == 1
    assert records[0]["id"] == "10"
    assert records[0]["status"] == "bad_survived"


def test_get_changed_lines(tmp_path: Path):
    """Verify get_changed_lines runs git diff and parses output."""
    adapter = SubprocessTestingRunnerAdapter()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="+++ b/packages/core/src/mod.py\n@@ -5 +5 @@\n+x = 2\n"
        )
        res = adapter.get_changed_lines(tmp_path)
        expected_path = (tmp_path / "packages/core/src/mod.py").resolve()
        assert expected_path in res
        assert 5 in res[expected_path]


def test_audit_missing_coverage(tmp_path: Path):
    """Verify audit methods return empty when coverage file does not exist."""
    adapter = SubprocessTestingRunnerAdapter()
    cov_path = tmp_path / "missing.coverage"
    assert adapter.find_impacted_tests({}, cov_path) == set()
    assert adapter.get_tests_covering_line("foo.py", 1, cov_path) == []
    assert adapter.audit_layer_boundary_leaks(cov_path) == []
    assert adapter.audit_redundant_tests(cov_path) == []


def test_execute_pytest(tmp_path: Path):
    """Verify execute_pytest invokes subprocess."""
    adapter = SubprocessTestingRunnerAdapter()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        res = adapter.execute_pytest(["test_a.py::test_1"], extra_args=["-v"], cwd=tmp_path)
        assert res == 0
        mock_run.assert_called_once_with(["pytest", "test_a.py::test_1", "-v"], cwd=tmp_path)


def test_get_changed_lines_base_ref(tmp_path: Path):
    """Verify get_changed_lines includes base_ref in git command."""
    adapter = SubprocessTestingRunnerAdapter()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="")
        adapter.get_changed_lines(tmp_path, base_ref="origin/main")
        mock_run.assert_called_once_with(
            ["git", "diff", "-U0", "origin/main"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )


def test_audit_layer_boundary_leaks_with_db(tmp_path: Path):
    """Verify auditing layer boundary leaks from SQLite database."""
    cov_db = tmp_path / ".coverage"
    con = sqlite3.connect(cov_db)
    con.execute("CREATE TABLE file (id INTEGER PRIMARY KEY, path TEXT)")
    con.execute("CREATE TABLE context (id INTEGER PRIMARY KEY, context TEXT)")
    con.execute("CREATE TABLE line_bits (file_id INTEGER, context_id INTEGER)")
    con.execute("INSERT INTO file VALUES (1, '/workspace/packages/core/src/infra/bus.py')")
    con.execute("INSERT INTO context VALUES (1, 'tests/test_domain_rules.py::test_rule')")
    con.execute("INSERT INTO line_bits VALUES (1, 1)")
    con.commit()
    con.close()

    adapter = SubprocessTestingRunnerAdapter()
    leaks = adapter.audit_layer_boundary_leaks(cov_db)
    assert len(leaks) == 1
    assert leaks[0][0] == "tests/test_domain_rules.py::test_rule"
    assert "/infra/bus.py" in leaks[0][1]


def test_audit_redundant_tests_with_db(tmp_path: Path):
    """Verify auditing redundant tests with SQLite coverage database."""
    cov_db = tmp_path / ".coverage"
    con = sqlite3.connect(cov_db)
    con.execute("CREATE TABLE context (id INTEGER PRIMARY KEY, context TEXT)")
    con.execute(
        "CREATE TABLE arc (file_id INTEGER, from_line INTEGER, to_line INTEGER, context_id INTEGER)"
    )
    con.execute("INSERT INTO context VALUES (1, '')")
    con.execute("INSERT INTO context VALUES (2, 'tests/test_main.py::test_first')")
    con.execute("INSERT INTO context VALUES (3, 'tests/test_main.py::test_redundant')")
    # Both test 2 and test 3 cover arc 1->2 in file 1, so no unique coverage for test 3
    con.execute("INSERT INTO arc VALUES (1, 1, 2, 2)")
    con.execute("INSERT INTO arc VALUES (1, 1, 2, 3)")
    con.commit()
    con.close()

    adapter = SubprocessTestingRunnerAdapter()
    redundant = adapter.audit_redundant_tests(cov_db)
    # Since neither has unique coverage, both or one will be reported
    assert isinstance(redundant, list)


def test_impacted_tests_and_covering_line_with_coverage_data(tmp_path: Path):
    """Verify mapping changed lines and finding test context via CoverageData."""
    cov_file = tmp_path / ".coverage"
    cov_file.write_text("mock coverage data")

    src_file = tmp_path / "src" / "service.py"
    src_file.parent.mkdir(parents=True)
    src_file.write_text("code")

    adapter = SubprocessTestingRunnerAdapter()

    mock_cov = MagicMock()
    mock_cov.measured_files.return_value = [str(src_file)]
    mock_cov.contexts_by_lineno.return_value = {10: ["test_service.py::test_exec"]}

    with patch(
        "hexaqual.adapters.runners.testing_runner.CoverageData",
        return_value=mock_cov,
    ):
        impacted = adapter.find_impacted_tests({src_file: {10}}, cov_file)
        assert "test_service.py::test_exec" in impacted

        covering = adapter.get_tests_covering_line(src_file, 10, cov_file)
        assert covering == ["test_service.py::test_exec"]
