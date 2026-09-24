"""Code analysis and AST/CST inspection adapters for hexaqual."""

from hexaqual.adapters.code_analysis.all_statements import (
    AllStatementsAnalyzer,
    check_file_all,
    fix_file_all,
)
from hexaqual.adapters.code_analysis.coverage import (
    parse_git_diff_hunks,
)
from hexaqual.adapters.code_analysis.doc_links import (
    CheckDocLinksHandler,
    extract_anchors_from_file,
    scan_doc_links,
    slugify_heading,
)
from hexaqual.adapters.code_analysis.extras_parity import (
    ExtraParityViolation,
    ExtrasParityAnalyzer,
    audit_extras_parity,
    generate_extras_mermaid_diagram,
)
from hexaqual.adapters.code_analysis.import_linter import (
    build_import_linter_toml,
    update_pyproject_toml,
)
from hexaqual.adapters.code_analysis.mutmut import (
    classify_mutant_line,
)
from hexaqual.adapters.code_analysis.pydeps import (
    check_all_diagrams,
    check_overview_diagram,
    check_package_diagram,
    generate_all_diagrams,
    generate_overview_diagram,
    generate_package_diagram,
)
from hexaqual.adapters.code_analysis.test_parity import (
    TestParityAnalyzer,
    check_architecture_test_parity,
    check_package_parity,
    check_src_to_test_symmetry,
    check_test_directories_inits,
)
from hexaqual.adapters.code_analysis.usage_docs import (
    UsageDocsAnalyzer,
    clean_help_output,
    extract_command_help,
    extract_command_tree_bfs,
    extract_commands_parallel,
    extract_subcommands_from_help,
)

__all__ = [
    "AllStatementsAnalyzer",
    "audit_extras_parity",
    "build_import_linter_toml",
    "check_all_diagrams",
    "check_architecture_test_parity",
    "check_file_all",
    "check_overview_diagram",
    "check_package_diagram",
    "check_package_parity",
    "check_src_to_test_symmetry",
    "check_test_directories_inits",
    "CheckDocLinksHandler",
    "classify_mutant_line",
    "clean_help_output",
    "extract_anchors_from_file",
    "extract_command_help",
    "extract_command_tree_bfs",
    "extract_commands_parallel",
    "extract_subcommands_from_help",
    "ExtraParityViolation",
    "ExtrasParityAnalyzer",
    "fix_file_all",
    "generate_all_diagrams",
    "generate_extras_mermaid_diagram",
    "generate_overview_diagram",
    "generate_package_diagram",
    "parse_git_diff_hunks",
    "scan_doc_links",
    "slugify_heading",
    "TestParityAnalyzer",
    "update_pyproject_toml",
    "UsageDocsAnalyzer",
]
