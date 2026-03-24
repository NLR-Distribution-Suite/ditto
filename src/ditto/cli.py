from __future__ import annotations

from pathlib import Path
import importlib
import pkgutil
from typing import Optional

import typer
from loguru import logger


app = typer.Typer(help="Ditto CLI: convert between model formats")


def _list_subpackages(package) -> list[str]:
    try:
        return [name for _, name, ispkg in pkgutil.iter_modules(package.__path__) if ispkg]
    except Exception:
        return []


def _import_reader(reader_name: str):
    module_path = f"ditto.readers.{reader_name}.reader"
    module = importlib.import_module(module_path)
    return getattr(module, "Reader")


def _import_writer(writer_name: str):
    module_path = f"ditto.writers.{writer_name}.write"
    module = importlib.import_module(module_path)
    return getattr(module, "Writer")


@app.command("list-readers")
def list_readers() -> None:
    """List available reader packages."""
    try:
        import ditto.readers as readers_pkg  # type: ignore
    except Exception:
        logger.error(
            "Could not import `ditto.readers`. Ensure PYTHONPATH includes `src` when running from repo."
        )
        raise typer.Exit(code=2)

    available_readers = _list_subpackages(readers_pkg)
    for r in available_readers:
        typer.echo(r)


@app.command("list-writers")
def list_writers() -> None:
    """List available writer packages."""
    try:
        import ditto.writers as writers_pkg  # type: ignore
    except Exception:
        logger.error(
            "Could not import `ditto.writers`. Ensure PYTHONPATH includes `src` when running from repo."
        )
        raise typer.Exit(code=2)

    available_writers = _list_subpackages(writers_pkg)
    for w in available_writers:
        typer.echo(w)


@app.command("convert")
def convert(
    reader: str = typer.Option(..., help="Reader package name (e.g. opendss, cim_iec_61968_13)"),
    writer: str = typer.Option(..., help="Writer package name (e.g. opendss)"),
    input: Path = typer.Option(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=True,
        help="Input file/folder for the chosen reader",
    ),
    output: Path = typer.Option(Path("."), help="Output folder for the writer (default: .)"),
    save_gdm: Optional[Path] = typer.Option(
        None, help="Path to save intermediate GDM/DistributionSystem JSON"
    ),
) -> None:
    """Convert from a reader to a writer and optionally save intermediate GDM JSON."""
    try:
        import ditto.readers as readers_pkg  # type: ignore
        import ditto.writers as writers_pkg  # type: ignore
    except Exception:
        logger.error(
            "Could not import `ditto` package. Ensure PYTHONPATH includes `src` when running from repo."
        )
        raise typer.Exit(code=2)

    available_readers = _list_subpackages(readers_pkg)
    available_writers = _list_subpackages(writers_pkg)

    if reader not in available_readers:
        logger.error(f"Reader '{reader}' not found. Available: {available_readers}")
        raise typer.Exit(code=2)

    if writer not in available_writers:
        logger.error(f"Writer '{writer}' not found. Available: {available_writers}")
        raise typer.Exit(code=2)

    try:
        ReaderClass = _import_reader(reader)
    except Exception:
        logger.exception("Failed to import reader module.")
        raise typer.Exit(code=2)

    logger.info(f"Instantiating reader '{reader}' with input {input}")
    reader_instance = ReaderClass(input)

    if hasattr(reader_instance, "read") and callable(getattr(reader_instance, "read")):
        try:
            reader_instance.read()
        except Exception:
            logger.exception("Reader `read()` failed")
            raise typer.Exit(code=1)

    system = reader_instance.get_system()

    if save_gdm:
        logger.info(f"Exporting intermediate GDM JSON to {save_gdm}")
        reader_instance.to_json(save_gdm)

    try:
        WriterClass = _import_writer(writer)
    except Exception:
        logger.exception("Failed to import writer module.")
        raise typer.Exit(code=2)

    writer_instance = WriterClass(system)
    output.mkdir(parents=True, exist_ok=True)
    logger.info(f"Running writer '{writer}' -> output: {output}")
    writer_instance.write(output)

    logger.success("Conversion complete")


if __name__ == "__main__":
    app()
