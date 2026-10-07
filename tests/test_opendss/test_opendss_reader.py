"""Module for testing parsers."""

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from gdm.distribution import DistributionSystem
from gdm.distribution.components import DistributionBus
from gdm.distribution.enums import Phase
from ditto.readers.opendss.components import branches
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


def test_single_phase_reactor_is_read(monkeypatch):
    system = DistributionSystem(auto_add_composed_components=True)
    buses = [
        DistributionBus.example().model_copy(update={"name": name, "uuid": uuid4()})
        for name in ("source", "load")
    ]
    system.add_components(*buses)

    last_command = ""

    def command(value):
        nonlocal last_command
        last_command = value

    def result():
        return {
            "? Reactor.r1.phases": "1",
            "? Reactor.r1.r": "0.1",
            "? Reactor.r1.x": "0.2",
        }[last_command]

    monkeypatch.setattr(
        branches,
        "odd",
        SimpleNamespace(
            Circuit=SimpleNamespace(
                AllElementNames=lambda: ["Reactor.r1"],
                SetActiveElement=lambda _element: None,
            ),
            CktElement=SimpleNamespace(
                BusNames=lambda: ["source.1", "load.1"],
                NumPhases=lambda: 1,
            ),
            Text=SimpleNamespace(Command=command, Result=result),
        ),
    )

    reactors = branches.get_reactors(system)

    assert len(reactors) == 1
    assert reactors[0].phases == [Phase.A]


JSON_CASEFILES = (Path(__file__).parent.parent / "data" / "opendss_circuit_models").rglob("*.json")
