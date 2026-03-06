"""Module for testing parsers."""

from pathlib import Path

import pytest

from ditto.readers.opendss.reader import Reader


base_path = Path(__file__).parents[1]
opendss_circuit_models = base_path / "data" / "opendss_circuit_models"
assert opendss_circuit_models.exists(), f"{opendss_circuit_models} does not exist"
OPENDSS_CASEFILES = list(opendss_circuit_models.rglob("Master.dss"))


@pytest.mark.parametrize("opendss_file", OPENDSS_CASEFILES)
def test_serialize_opendss_model(opendss_file: Path, fixed_tmp_path):
    example_name = opendss_file.parent.name
    export_path = Path(fixed_tmp_path) / example_name
    if not export_path.exists():
        export_path.mkdir(parents=True, exist_ok=True)
    parser = Reader(opendss_file)
    system = parser.get_system()

    # Verify the parsed system has components
    component_types = list(system.get_component_types())
    assert len(component_types) > 0, "Parsed system has no component types"

    json_path = export_path / (opendss_file.stem.lower() + ".json")
    system.to_json(json_path, overwrite=True)
    assert json_path.exists(), "Failed to export the json file"


JSON_CASEFILES = (Path(__file__).parent.parent / "data" / "opendss_circuit_models").rglob("*.json")
