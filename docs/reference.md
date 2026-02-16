# API Reference

This section documents the public Python API for DiTTo's readers and writers.
Each reader/writer page includes auto-generated documentation from the source
code docstrings.

## Readers

Readers parse source distribution-system files into a GDM
`DistributionSystem`. Each reader sub-package exposes a `Reader` class that
inherits from {py:class}`ditto.readers.reader.AbstractReader`.

```{toctree}
:caption: Readers
:hidden: true

api/opendss_reader
api/cim_reader
```

## Writers

Writers export a GDM `DistributionSystem` to a target format on disk.

```{toctree}
:caption: Writers
:hidden: true

api/opendss_writer
```

## MCP Server

DiTTo provides a Model Context Protocol server for LLM integration.

```{toctree}
:caption: MCP
:hidden: true

api/mcp_server
```