# MCP Server

DiTTo provides a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
server that exposes its full reader/writer pipeline, model inspection, and
documentation to LLM applications such as Claude Desktop, VS Code Copilot, and
Claude Code.

## Installation

The MCP server is included with DiTTo. The `mcp` dependency is installed
automatically with the core package:

```bash
pip install nrel-ditto
```

Or install only the MCP extra:

```bash
pip install nrel-ditto[mcp]
```

## Running the Server

### Direct execution (stdio transport)

```bash
ditto_mcp
```

Or as a Python module:

```bash
python -m ditto.mcp.server
```

### Development mode with MCP Inspector

```bash
uv run mcp dev src/ditto/mcp/server.py --with-editable .
```

### Claude Desktop integration

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "ditto": {
      "command": "ditto_mcp"
    }
  }
}
```

### VS Code / Claude Code integration

```bash
claude mcp add ditto -- ditto_mcp
```

## Available Tools

### Discovery

| Tool | Description |
|------|-------------|
| `list_readers` | List available reader formats (e.g. opendss, cim_iec_61968_13) |
| `list_writers` | List available writer formats (e.g. opendss) |

### Loading Models

| Tool | Description |
|------|-------------|
| `read_opendss_model` | Load an OpenDSS model from a `.dss` master file |
| `read_cim_model` | Load a CIM IEC 61968-13 XML model |
| `load_gdm_json` | Load a previously-exported GDM JSON file |

### Inspection

| Tool | Description |
|------|-------------|
| `list_loaded_systems` | Show names of all systems currently in memory |
| `get_system_summary` | Component counts and type breakdown for a loaded system |
| `get_components` | List components of a given type (buses, loads, lines, etc.) |
| `get_component_detail` | Full Pydantic model dump of a single component |

### Writing / Export

| Tool | Description |
|------|-------------|
| `write_opendss` | Write a loaded system to OpenDSS `.dss` files |
| `export_gdm_json` | Serialize a loaded system to GDM JSON |
| `convert_model` | Full read → write conversion between formats |

## Available Resources

Documentation pages are exposed as MCP resources under the `ditto://docs/` URI
scheme:

| Resource URI | Content |
|-------------|---------|
| `ditto://docs` | Index of all available documentation pages |
| `ditto://docs/index` | Project overview and architecture |
| `ditto://docs/install` | Installation instructions |
| `ditto://docs/usage` | Usage guide with code examples |
| `ditto://docs/reference` | API reference overview |
| `ditto://docs/api/opendss_reader` | OpenDSS reader API docs |
| `ditto://docs/api/cim_reader` | CIM reader API docs |
| `ditto://docs/api/opendss_writer` | OpenDSS writer API docs |

## Available Prompts

| Prompt | Description |
|--------|-------------|
| `convert_guide` | Step-by-step interactive guide for format conversion |
| `inspect_model` | Interactive workflow for exploring a loaded model |

## Example Workflow

A typical interaction with the DiTTo MCP server:

1. **List formats**: Ask the LLM to call `list_readers` and `list_writers`
2. **Load a model**: Call `read_opendss_model` with a path to `Master.dss`
3. **Inspect**: Use `get_system_summary` to see what's in the model
4. **Browse components**: Use `get_components` to list buses, loads, etc.
5. **Export**: Use `write_opendss` or `export_gdm_json` to save the model
6. **Read docs**: Access `ditto://docs/usage` for detailed usage guides

## Architecture

```{mermaid}
flowchart TD
    A["LLM Client\n(Claude, VS Code, etc.)"] <-->|"MCP Protocol\n(stdio)"| B["DiTTo MCP Server"]
    B --> C["Tools"]
    B --> D["Resources"]
    B --> E["Prompts"]
    C --> F["Readers\n(OpenDSS, CIM)"]
    C --> G["Writers\n(OpenDSS)"]
    C --> H["GDM System\nInspection"]
    D --> I["Documentation\n(Markdown)"]
```
