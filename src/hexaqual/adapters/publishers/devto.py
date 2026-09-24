"""Medium/DEV.to article publisher for Hexastack docs/medium drafts.

Notes/Architectural Intent:
    Medium's public API is deprecated (no new tokens issued after 2025). The
    recommended two-pass workflow is:

    Pass 1 — Draft upload:
        POST each article to DEV.to as a draft.  The response ``id`` is stable
        regardless of draft/published state and is written back into the
        article's YAML front matter as ``devto_id``.  Draft URLs are *not*
        stored because DEV.to preview links may change on publish.

    Pass 2 — Publish + URL capture:
        PATCH each draft to published (in topological order, respecting
        cross-article dependencies).  The final stable URL is captured from the
        API response and written into ``devto_url`` in front matter and into
        the README URL registry table.

    After DEV.to publication, use Medium's "Import a Story" feature
    (https://medium.com/p/import) to syndicate.  Medium auto-sets the
    canonical URL pointing back to DEV.to, preserving SEO ownership.

Cross-linking convention:
    In article markdown bodies, use ``devto://slug`` as a placeholder URI for
    links to other articles in the series.  On publish, ``medium-publish``
    resolves known slugs to their final DEV.to URLs before POSTing.
    Example::

        [See also: uv Monorepo Pattern](devto://uv-monorepo)
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import yaml
from rich.console import Console

from hexaqual.adapters.workspace import get_repo_root
from hexaqual.ports.publishers import ArticlePublisherPort

console = Console()

DEVTO_API_BASE = "https://dev.to/api"
MEDIUM_IMPORT_URL = "https://medium.com/p/import"
_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_DEVTO_LINK_RE = re.compile(r"\(devto://([a-z0-9\-]+)\)")


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class FrontMatter:
    """Parsed YAML front matter extracted from a markdown draft.

    Notes/Architectural Intent:
        Parsed using PyYAML ``safe_load`` for correctness and simplicity.
        Unknown keys are preserved in ``extra`` so round-trip writes don't
        silently drop fields added in the future.

    Attributes:
        title: Article title.
        subtitle: Optional subtitle (used as DEV.to description).
        tags: List of tag slugs (max 4 for DEV.to, alphanumeric).
        canonical_url: Canonical URL set after first DEV.to publication.
        status: Draft status string (e.g. "draft", "published").
        devto_id: DEV.to article ID — set after draft upload, stable forever.
        devto_url: Final DEV.to URL — set after publication, stable forever.
        medium_url: Medium URL — set after Medium import.
        extra: All other front matter keys preserved for round-trip writes.
    """

    title: str = ""
    subtitle: str = ""
    tags: list[str] = field(default_factory=list)
    canonical_url: str = ""
    status: str = "draft"
    devto_id: int | None = None
    devto_url: str = ""
    medium_url: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArticlePayload:
    """Resolved article ready to POST or PATCH to DEV.to.

    Attributes:
        front_matter: Parsed front matter.
        body_markdown: Full markdown body (front matter stripped).
        slug: Filename stem used as the article identifier.
        path: Absolute path to the source markdown file.
    """

    front_matter: FrontMatter
    body_markdown: str
    slug: str
    path: Path


# ---------------------------------------------------------------------------
# Front-matter parsing and writing
# ---------------------------------------------------------------------------


def _parse_article(text: str, path: Path) -> ArticlePayload:
    """Parse a full markdown file into an ArticlePayload.

    Args:
        text: Raw markdown file contents.
        path: Absolute path to the source file (for writeback).

    Returns:
        ArticlePayload with parsed FrontMatter and stripped body.

    Raises:
        SystemExit: If no front matter block is found or YAML is invalid.

    Notes/Architectural Intent:
        Uses PyYAML ``safe_load`` which handles nested structures, multi-line
        strings, and all standard YAML types without a custom parser.
    """
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        console.print("[red]Error:[/] No YAML front matter found (expected --- block at top).")
        sys.exit(1)

    raw_yaml = match.group(1)
    body = text[match.end() :]

    try:
        data: dict[str, Any] = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError as exc:
        console.print(f"[red]YAML parse error:[/] {exc}")
        sys.exit(1)

    tags: list[str] = data.pop("tags", []) or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    fm = FrontMatter(
        title=str(data.pop("title", "")),
        subtitle=str(data.pop("subtitle", "")),
        tags=tags,
        canonical_url=str(data.pop("canonical_url", "") or ""),
        status=str(data.pop("status", "draft")),
        devto_id=data.pop("devto_id", None),
        devto_url=str(data.pop("devto_url", "") or ""),
        medium_url=str(data.pop("medium_url", "") or ""),
        extra=data,
    )
    return ArticlePayload(front_matter=fm, body_markdown=body, slug=path.stem, path=path)


def _write_front_matter(payload: ArticlePayload) -> None:
    """Write updated front matter back to the source markdown file.

    Args:
        payload: ArticlePayload with updated FrontMatter fields.

    Raises:
        SystemExit: On I/O error.

    Notes/Architectural Intent:
        Reconstructs the YAML block from the FrontMatter dataclass, then
        splices it back ahead of the body.  All ``extra`` keys are preserved
        so unknown fields added in future are not lost on writeback.
    """
    fm = payload.front_matter
    data: dict[str, Any] = {
        "title": fm.title,
        "subtitle": fm.subtitle,
        "status": fm.status,
        "tags": fm.tags,
        **fm.extra,
    }
    # Only emit tracking fields if they have values, to keep drafts clean
    if fm.devto_id is not None:
        data["devto_id"] = fm.devto_id
    if fm.devto_url:
        data["devto_url"] = fm.devto_url
        data["canonical_url"] = fm.devto_url
    elif fm.canonical_url:
        data["canonical_url"] = fm.canonical_url
    if fm.medium_url:
        data["medium_url"] = fm.medium_url

    yaml_block = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    new_content = f"---\n{yaml_block}---\n{payload.body_markdown}"
    payload.path.write_text(new_content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Cross-link resolution
# ---------------------------------------------------------------------------


def _build_slug_url_map(medium_dir: Path) -> dict[str, str]:
    """Build a mapping of article slug → DEV.to URL from all local drafts.

    Args:
        medium_dir: Path to the docs/medium/ directory.

    Returns:
        Dict mapping slug (filename stem) to known devto_url.

    Notes/Architectural Intent:
        Only articles with a non-empty ``devto_url`` in front matter are
        included.  Unknown slugs are left as ``devto://slug`` in the posted
        body so they can be resolved in a later pass.
    """
    slug_map: dict[str, str] = {}
    for md_file in sorted(medium_dir.glob("*.md")):
        if md_file.name == "README.md":
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            payload = _parse_article(text, md_file)
            if payload.front_matter.devto_url:
                slug_map[payload.slug] = payload.front_matter.devto_url
        except SystemExit:
            continue
    return slug_map


def _resolve_cross_links(body: str, slug_map: dict[str, str]) -> str:
    """Replace ``devto://slug`` placeholders with known DEV.to URLs.

    Args:
        body: Raw markdown body string.
        slug_map: Mapping of slug → devto_url for articles with known URLs.

    Returns:
        Body with resolvable placeholders substituted.

    Notes/Architectural Intent:
        Placeholders for articles not yet published are left intact so that
        a subsequent publish pass can resolve them without manual editing.
    """

    def _replace(m: re.Match) -> str:
        slug = m.group(1)
        url = slug_map.get(slug)
        return f"({url})" if url else m.group(0)

    return _DEVTO_LINK_RE.sub(_replace, body)


# ---------------------------------------------------------------------------
# File resolution
# ---------------------------------------------------------------------------


def _resolve_article_path(slug: str, medium_dir: Path | None = None) -> Path:
    """Resolve the absolute path to a docs/medium article by slug or path.

    Args:
        slug: File stem, filename, or path (e.g. "ai-guardrails-manifesto"
              or "docs/medium/ai-guardrails-manifesto.md").
        medium_dir: Optional path to the medium drafts directory.

    Returns:
        Resolved absolute Path to the markdown file.

    Raises:
        SystemExit: If the file cannot be located.

    Notes/Architectural Intent:
        Accepts both bare slugs and full paths so the command works whether
        the user tab-completes the filename or types the stem.
    """
    candidate = Path(slug)
    if candidate.exists():
        return candidate.resolve()
    if not candidate.suffix:
        candidate = candidate.with_suffix(".md")
    if candidate.exists():
        return candidate.resolve()

    if medium_dir is None:
        root = get_repo_root()
        medium_dir = root / "docs" / "medium"

    name = Path(slug).stem
    if (medium_dir / f"{name}.md").exists():
        return (medium_dir / f"{name}.md").resolve()
    for path in medium_dir.glob("*.md"):
        if path.stem == name or path.name == name:
            return path

    console.print(f"[red]Error:[/] Cannot find article [bold]{slug!r}[/] under {medium_dir}")
    raise SystemExit(1)


def _get_medium_dir() -> Path:
    """Return the docs/medium/ directory in the workspace root.

    Returns:
        Absolute Path to the docs/medium/ directory.

    Raises:
        SystemExit: If the directory does not exist.
    """
    medium_dir = get_repo_root() / "docs" / "medium"
    if not medium_dir.is_dir():
        console.print(f"[red]Error:[/] {medium_dir} does not exist.")
        sys.exit(1)
    return medium_dir


def _all_unposted_articles(medium_dir: Path) -> list[ArticlePayload]:
    """Return all articles in docs/medium/ that have not yet been uploaded.

    Args:
        medium_dir: Path to the docs/medium/ directory.

    Returns:
        List of ArticlePayload for articles without a ``devto_id``.

    Notes/Architectural Intent:
        Articles that already have a ``devto_id`` are skipped — they were
        already uploaded as drafts and do not need re-uploading.
    """
    unposted: list[ArticlePayload] = []
    for md_file in sorted(medium_dir.glob("*.md")):
        if md_file.name == "README.md":
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            payload = _parse_article(text, md_file)
            if payload.front_matter.devto_id is None:
                unposted.append(payload)
        except SystemExit:
            continue
    return unposted


# ---------------------------------------------------------------------------
# DEV.to API
# ---------------------------------------------------------------------------


def _devto_tags(tags: list[str]) -> list[str]:
    """Normalise tags for DEV.to: lowercase, alphanumeric only, max 4.

    Args:
        tags: Raw tag strings from front matter.

    Returns:
        List of at most 4 DEV.to-compatible tag slugs.

    Notes/Architectural Intent:
        DEV.to tags must be alphanumeric (underscores allowed). Hyphens are
        replaced with empty string to match their validation rules.
    """
    normalised: list[str] = []
    for tag in tags:
        clean = re.sub(r"[^a-z0-9]", "", tag.lower().replace("-", ""))
        if clean:
            normalised.append(clean)
    return normalised[:4]


def _devto_request(
    method: str,
    path: str,
    api_key: str,
    json: dict | None = None,
) -> dict:
    """Execute a DEV.to API request and return the parsed JSON response.

    Args:
        method: HTTP method ("POST" or "PATCH").
        path: API path relative to the base URL (e.g. "/articles").
        api_key: DEV.to integration API key.
        json: Optional JSON request body dict.

    Returns:
        Parsed JSON response as a dict.

    Raises:
        SystemExit: On network error or non-2xx HTTP response.

    Notes/Architectural Intent:
        Centralises auth headers and error handling for all DEV.to API calls.
    """
    url = f"{DEVTO_API_BASE}{path}"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/vnd.forem.api-v1+json",
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.request(method, url, headers=headers, json=json)
    except httpx.RequestError as exc:
        console.print(f"[red]Network error:[/] {exc}")
        sys.exit(1)

    if resp.status_code not in (200, 201):
        console.print(f"[red]DEV.to API error {resp.status_code}:[/] {resp.text}")
        sys.exit(1)

    return resp.json()


def _upload_draft(payload: ArticlePayload, api_key: str, slug_map: dict[str, str]) -> dict:
    """POST a new draft article to DEV.to.

    Args:
        payload: Resolved article payload.
        api_key: DEV.to integration API key.
        slug_map: Known slug→URL map for cross-link resolution.

    Returns:
        Parsed DEV.to API response dict.

    Raises:
        SystemExit: If the article already has a devto_id.

    Notes/Architectural Intent:
        Draft URLs returned by the API are intentionally NOT stored because
        they are temporary preview links that may change on publication.
        Only ``devto_id`` is written back to front matter.
    """
    if payload.front_matter.devto_id is not None:
        console.print(
            f"[yellow]Skip:[/] {payload.slug} already has devto_id="
            f"{payload.front_matter.devto_id}. Use --publish to publish it."
        )
        sys.exit(0)

    fm = payload.front_matter
    body = _resolve_cross_links(payload.body_markdown, slug_map)

    article: dict[str, Any] = {
        "title": fm.title,
        "body_markdown": body,
        "published": False,
        "tags": _devto_tags(fm.tags),
        "ai_disclosure": "ai_assisted",
    }
    if fm.subtitle:
        article["description"] = fm.subtitle
    if series := fm.extra.get("series"):
        article["series"] = str(series)

    return _devto_request("POST", "/articles", api_key, json={"article": article})


def _publish_draft(payload: ArticlePayload, api_key: str, slug_map: dict[str, str]) -> dict:
    """PATCH an existing draft to published state on DEV.to.

    Args:
        payload: Resolved article payload (must have devto_id).
        api_key: DEV.to integration API key.
        slug_map: Known slug→URL map for cross-link resolution in body update.

    Returns:
        Parsed DEV.to API response dict containing the final stable URL.

    Raises:
        SystemExit: If the article has no devto_id to publish.

    Notes/Architectural Intent:
        Uses PATCH /articles/{id} to transition draft→published and also
        sends an updated body with resolved cross-links now that more articles
        may have their final DEV.to URLs available.
    """
    if payload.front_matter.devto_id is None:
        console.print(
            f"[red]Error:[/] {payload.slug} has no devto_id. "
            "Upload as draft first with: medium-publish " + payload.slug
        )
        sys.exit(1)

    fm = payload.front_matter
    body = _resolve_cross_links(payload.body_markdown, slug_map)

    article: dict[str, Any] = {
        "published": True,
        "body_markdown": body,
        "ai_disclosure": "ai_assisted",
    }
    if series := fm.extra.get("series"):
        article["series"] = str(series)
    if fm.canonical_url or fm.devto_url:
        article["canonical_url"] = fm.canonical_url or fm.devto_url

    return _devto_request(
        "PATCH",
        f"/articles/{fm.devto_id}",
        api_key,
        json={"article": article},
    )


# ---------------------------------------------------------------------------
# Docs cross-link updater + blog index
# ---------------------------------------------------------------------------

_DOCS_DEVTO_LINK_RE = re.compile(r"\(devto://([a-z0-9\-]+)\)")


def _update_docs_links(repo_root: Path, slug_map: dict[str, str]) -> int:
    """Replace ``devto://slug`` placeholders in all docs/ markdown files with real URLs.

    Args:
        repo_root: Root of the repository.
        slug_map: Mapping of article slug to final DEV.to URL.

    Returns:
        Number of files updated.

    Notes/Architectural Intent:
        Scans every .md file under docs/ (except docs/medium/ staging area) and
        resolves ``devto://slug`` URIs to the live DEV.to URL once available.
        This is the same resolution mechanism used in article cross-links, applied
        to the Zensical documentation pages' "In Depth" callouts.
    """
    docs_dir = repo_root / "docs"
    updated = 0
    for md_file in sorted(docs_dir.rglob("*.md")):
        if "medium" in md_file.parts:
            continue
        text = md_file.read_text(encoding="utf-8")
        new_text = _DOCS_DEVTO_LINK_RE.sub(
            lambda m: f"({slug_map[m.group(1)]})" if m.group(1) in slug_map else m.group(0),
            text,
        )
        if new_text != text:
            md_file.write_text(new_text, encoding="utf-8")
            updated += 1
            console.print(f"  [dim]Updated links in {md_file.relative_to(repo_root)}[/]")
    return updated


# Publication order for the blog index (topological sort from publishing strategy)
_BLOG_PUBLICATION_ORDER: list[tuple[str, str, str, str]] = [
    (
        "10",
        "ai-guardrails-manifesto",
        "What 20 Years of Python Infrastructure Taught Me About Building in the Age of AI Coding Assistants",
        "Manifesto",
    ),
    (
        "5",
        "uv-monorepo",
        "Managing 17 Python Packages Without Losing Your Mind: The `uv` Workspace Monorepo Pattern",
        "Tooling",
    ),
    ("0", "what-is-hexastack", "What Is Hexastack?", "Overview"),
    (
        "6",
        "ai-native-backend-mcp",
        "Your FastAPI Service, Now AI-Native: LLM Agents + MCP",
        "AI / MCP",
    ),
    (
        "15",
        "ast-knowledge-graphs-ai-agents",
        "Why Context Dumps Break AI Coding Agents: Navigating Codebases with AST Knowledge Graphs",
        "AI Tooling",
    ),
    (
        "1",
        "hexagonal-fastapi-cqrs",
        "Stop Writing Spaghetti FastAPI: Hexagonal Architecture + CQRS",
        "Architecture",
    ),
    (
        "12",
        "hexaflow-in-process-workflows",
        "You Probably Don't Need Temporal: Lightweight In-Process Workflows in Python",
        "Workflows",
    ),
    (
        "3",
        "mutation-testing-openssf",
        "90%+ Coverage Isn't Enough: Mutation Testing + OpenSSF Gold",
        "Quality",
    ),
    (
        "2",
        "transactional-outbox-nats",
        "The Dual-Write Trap: Transactional Outbox with NATS JetStream",
        "Events",
    ),
    (
        "7",
        "feature-flags-openfeature",
        "Beyond `if os.getenv`: Feature Flags with OpenFeature",
        "Flags",
    ),
    (
        "8",
        "observability-ports",
        "Logging and Tracing That Don't Fight Your Architecture",
        "Observability",
    ),
    (
        "13",
        "hexaqual-architecture-linting",
        "Stop Reviewing Architecture in PRs: Automating Hexagonal Boundaries and Test Parity",
        "Governance",
    ),
    (
        "11",
        "hipaa-fedramp-compliance",
        "Building for HIPAA and FedRAMP: Architecture as Compliance",
        "Compliance",
    ),
    (
        "9",
        "grpc-fastapi-dual-protocol",
        "gRPC and REST from the Same Service, Without Spaghetti",
        "gRPC",
    ),
    (
        "14",
        "hexaqueue-distributed-batch",
        "Reimagining Slurm for Modern Python: Distributed Batch Scheduling with Heartbeats and DAGs",
        "Distributed Batch",
    ),
    ("4", "nicegui-reactive-devtools", "Reactive DevTools in Python with NiceGUI", "DevTools"),
    (
        "16",
        "four-pillars-hexa-ecosystem",
        "From In-Process DAGs to Distributed Clusters: Designing a Four-Pillar Python Ecosystem",
        "Ecosystem Capstone",
    ),
]


def _regenerate_blog_index(repo_root: Path, medium_dir: Path) -> None:
    """Regenerate docs/blog/index.md from published article front matter.

    Args:
        repo_root: Root of the repository.
        medium_dir: Path to the docs/medium/ staging directory.

    Notes/Architectural Intent:
        Reads devto_url and medium_url from each article's front matter and
        rebuilds the blog index table in topological (publication) order.
        Articles not yet published show "—" in the URL columns.
        This function is called automatically after every ``--publish`` run so
        the Zensical docs site always reflects current publication state.
    """
    blog_index = repo_root / "docs" / "blog" / "index.md"
    if not blog_index.exists():
        return

    # Collect known URLs from front matter
    fm_map: dict[str, FrontMatter] = {}
    for md_file in medium_dir.glob("*.md"):
        if md_file.name == "README.md":
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            p = _parse_article(text, md_file)
            fm_map[md_file.stem] = p.front_matter
        except SystemExit:
            continue

    rows: list[str] = []
    for num, slug, title, topic in _BLOG_PUBLICATION_ORDER:
        fm = fm_map.get(slug)
        devto = f"[Read →]({fm.devto_url})" if fm and fm.devto_url else "—"
        medium = f"[Read →]({fm.medium_url})" if fm and fm.medium_url else "—"
        rows.append(f"| {num} | {title} | {topic} | {devto} | {medium} |")

    table = (
        "| # | Title | Topic | DEV.to | Medium |\n"
        "|---|-------|-------|--------|--------|\n" + "\n".join(rows)
    )

    # Splice the table into the existing index, replacing the old one
    content = blog_index.read_text(encoding="utf-8")
    # Replace between the series header and the > URLs populate line
    new_content = re.sub(
        r"(\| # \| Title \|[^\n]*\n)(?:\|[^\n]*\n)*(\n>)",
        lambda m: f"{table}\n{m.group(2)}",
        content,
    )
    if new_content != content:
        blog_index.write_text(new_content, encoding="utf-8")
        console.print(f"  [dim]Regenerated {blog_index.relative_to(repo_root)}[/]")


# ---------------------------------------------------------------------------
# README URL registry
# ---------------------------------------------------------------------------

_README_REGISTRY_HEADER = "## URL Registry"
_README_REGISTRY_RE = re.compile(r"(## URL Registry\n)(.*?)(\n---|\Z)", re.DOTALL)


def _update_readme_registry(medium_dir: Path) -> None:
    """Rebuild the URL Registry section of docs/medium/README.md from front matter.

    Args:
        medium_dir: Path to the docs/medium/ directory.

    Notes/Architectural Intent:
        Reads all article front matter files and regenerates the registry table
        in-place.  The registry is the canonical human-readable view of
        publishing status; the front matter files are the source of truth.
        If no registry section exists, one is appended to the README.
    """
    readme_path = medium_dir / "README.md"
    if not readme_path.exists():
        return

    rows: list[tuple[str, str, str, str]] = []
    for md_file in sorted(medium_dir.glob("*.md")):
        if md_file.name == "README.md":
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            p = _parse_article(text, md_file)
            fm = p.front_matter
            rows.append(
                (
                    md_file.stem,
                    fm.title[:50] + ("…" if len(fm.title) > 50 else ""),
                    fm.devto_url or "—",
                    fm.medium_url or "—",
                )
            )
        except SystemExit:
            continue

    table_lines = [
        "| Slug | Title | DEV.to | Medium |",
        "|------|-------|--------|--------|",
    ]
    for slug, title, devto, medium in rows:
        table_lines.append(f"| {slug} | {title} | {devto} | {medium} |")

    new_registry = _README_REGISTRY_HEADER + "\n" + "\n".join(table_lines) + "\n"

    readme = readme_path.read_text(encoding="utf-8")
    if _README_REGISTRY_HEADER in readme:
        readme = _README_REGISTRY_RE.sub(
            lambda m: new_registry + (m.group(3) if m.group(3).startswith("\n---") else ""),
            readme,
        )
    else:
        readme = readme.rstrip("\n") + "\n\n---\n\n" + new_registry

    readme_path.write_text(readme, encoding="utf-8")
    console.print(f"[dim]Updated URL registry in {readme_path.name}[/]")


# ---------------------------------------------------------------------------
# Status and syndication helpers for CQRS handler
# ---------------------------------------------------------------------------


def get_article_status_table(medium_dir: Path) -> list[tuple[str, str, str, str, str]]:
    """Return status tuple rows for all articles under docs/medium/.

    Args:
        medium_dir: Path to docs/medium/ staging directory.

    Returns:
        List of (slug, state, devto_id, devto_url, medium_url) tuples.
    """
    rows: list[tuple[str, str, str, str, str]] = []
    for md_file in sorted(medium_dir.glob("*.md")):
        if md_file.name == "README.md":
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            p = _parse_article(text, md_file)
            fm = p.front_matter
        except SystemExit:
            rows.append((md_file.stem, "parse error", "—", "—", "—"))
            continue

        if fm.medium_url:
            state = "syndicated"
        elif fm.devto_url:
            state = "published"
        elif fm.devto_id:
            state = "draft"
        else:
            state = "local"

        rows.append(
            (
                md_file.stem,
                state,
                str(fm.devto_id) if fm.devto_id else "—",
                fm.devto_url or "—",
                fm.medium_url or "—",
            )
        )
    return rows


def record_medium_url(
    slug: str,
    medium_url: str,
    repo_root: Path,
    dry_run: bool = False,
    medium_dir: Path | None = None,
) -> tuple[str, str]:
    """Record Medium syndicated URL in front matter and update registry."""
    medium_dir = medium_dir or (repo_root / "docs" / "medium")
    article_path = _resolve_article_path(slug, medium_dir=medium_dir)
    payload = _parse_article(article_path.read_text("utf-8"), article_path)
    payload.front_matter.medium_url = medium_url
    if not dry_run:
        _write_front_matter(payload)
        _update_readme_registry(medium_dir)
        _regenerate_blog_index(repo_root, medium_dir)
    return payload.slug, f"Recorded Medium URL: {medium_url}"


def upload_all_drafts(
    medium_dir: Path,
    api_key: str,
    dry_run: bool = False,
) -> list[tuple[str, str]]:
    """Upload all unposted articles as drafts to DEV.to."""
    unposted = _all_unposted_articles(medium_dir)
    slug_map = _build_slug_url_map(medium_dir)
    details: list[tuple[str, str]] = []

    for payload in unposted:
        if dry_run:
            details.append((payload.slug, "[dry-run] would upload as draft"))
            continue
        result = _upload_draft(payload, api_key, slug_map)
        devto_id = result.get("id")
        payload.front_matter.devto_id = devto_id
        _write_front_matter(payload)
        details.append((payload.slug, f"Uploaded draft devto_id={devto_id}"))

    if not dry_run and unposted:
        _update_readme_registry(medium_dir)
    return details


def publish_or_upload_single(
    slug_or_path: str,
    publish: bool,
    api_key: str,
    repo_root: Path,
    dry_run: bool = False,
    medium_dir: Path | None = None,
) -> tuple[str, str]:
    """Upload single draft or publish article to DEV.to."""
    medium_dir = medium_dir or (repo_root / "docs" / "medium")
    article_path = _resolve_article_path(slug_or_path, medium_dir=medium_dir)
    payload = _parse_article(article_path.read_text("utf-8"), article_path)
    slug_map = _build_slug_url_map(medium_dir)

    if dry_run:
        action = "PUBLISH" if publish else "DRAFT UPLOAD"
        return payload.slug, f"[dry-run] would execute {action}"

    if publish:
        result = _publish_draft(payload, api_key, slug_map)
        devto_url = str(result.get("url", ""))
        devto_id = result.get("id", payload.front_matter.devto_id)
        payload.front_matter.devto_id = devto_id
        payload.front_matter.devto_url = devto_url
        _write_front_matter(payload)
        slug_map[payload.slug] = devto_url
        _update_readme_registry(medium_dir)
        _update_docs_links(repo_root, slug_map)
        _regenerate_blog_index(repo_root, medium_dir)
        return payload.slug, f"Published -> {devto_url}"

    result = _upload_draft(payload, api_key, slug_map)
    devto_id = result.get("id")
    payload.front_matter.devto_id = devto_id
    _write_front_matter(payload)
    _update_readme_registry(medium_dir)
    return payload.slug, f"Uploaded draft devto_id={devto_id}"


def sync_all_links(
    medium_dir: Path,
    api_key: str,
    repo_root: Path,
    dry_run: bool = False,
) -> list[tuple[str, str]]:
    """Re-resolve cross-links and update DEV.to for all published articles."""
    slug_map = _build_slug_url_map(medium_dir)
    results: list[tuple[str, str]] = []

    for md_file in sorted(medium_dir.glob("*.md")):
        if md_file.name == "README.md":
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            payload = _parse_article(text, md_file)
            fm = payload.front_matter
            if fm.devto_id is None or not fm.devto_url:
                continue

            resolved_body = _resolve_cross_links(payload.body_markdown, slug_map)
            if not dry_run:
                article: dict[str, Any] = {
                    "published": True,
                    "body_markdown": resolved_body,
                    "ai_disclosure": "ai_assisted",
                }
                if series := fm.extra.get("series"):
                    article["series"] = str(series)
                if fm.canonical_url or fm.devto_url:
                    article["canonical_url"] = fm.canonical_url or fm.devto_url

                _devto_request(
                    "PATCH",
                    f"/articles/{fm.devto_id}",
                    api_key,
                    json={"article": article},
                )
                results.append((payload.slug, f"Synced links -> {fm.devto_url}"))
            else:
                results.append((payload.slug, f"[dry-run] would sync links -> {fm.devto_url}"))
        except Exception as exc:
            results.append((md_file.stem, f"Error: {exc}"))

    if not dry_run:
        _update_docs_links(repo_root, slug_map)
        _regenerate_blog_index(repo_root, medium_dir)
        _update_readme_registry(medium_dir)

    return results


class DevToPublisherAdapter(ArticlePublisherPort):
    """DEV.to REST API publishing adapter implementing ArticlePublisherPort."""

    def __init__(self, api_key: str = "", client: httpx.Client | None = None) -> None:
        self.api_key = api_key
        self._client = client

    def list_articles(self) -> list[dict[str, Any]]:
        """List articles published or drafted by authenticated user."""
        headers = {
            "api-key": self.api_key,
            "Accept": "application/vnd.forem.api-v1+json",
        }
        client = self._client or httpx.Client(timeout=30.0)
        try:
            resp = client.get(f"{DEVTO_API_BASE}/articles/me", headers=headers)
            if resp.status_code == 200:
                return resp.json()
            return []
        finally:
            if self._client is None:
                client.close()

    def get_article(self, article_id: int) -> dict[str, Any]:
        """Fetch remote article representation by ID."""
        headers = {
            "api-key": self.api_key,
            "Accept": "application/vnd.forem.api-v1+json",
        }
        client = self._client or httpx.Client(timeout=30.0)
        try:
            resp = client.get(f"{DEVTO_API_BASE}/articles/{article_id}", headers=headers)
            if resp.status_code == 200:
                return resp.json()
            return {}
        finally:
            if self._client is None:
                client.close()

    def create_article(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create new article on DEV.to."""
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/vnd.forem.api-v1+json",
        }
        client = self._client or httpx.Client(timeout=30.0)
        try:
            resp = client.post(
                f"{DEVTO_API_BASE}/articles", headers=headers, json={"article": payload}
            )
            if resp.status_code in (200, 201):
                return resp.json()
            return {}
        finally:
            if self._client is None:
                client.close()

    def update_article(self, article_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Update existing article on DEV.to."""
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/vnd.forem.api-v1+json",
        }
        client = self._client or httpx.Client(timeout=30.0)
        try:
            resp = client.patch(
                f"{DEVTO_API_BASE}/articles/{article_id}",
                headers=headers,
                json={"article": payload},
            )
            if resp.status_code in (200, 201):
                return resp.json()
            return {}
        finally:
            if self._client is None:
                client.close()


publish_all = upload_all_drafts
check_all = get_article_status_table

__all__ = [
    "_all_unposted_articles",
    "_BLOG_PUBLICATION_ORDER",
    "_build_slug_url_map",
    "_devto_request",
    "_devto_tags",
    "_get_medium_dir",
    "_parse_article",
    "_publish_draft",
    "_regenerate_blog_index",
    "_resolve_article_path",
    "_resolve_cross_links",
    "_update_docs_links",
    "_update_readme_registry",
    "_upload_draft",
    "_write_front_matter",
    "ArticlePayload",
    "check_all",
    "DevToPublisherAdapter",
    "FrontMatter",
    "get_article_status_table",
    "publish_all",
    "publish_or_upload_single",
    "record_medium_url",
    "sync_all_links",
    "upload_all_drafts",
]
