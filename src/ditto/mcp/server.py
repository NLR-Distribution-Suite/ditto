"""DiTTo MCP Server — Model Context Protocol interface for the Distribution Transformation Tool.

Exposes DiTTo's reader/writer pipeline, model inspection, and documentation
as MCP tools, resources, and prompts.  Uses a module-level ``AppState``
singleton to hold loaded ``DistributionSystem`` instances across calls.

Run directly::

    python -m ditto.mcp.server        # stdio transport (default)
    ditto_mcp                          # via entry-point

Or in development with the MCP inspector::

    uv run mcp dev src/ditto/mcp/server.py --with-editable .
"""

from __future__ import annotations

import importlib
import json
import pkgutil
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from loguru import logger

from ditto.mcp.docs import list_doc_pages, read_doc_page
from ditto.mcp.state import AppState

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "DiTTo",
    instructions=(
        "DiTTo (Distribution Transformation Tool) converts electrical "
        "distribution system models between formats such as OpenDSS and "
        "CIM IEC 61968-13 via an intermediate Grid-Data-Models (GDM) "
        "DistributionSystem representation.  Use the available tools to "
        "list readers/writers, load models, inspect components, and "
        "write output files.  Documentation is available as resources."
    ),
)

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


@mcp.tool()
def list_readers() -> list[str]:
    """List available reader formats (e.g. opendss, cim_iec_61968_13)."""
    return _list_subpackages("ditto.readers")


@mcp.tool()
def list_writers() -> list[str]:
    """List available writer formats (e.g. opendss)."""
    return _list_subpackages("ditto.writers")


# ---------------------------------------------------------------------------
# Tools — Loading models
# ---------------------------------------------------------------------------


@mcp.tool()
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

    # We need to store in a module-level dict since this is a sync tool
    # and ctx is only available in async tools with type annotation.
    # Instead, use the _SYNC_STATE fallback.
    _SYNC_STATE.store(name, system)
    return _SYNC_STATE.summary(name)


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
def list_loaded_systems() -> list[str]:
    """Return the names of all distribution systems currently loaded in memory."""
    return list(_SYNC_STATE.systems.keys())


@mcp.tool()
def get_system_summary(name: str = "default") -> dict[str, Any]:
    """Return a summary of a loaded distribution system (component counts, etc.).

    Parameters
    ----------
    name:
        The key under which the system was loaded.
    """
    return _SYNC_STATE.summary(name)


@mcp.tool()
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
        # Add a few common attribute summaries
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


@mcp.tool()
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


@mcp.tool()
def write_opendss(
    name: str = "default",
    output_path: str = "./opendss_output",
    separate_substations: bool = True,
    separate_feeders: bool = True,
) -> str:
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
    str
        Confirmation message with the output path.
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
    return f"OpenDSS model written to {out}"


@mcp.tool()
def export_gdm_json(
    name: str = "default",
    output_path: str = "./model.json",
) -> str:
    """Serialize a loaded system to GDM JSON format.

    Parameters
    ----------
    name:
        System key.
    output_path:
        Destination file path for the JSON export.

    Returns
    -------
    str
        Confirmation message.
    """
    system = _SYNC_STATE.get(name)
    out = Path(output_path).resolve()
    system.to_json(out, overwrite=True)
    return f"GDM JSON exported to {out}"


@mcp.tool()
def convert_model(
    reader_type: str,
    writer_type: str,
    input_path: str,
    output_path: str = "./converted_output",
    save_gdm: str | None = None,
) -> str:
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
    str
        Confirmation message.
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

    if save_gdm:
        gdm_path = Path(save_gdm).resolve()
        system.to_json(gdm_path, overwrite=True)

    WriterClass = _import_writer(writer_type)
    writer_instance = WriterClass(system)
    out = Path(output_path).resolve()
    out.mkdir(parents=True, exist_ok=True)
    writer_instance.write(out)

    msg = f"Conversion complete: {reader_type} → {writer_type}.  Output: {out}"
    if save_gdm:
        msg += f"  GDM JSON saved to {gdm_path}"
    return msg


# ---------------------------------------------------------------------------
# Resources — Documentation
# ---------------------------------------------------------------------------


@mcp.resource("ditto://docs")
def docs_index() -> str:
    """List all available DiTTo documentation pages."""
    pages = list_doc_pages()
    return json.dumps(pages, indent=2)


@mcp.resource("ditto://docs/{page}")
def docs_page(page: str) -> str:
    """Read a specific DiTTo documentation page by slug.

    Available slugs: index, install, usage, reference,
    api/opendss_reader, api/cim_reader, api/opendss_writer, api/cim_writer.
    """
    return read_doc_page(page)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt(description="Step-by-step guide for converting a distribution model between formats")
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


@mcp.prompt(description="Explore a loaded distribution system model interactively")
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


# ---------------------------------------------------------------------------
# Module-level sync state
# ---------------------------------------------------------------------------
# FastMCP sync tool functions cannot receive Context, so we use a
# module-level AppState singleton to persist loaded systems across calls.

_SYNC_STATE = AppState()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    """Run the DiTTo MCP server (stdio transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
