"""Tests for the DiTTo MCP server documentation resources."""

import json

import pytest

from ditto.mcp.docs import get_docs_dir, list_doc_pages, read_doc_page


# ---------------------------------------------------------------------------
# docs.py unit tests
# ---------------------------------------------------------------------------


class TestDocsDiscovery:
    def test_docs_dir_exists(self):
        docs_dir = get_docs_dir()
        assert docs_dir.exists(), f"docs dir not found at {docs_dir}"
        assert docs_dir.is_dir()

    def test_list_doc_pages_returns_pages(self):
        pages = list_doc_pages()
        assert isinstance(pages, list)
        assert len(pages) > 0
        # Each page should have slug, title, uri
        for page in pages:
            assert "slug" in page
            assert "title" in page
            assert "uri" in page
            assert page["uri"].startswith("ditto://docs/")

    def test_list_doc_pages_includes_expected(self):
        pages = list_doc_pages()
        slugs = [p["slug"] for p in pages]
        assert "index" in slugs
        assert "usage" in slugs
        assert "install" in slugs

    def test_read_doc_page_index(self):
        content = read_doc_page("index")
        assert isinstance(content, str)
        assert len(content) > 0
        assert "DiTTo" in content

    def test_read_doc_page_usage(self):
        content = read_doc_page("usage")
        assert "Usage" in content or "usage" in content.lower()

    def test_read_doc_page_install(self):
        content = read_doc_page("install")
        assert "install" in content.lower() or "pip" in content.lower()

    def test_read_doc_page_api_opendss_reader(self):
        content = read_doc_page("api/opendss_reader")
        assert "OpenDSS" in content

    def test_read_doc_page_api_cim_reader(self):
        content = read_doc_page("api/cim_reader")
        assert "CIM" in content

    def test_read_doc_page_api_opendss_writer(self):
        content = read_doc_page("api/opendss_writer")
        assert "Writer" in content or "writer" in content.lower()

    def test_read_doc_page_unknown_slug(self):
        with pytest.raises(FileNotFoundError, match="Unknown documentation page"):
            read_doc_page("nonexistent_page")

    def test_read_doc_page_reference(self):
        content = read_doc_page("reference")
        assert "API" in content or "Reference" in content


# ---------------------------------------------------------------------------
# Server resource function tests
# ---------------------------------------------------------------------------


class TestServerResources:
    """Test the resource functions registered on the MCP server."""

    def test_docs_index_resource(self):
        from ditto.mcp.server import docs_index

        result = docs_index()
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    def test_docs_page_resource(self):
        from ditto.mcp.server import docs_page

        content = docs_page("usage")
        assert isinstance(content, str)
        assert len(content) > 0
