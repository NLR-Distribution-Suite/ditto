"""DiTTo MCP Server — low-level MCP 2.0 interface.

Exposes DiTTo's reader/writer pipeline, model inspection, and documentation
as MCP tools, resources, and prompts. Uses a module-level ``AppState``
singleton to hold loaded ``DistributionSystem`` instances across calls.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import pkgutil
from pathlib import Path
from typing import Any, Callable

from loguru import logger
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    GetPromptRequestParams,
    GetPromptResult,
    ListPromptsRequest,
    ListPromptsResult,
    ListResourceTemplatesRequest,
    ListResourceTemplatesResult,
    ListResourcesRequest,
    ListResourcesResult,
    ListToolsRequest,
    ListToolsResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    ReadResourceRequestParams,
    ReadResourceResult,
    Resource,
    ResourceTemplate,
    TextContent,
    TextResourceContents,
    Tool,
)

from ditto.mcp.docs import list_doc_pages, read_doc_page
from ditto.mcp.state import AppState

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

mcp = Server("DiTTo")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _list_subpackages(package_name: str) -> list[str]:
    """Return sub-package names under *package_name*."""
    try:
        pkg = importlib.import_module(package_name)
        return [name for _, name, ispkg in pkgutil.iter_modules(pkg.__path__) if ispkg]
    except Exception:
        logger.warning(f"Failed to import package '{package_name}' for listing subpackages")
        return []


def _import_reader(reader_name: str):
    """Dynamically import and return a Reader class."""
    module = importlib.import_module(f"ditto.readers.{reader_name}.reader")
    return getattr(module, "Reader")


def _import_writer(writer_name: str):
    """Dynamically import and return a Writer class."""
    module = importlib.import_module(f"ditto.writers.{writer_name}.write")
    return getattr(module, "Writer")


def _resolve_component_type(type_name: str):
    """Resolve a GDM component class by its short name.

    Searches ``gdm.distribution.components``, ``gdm.distribution.equipment``,
    and ``gdm.distribution.controllers`` for a class matching *type_name*.
    """
    search_modules = [
        "gdm.distribution.components",
        "gdm.distribution.equipment",
        "gdm.distribution.controllers",
    ]
    for mod_path in search_modules:
        try:
            mod = importlib.import_module(mod_path)
            if hasattr(mod, type_name):
                return getattr(mod, type_name)
        except ImportError:
            continue
    raise ValueError(
        f"Unknown component type '{type_name}'. "
        "Check gdm.distribution.components / equipment / controllers."
    )


def _safe_json(obj: Any) -> Any:
    """Best-effort JSON-safe conversion of a pydantic/infrasys model."""
    try:
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        return str(obj)
    except Exception:
        return str(obj)


# ---------------------------------------------------------------------------
# Tools — Discovery
# ---------------------------------------------------------------------------


def list_readers() -> list[str]:
    """List available reader formats (e.g. opendss, cim_iec_61968_13)."""
    return _list_subpackages("ditto.readers")


def list_writers() -> list[str]:
    """List available writer formats (e.g. opendss)."""
    return _list_subpackages("ditto.writers")


# ---------------------------------------------------------------------------
# Tools — Loading models
# ---------------------------------------------------------------------------


def read_opendss_model(
    master_file: str,
    name: str = "default",
    crs: str | None = None,
) -> dict[str, Any]:
    """Load an OpenDSS model from a master .dss file into memory.

    Parameters
    ----------
    master_file:
        Absolute or relative path to the OpenDSS master file.
    name:
        Key to store the loaded system under.  Use ``list_loaded_systems``
        to see all loaded names.
    crs:
        Optional coordinate reference system identifier.

    Returns
    -------
    dict
        Summary of the loaded system (component counts, etc.).
    """
    from ditto.readers.opendss.reader import Reader

    path = Path(master_file).resolve()
    reader = Reader(path, crs=crs)
    system = reader.get_system()

    _SYNC_STATE.store(name, system)
    return _SYNC_STATE.summary(name)


def read_cim_model(
    cim_file: str,
    name: str = "default",
) -> dict[str, Any]:
    """Load a CIM IEC 61968-13 XML model into memory.

    Parameters
    ----------
    cim_file:
        Path to the CIM XML file.
    name:
        Key to store the loaded system under.
    """
    from ditto.readers.cim_iec_61968_13.reader import Reader

    path = Path(cim_file).resolve()
    reader = Reader(path)
    reader.read()
    system = reader.get_system()
    _SYNC_STATE.store(name, system)
    return _SYNC_STATE.summary(name)


def load_gdm_json(
    json_file: str,
    name: str = "default",
) -> dict[str, Any]:
    """Load a previously-exported GDM DistributionSystem from JSON.

    Parameters
    ----------
    json_file:
        Path to the GDM JSON file.
    name:
        Key to store the loaded system under.
    """
    from gdm.distribution import DistributionSystem

    path = Path(json_file).resolve()
    system = DistributionSystem.from_json(path)
    _SYNC_STATE.store(name, system)
    return _SYNC_STATE.summary(name)


# ---------------------------------------------------------------------------
# Tools — Inspection
# ---------------------------------------------------------------------------


def list_loaded_systems() -> list[str]:
    """Return the names of all distribution systems currently loaded in memory."""
    return list(_SYNC_STATE.systems.keys())


def get_system_summary(name: str = "default") -> dict[str, Any]:
    """Return a summary of a loaded distribution system (component counts, etc.).

    Parameters
    ----------
    name:
        The key under which the system was loaded.
    """
    return _SYNC_STATE.summary(name)


def get_components(
    component_type: str,
    name: str = "default",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List components of a given type from a loaded system.

    Parameters
    ----------
    component_type:
        GDM class name, e.g. ``"DistributionBus"``, ``"DistributionLoad"``,
        ``"MatrixImpedanceBranch"``, ``"DistributionTransformer"``.
    name:
        System key.
    limit:
        Maximum number of components to return (default 50).

    Returns
    -------
    list[dict]
        Each dict contains ``name`` and key attributes for the component.
    """
    system = _SYNC_STATE.get(name)
    cls = _resolve_component_type(component_type)
    results = []
    for i, comp in enumerate(system.get_components(cls)):
        if i >= limit:
            break
        entry: dict[str, Any] = {"name": comp.name}
        for attr in (
            "rated_voltage",
            "phases",
            "bus",
            "from_bus",
            "to_bus",
            "equipment",
            "rated_power",
            "nominal_voltage",
        ):
            if hasattr(comp, attr):
                val = getattr(comp, attr)
                entry[attr] = str(val)
        results.append(entry)
    return results


def get_component_detail(
    component_type: str,
    component_name: str,
    name: str = "default",
) -> dict[str, Any]:
    """Return the full detail of a single component (all fields).

    Parameters
    ----------
    component_type:
        GDM class name, e.g. ``"DistributionBus"``.
    component_name:
        The ``name`` attribute of the component to retrieve.
    name:
        System key.
    """
    system = _SYNC_STATE.get(name)
    cls = _resolve_component_type(component_type)
    comp = system.get_component(cls, component_name)
    return _safe_json(comp)


# ---------------------------------------------------------------------------
# Tools — Writing / Export
# ---------------------------------------------------------------------------


def write_opendss(
    name: str = "default",
    output_path: str = "./opendss_output",
    separate_substations: bool = True,
    separate_feeders: bool = True,
) -> dict[str, Any]:
    """Write a loaded system to OpenDSS format.

    Parameters
    ----------
    name:
        System key of the model to export.
    output_path:
        Directory where .dss files will be written.
    separate_substations:
        Create separate directories per substation.
    separate_feeders:
        Create separate directories per feeder.

    Returns
    -------
    dict
        ``{success, output_path, message}`` — ``output_path`` is the absolute
        output directory (so orchestrators can track/attach it as an artifact).
    """
    from ditto.writers.opendss.write import Writer

    system = _SYNC_STATE.get(name)
    out = Path(output_path).resolve()
    out.mkdir(parents=True, exist_ok=True)
    writer = Writer(system)
    writer.write(
        output_path=out,
        separate_substations=separate_substations,
        separate_feeders=separate_feeders,
    )
    return {
        "success": True,
        "output_path": str(out),
        "message": f"OpenDSS model written to {out}",
    }


def export_gdm_json(
    name: str = "default",
    output_path: str = "./model.json",
) -> dict[str, Any]:
    """Serialize a loaded system to GDM JSON format.

    Parameters
    ----------
    name:
        System key.
    output_path:
        Destination file path for the JSON export.

    Returns
    -------
    dict
        ``{success, output_path, message}`` — ``output_path`` is the absolute
        JSON path (so orchestrators can track/attach it as an artifact).
    """
    system = _SYNC_STATE.get(name)
    out = Path(output_path).resolve()
    system.to_json(out, overwrite=True)
    return {
        "success": True,
        "output_path": str(out),
        "message": f"GDM JSON exported to {out}",
    }


def convert_model(
    reader_type: str,
    writer_type: str,
    input_path: str,
    output_path: str = "./converted_output",
    save_gdm: str | None = None,
) -> dict[str, Any]:
    """Run a full format conversion (reader → GDM → writer).

    This is the MCP equivalent of the ``ditto_cli convert`` command.

    Parameters
    ----------
    reader_type:
        Reader sub-package name (e.g. ``"opendss"``, ``"cim_iec_61968_13"``).
    writer_type:
        Writer sub-package name (e.g. ``"opendss"``).
    input_path:
        Path to the source model file / directory.
    output_path:
        Directory for writer output files.
    save_gdm:
        Optional path to save the intermediate GDM JSON.

    Returns
    -------
    dict
        ``{success, output_path, gdm_path, message}`` — ``output_path`` is the
        absolute writer output (so orchestrators can track/attach it as an
        artifact); ``gdm_path`` is set when ``save_gdm`` was requested.
    """
    available_readers = _list_subpackages("ditto.readers")
    available_writers = _list_subpackages("ditto.writers")

    if reader_type not in available_readers:
        raise ValueError(f"Unknown reader '{reader_type}'. Available: {available_readers}")
    if writer_type not in available_writers:
        raise ValueError(f"Unknown writer '{writer_type}'. Available: {available_writers}")

    ReaderClass = _import_reader(reader_type)
    reader_instance = ReaderClass(Path(input_path).resolve())

    if hasattr(reader_instance, "read") and callable(reader_instance.read):
        reader_instance.read()

    system = reader_instance.get_system()

    gdm_path: Path | None = None
    if save_gdm:
        gdm_path = Path(save_gdm).resolve()
        system.to_json(gdm_path, overwrite=True)

    WriterClass = _import_writer(writer_type)
    writer_instance = WriterClass(system)
    out = Path(output_path).resolve()
    out.mkdir(parents=True, exist_ok=True)
    writer_instance.write(out)

    msg = f"Conversion complete: {reader_type} → {writer_type}.  Output: {out}"
    if gdm_path is not None:
        msg += f"  GDM JSON saved to {gdm_path}"
    return {
        "success": True,
        "output_path": str(out),
        "gdm_path": str(gdm_path) if gdm_path is not None else None,
        "message": msg,
    }


def _get_tools() -> list[Tool]:
    return [
        Tool(
            name="list_readers",
            description="List available reader formats (e.g. opendss, cim_iec_61968_13).",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_writers",
            description="List available writer formats (e.g. opendss).",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="read_opendss_model",
            description="Load an OpenDSS model from a master .dss file into memory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "master_file": {
                        "type": "string",
                        "description": "Absolute or relative path to the OpenDSS master file.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Key to store the loaded system under. Use list_loaded_systems to see all loaded names.",
                        "default": "default",
                    },
                    "crs": {
                        "type": ["string", "null"],
                        "description": "Optional coordinate reference system identifier.",
                        "default": None,
                    },
                },
                "required": ["master_file"],
            },
        ),
        Tool(
            name="read_cim_model",
            description="Load a CIM IEC 61968-13 XML model into memory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cim_file": {
                        "type": "string",
                        "description": "Path to the CIM XML file.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Key to store the loaded system under.",
                        "default": "default",
                    },
                },
                "required": ["cim_file"],
            },
        ),
        Tool(
            name="load_gdm_json",
            description="Load a previously-exported GDM DistributionSystem from JSON.",
            inputSchema={
                "type": "object",
                "properties": {
                    "json_file": {"type": "string", "description": "Path to the GDM JSON file."},
                    "name": {
                        "type": "string",
                        "description": "Key to store the loaded system under.",
                        "default": "default",
                    },
                },
                "required": ["json_file"],
            },
        ),
        Tool(
            name="list_loaded_systems",
            description="Return the names of all distribution systems currently loaded in memory.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_system_summary",
            description="Return a summary of a loaded distribution system (component counts, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The key under which the system was loaded.",
                        "default": "default",
                    }
                },
            },
        ),
        Tool(
            name="get_components",
            description="List components of a given type from a loaded system.",
            inputSchema={
                "type": "object",
                "properties": {
                    "component_type": {
                        "type": "string",
                        "description": "GDM class name, e.g. DistributionBus, DistributionLoad, MatrixImpedanceBranch, DistributionTransformer.",
                    },
                    "name": {
                        "type": "string",
                        "description": "System key.",
                        "default": "default",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of components to return (default 50).",
                        "default": 50,
                    },
                },
                "required": ["component_type"],
            },
        ),
        Tool(
            name="get_component_detail",
            description="Return the full detail of a single component (all fields).",
            inputSchema={
                "type": "object",
                "properties": {
                    "component_type": {
                        "type": "string",
                        "description": "GDM class name, e.g. DistributionBus.",
                    },
                    "component_name": {
                        "type": "string",
                        "description": "The name attribute of the component to retrieve.",
                    },
                    "name": {
                        "type": "string",
                        "description": "System key.",
                        "default": "default",
                    },
                },
                "required": ["component_type", "component_name"],
            },
        ),
        Tool(
            name="write_opendss",
            description="Write a loaded system to OpenDSS format.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "System key of the model to export.",
                        "default": "default",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Directory where .dss files will be written.",
                        "default": "./opendss_output",
                    },
                    "separate_substations": {
                        "type": "boolean",
                        "description": "Create separate directories per substation.",
                        "default": True,
                    },
                    "separate_feeders": {
                        "type": "boolean",
                        "description": "Create separate directories per feeder.",
                        "default": True,
                    },
                },
            },
        ),
        Tool(
            name="export_gdm_json",
            description="Serialize a loaded system to GDM JSON format.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "System key.",
                        "default": "default",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Destination file path for the JSON export.",
                        "default": "./model.json",
                    },
                },
            },
        ),
        Tool(
            name="convert_model",
            description="Run a full format conversion (reader → GDM → writer).",
            inputSchema={
                "type": "object",
                "properties": {
                    "reader_type": {
                        "type": "string",
                        "description": "Reader sub-package name (e.g. opendss, cim_iec_61968_13).",
                    },
                    "writer_type": {
                        "type": "string",
                        "description": "Writer sub-package name (e.g. opendss).",
                    },
                    "input_path": {
                        "type": "string",
                        "description": "Path to the source model file / directory.",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Directory for writer output files.",
                        "default": "./converted_output",
                    },
                    "save_gdm": {
                        "type": ["string", "null"],
                        "description": "Optional path to save the intermediate GDM JSON.",
                        "default": None,
                    },
                },
                "required": ["reader_type", "writer_type", "input_path"],
            },
        ),
    ]


def docs_index() -> str:
    """List all available DiTTo documentation pages."""
    pages = list_doc_pages()
    return json.dumps(pages, indent=2)


def docs_page(page: str) -> str:
    """Read a specific DiTTo documentation page by slug.

    Available slugs: index, install, usage, reference,
    api/opendss_reader, api/cim_reader, api/opendss_writer, api/cim_writer.
    """
    return read_doc_page(page)


def convert_guide() -> str:
    """Interactive conversion workflow prompt."""
    return (
        "I'll help you convert a distribution system model from one format "
        "to another using DiTTo.\n\n"
        "Step 1: Let's see what formats are available.\n"
        "  → Use the `list_readers` tool to see available source formats.\n"
        "  → Use the `list_writers` tool to see available target formats.\n\n"
        "Step 2: Tell me:\n"
        "  - **Source format** (reader name)\n"
        "  - **Input file path** (e.g. Master.dss or model.xml)\n"
        "  - **Target format** (writer name)\n"
        "  - **Output directory** (where to write the converted model)\n\n"
        "Step 3: I'll run the `convert_model` tool and report the results.\n\n"
        "Would you also like to save the intermediate GDM JSON representation? "
        "This can be useful for inspection or future re-use."
    )


def inspect_model(name: str = "default") -> str:
    """Interactive model inspection prompt."""
    return (
        f"Let's explore the distribution system model '{name}'.\n\n"
        "I can help you:\n"
        "  1. **Get a summary** — component counts, types present\n"
        "  2. **List components** of a specific type (buses, loads, lines, etc.)\n"
        "  3. **View full detail** of any individual component\n"
        "  4. **Export** the model to OpenDSS or GDM JSON\n\n"
        "What would you like to explore first?  If the model isn't loaded yet, "
        "provide the path and format and I'll load it for you."
    )


def _tool_handler(fn: Callable[..., Any], arguments: dict[str, Any] | None) -> Any:
    return fn(**(arguments or {}))


_TOOL_HANDLERS: dict[str, Callable[..., Any]] = {
    "list_readers": list_readers,
    "list_writers": list_writers,
    "read_opendss_model": read_opendss_model,
    "read_cim_model": read_cim_model,
    "load_gdm_json": load_gdm_json,
    "list_loaded_systems": list_loaded_systems,
    "get_system_summary": get_system_summary,
    "get_components": get_components,
    "get_component_detail": get_component_detail,
    "write_opendss": write_opendss,
    "export_gdm_json": export_gdm_json,
    "convert_model": convert_model,
}


async def _handle_list_tools(ctx: Any, params: ListToolsRequest) -> ListToolsResult:
    del ctx, params
    return ListToolsResult(tools=_get_tools())


async def _handle_call_tool(ctx: Any, params: CallToolRequestParams) -> CallToolResult:
    del ctx
    name = params.name
    arguments = params.arguments or {}
    try:
        fn = _TOOL_HANDLERS.get(name)
        if fn is None:
            raise ValueError(f"Unknown tool: {name}")
        result = _tool_handler(fn, arguments)
        text = json.dumps(result, indent=2, default=str)
    except Exception as e:
        text = json.dumps({"error": str(e)})
    return CallToolResult(content=[TextContent(type="text", text=text)])


async def _handle_list_resources(ctx: Any, params: ListResourcesRequest) -> ListResourcesResult:
    del ctx, params
    return ListResourcesResult(
        resources=[
            Resource(
                name="DiTTo Documentation Index",
                uri="ditto://docs",
                description="List all available DiTTo documentation pages.",
                mimeType="application/json",
            )
        ]
    )


async def _handle_list_resource_templates(
    ctx: Any, params: ListResourceTemplatesRequest
) -> ListResourceTemplatesResult:
    del ctx, params
    return ListResourceTemplatesResult(
        resourceTemplates=[
            ResourceTemplate(
                name="DiTTo Documentation Page",
                uriTemplate="ditto://docs/{page}",
                description="Read a specific DiTTo documentation page by slug.",
                mimeType="text/markdown",
            )
        ]
    )


async def _handle_read_resource(ctx: Any, params: ReadResourceRequestParams) -> ReadResourceResult:
    del ctx
    uri = str(params.uri)
    if uri == "ditto://docs":
        text = docs_index()
        mime_type = "application/json"
    elif uri.startswith("ditto://docs/"):
        page = uri[len("ditto://docs/") :]
        text = docs_page(page)
        mime_type = "text/markdown"
    else:
        text = json.dumps({"error": f"Unknown resource URI: {uri}"})
        mime_type = "application/json"

    return ReadResourceResult(
        contents=[TextResourceContents(uri=uri, mimeType=mime_type, text=text)]
    )


async def _handle_list_prompts(ctx: Any, params: ListPromptsRequest) -> ListPromptsResult:
    del ctx, params
    return ListPromptsResult(
        prompts=[
            Prompt(
                name="convert_guide",
                description="Step-by-step guide for converting a distribution model between formats",
            ),
            Prompt(
                name="inspect_model",
                description="Explore a loaded distribution system model interactively",
                arguments=[
                    PromptArgument(
                        name="name",
                        description="System key to inspect (defaults to 'default').",
                        required=False,
                    )
                ],
            ),
        ]
    )


async def _handle_get_prompt(ctx: Any, params: GetPromptRequestParams) -> GetPromptResult:
    del ctx
    if params.name == "convert_guide":
        text = convert_guide()
    elif params.name == "inspect_model":
        name = "default"
        if params.arguments:
            name = params.arguments.get("name", "default")
        text = inspect_model(name=name)
    else:
        text = json.dumps({"error": f"Unknown prompt: {params.name}"})

    return GetPromptResult(
        messages=[PromptMessage(role="user", content=TextContent(type="text", text=text))]
    )


mcp.add_request_handler("tools/list", ListToolsRequest, _handle_list_tools)
mcp.add_request_handler("tools/call", CallToolRequestParams, _handle_call_tool)
mcp.add_request_handler("resources/list", ListResourcesRequest, _handle_list_resources)
mcp.add_request_handler(
    "resources/templates/list", ListResourceTemplatesRequest, _handle_list_resource_templates
)
mcp.add_request_handler("resources/read", ReadResourceRequestParams, _handle_read_resource)
mcp.add_request_handler("prompts/list", ListPromptsRequest, _handle_list_prompts)
mcp.add_request_handler("prompts/get", GetPromptRequestParams, _handle_get_prompt)


# ---------------------------------------------------------------------------
# Module-level sync state
# ---------------------------------------------------------------------------

_SYNC_STATE = AppState()


async def serve() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await mcp.run(read_stream, write_stream, mcp.create_initialization_options())


def main() -> None:
    """Run the DiTTo MCP server (stdio transport)."""
    asyncio.run(serve())


if __name__ == "__main__":
    main()
