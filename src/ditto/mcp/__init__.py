"""DiTTo MCP Server package.

Provides a Model Context Protocol (MCP) interface for DiTTo, exposing
readers, writers, model inspection, and documentation through the
standardized MCP tool/resource protocol.

Usage::

    from ditto.mcp.server import mcp, main

    # Run stdio server
    main()
"""

from ditto.mcp.server import main, mcp

__all__ = ["main", "mcp"]
