"""Documentation discovery and serving for the DiTTo MCP server.

Locates the ``docs/`` directory relative to the project root and exposes
helper functions that list available documentation pages and read their
raw Markdown content.  These are consumed by MCP resource definitions in
:mod:`ditto.mcp.server`.
"""

from __future__ import annotations

from pathlib import Path

# Resolve the project root: src/ditto/mcp/docs.py -> src/ditto/mcp -> src/ditto -> src -> project
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DOCS_DIR = _PROJECT_ROOT / "docs"

# Map of page slug -> relative path within docs/
_DOC_PAGES: dict[str, str] = {
    "index": "index.md",
    "install": "install.md",
    "usage": "usage.md",
    "reference": "reference.md",
    "api/opendss_reader": "api/opendss_reader.md",
    "api/cim_reader": "api/cim_reader.md",
    "api/opendss_writer": "api/opendss_writer.md",
}


def get_docs_dir() -> Path:
    """Return the resolved path to the ``docs/`` directory."""
    return _DOCS_DIR


def list_doc_pages() -> list[dict[str, str]]:
    """Return a list of available documentation pages.

    Each entry is a dict with ``slug`` and ``title`` keys.
    """
    pages = []
    for slug, rel_path in _DOC_PAGES.items():
        doc_file = _DOCS_DIR / rel_path
        if doc_file.exists():
            # Extract first heading as title, or fall back to slug
            title = slug
            for line in doc_file.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("# "):
                    title = stripped.lstrip("# ").strip()
                    break
            pages.append(
                {
                    "slug": slug,
                    "title": title,
                    "uri": f"ditto://docs/{slug}",
                }
            )
    return pages


def read_doc_page(slug: str) -> str:
    """Read and return the raw Markdown content for a documentation page.

    Parameters
    ----------
    slug:
        Page identifier, e.g. ``"usage"`` or ``"api/opendss_reader"``.

    Raises
    ------
    FileNotFoundError
        If the slug is unknown or the file does not exist on disk.
    """
    if slug not in _DOC_PAGES:
        available = ", ".join(sorted(_DOC_PAGES.keys()))
        raise FileNotFoundError(f"Unknown documentation page '{slug}'. Available: {available}")
    doc_file = _DOCS_DIR / _DOC_PAGES[slug]
    if not doc_file.exists():
        raise FileNotFoundError(f"Documentation file not found: {doc_file}")
    return doc_file.read_text(encoding="utf-8")
