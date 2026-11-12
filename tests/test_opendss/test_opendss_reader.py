"""Module for testing parsers."""

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
import opendssdirect as odd

from gdm.distribution import DistributionSystem
from gdm.distribution.components import DistributionBus
from gdm.distribution.enums import Phase
from ditto.readers.opendss.components import branches
from ditto.readers.opendss.components.cables import get_cables_equipment
from ditto.readers.opendss.components.conductors import get_conductors_equipment
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


def test_cable_dimensions():
    odd.Basic.ClearAll()
    odd.Text.Command("new circuit.test")
    odd.Text.Command(
        "new cndata.cable1 runits=km radunits=cm gmrunits=cm "
        "inslayer=0.4 diains=2.1 diacable=2.7 rac=0.6 gmrac=0.34 "
        "diam=0.9 rstrand=2.5 gmrstrand=0.025 diastrand=0.064 k=6 normamps=100"
    )

    cable = get_cables_equipment()[0]

    assert cable.name == "cable1"
    assert cable.num_neutral_strands == 6
    assert cable.strand_gmr.to("cm").magnitude == pytest.approx(0.025)
    assert cable.conductor_gmr.to("cm").magnitude == pytest.approx(0.34)
    assert cable.strand_diameter.to("cm").magnitude == pytest.approx(0.064)
    assert cable.insulation_thickness.to("cm").magnitude == pytest.approx(0.4)
    type(cable).model_validate(cable.model_dump())


def test_wire_gmr_is_preserved_and_equivalent_wires_are_deduplicated():
    odd.Basic.ClearAll()
    odd.Text.Command("new circuit.test")
    for name in ("wire1", "wire2"):
        odd.Text.Command(
            f"new wiredata.{name} rac=0.1 runits=km gmrac=0.3 gmrunits=cm "
            "diam=1 radunits=cm normamps=100"
        )
    wires = get_conductors_equipment()
    assert wires[0].conductor_gmr.to("cm").magnitude == pytest.approx(0.3)
    assert wires[0].uuid == wires[1].uuid


def test_recloser_controls_are_not_silently_discarded(tmp_path):
    source = tmp_path / "master.dss"
    source.write_text(
        "clear\nnew circuit.test bus1=source basekv=12.47\n"
        "new line.feeder bus1=source bus2=load length=1\n"
        "new recloser.test monitoredobj=line.feeder\n"
        "set voltagebases=[12.47]\ncalcvoltagebases\nsolve\n"
    )
    with pytest.raises(NotImplementedError, match="recloser controls"):
        Reader(source)


def test_switch_rejects_different_terminal_phases(monkeypatch):
    from gdm.distribution.equipment import MatrixImpedanceSwitchEquipment

    system = DistributionSystem(auto_add_composed_components=True)
    buses = [
        DistributionBus.example().model_copy(update={"name": name, "uuid": uuid4()})
        for name in ("source", "load")
    ]
    system.add_components(*buses)

    monkeypatch.setattr(
        branches,
        "odd",
        SimpleNamespace(
            Lines=SimpleNamespace(
                First=lambda: 1,
                Name=lambda: "malformed_switch",
                IsSwitch=lambda: True,
                Length=lambda: 1.0,
                Units=lambda: 3,
                Geometry=lambda: "",
                R1=lambda: 0.1,
                X1=lambda: 0.2,
                C1=lambda: 0.3,
                R0=lambda: 0.4,
                X0=lambda: 0.5,
                C0=lambda: 0.6,
                Next=lambda: 0,
            ),
            CktElement=SimpleNamespace(
                Name=lambda: "Line.malformed_switch",
                BusNames=lambda: ["source.1.2.3", "load.1.2"],
                NumPhases=lambda: 3,
                NumConductors=lambda: 3,
                NodeOrder=lambda: [1, 2, 3, 1, 2, 0],
                IsOpen=lambda _terminal, _phase: False,
            ),
        ),
    )
    monkeypatch.setattr(branches, "get_reclosers", lambda: {})
    monkeypatch.setattr(branches, "get_fuses", lambda: {})
    monkeypatch.setattr(
        branches,
        "_build_matrix_branch",
        lambda *_args, **_kwargs: MatrixImpedanceSwitchEquipment.example(),
    )
    monkeypatch.setattr(
        branches,
        "get_equipment_from_catalog",
        lambda equipment, *_args: equipment,
    )

    with pytest.raises(ValueError, match="unsupported terminal connections"):
        branches.get_branches(system, {}, {}, {}, {})


JSON_CASEFILES = (Path(__file__).parent.parent / "data" / "opendss_circuit_models").rglob("*.json")
