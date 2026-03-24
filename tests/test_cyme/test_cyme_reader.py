""" Module for testing parsers."""
from pathlib import Path
import pytest
from ditto.readers.cyme.reader import Reader
from ditto.writers.opendss.write import Writer
import sys
from loguru import logger

logger.add(sys.stderr, level="WARNING")

base_path = Path(__file__).parent.parent
cyme_circuit_models = base_path / "data" / "cyme_test_cases"
assert cyme_circuit_models.exists, f"{cyme_circuit_models} does not exist"

# Require all models to be called Model.mdb and Equipment.mdb for testing

cyme_network_name = "Network.txt"
cyme_equipment_name = "Equipment.txt"
cyme_load_name = "Load.txt"

target_files = set([cyme_network_name, cyme_equipment_name])
matching_folders = []
for folder in Path(cyme_circuit_models).rglob("*"):
    if folder.is_dir():
        files_in_folder = set(f.name for f in folder.iterdir() if f.is_file())
        if target_files.issubset(files_in_folder):
            matching_folders.append(folder)


@pytest.mark.parametrize("cyme_folder", matching_folders)
def test_cyme_reader(cyme_folder: Path, tmp_path):
    export_path = base_path / "dump_from_tests" / "cyme" / cyme_folder.name
    if not export_path.exists():
        export_path.mkdir(parents=True, exist_ok=True)

    load_model_id = "1"
    reader = Reader(
        cyme_folder / cyme_network_name,
        cyme_folder / cyme_equipment_name,
        cyme_folder / cyme_load_name,
        load_model_id,
    )
    writer = Writer(reader.get_system())
    writer.write(export_path / "opendss", separate_substations=False, separate_feeders=False)
    system = reader.get_system()
    json_path = (export_path / cyme_folder.stem.lower()).with_suffix(".json")
    system.to_json(json_path, overwrite=True, indent=4)
    system.to_geojson(export_path / (cyme_folder.stem.lower() + ".geojson"))

    assert json_path.exists(), "Failed to export the json file"
