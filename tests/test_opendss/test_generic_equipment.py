import importlib
import json
import xml.etree.ElementTree as ET

import numpy as np
import opendssdirect as odd
import pytest

from gdm.systems.distribution import DistributionSystem
from gdm.systems.distribution.components import (
    DistributionLoad,
    MatrixImpedanceSwitch,
    SequenceImpedanceSwitch,
)
from gdm.systems.distribution.enums import Phase
from ditto.enumerations import OpenDSSFileTypes
from ditto.readers.opendss.reader import Reader
from ditto.writers.opendss.write import Writer
from ditto.writers.opendss.components.distribution_load import DistributionLoadMapper


def make_circuit(tmp_path, switch_properties, load_properties="model=1", linecode=""):
    source = tmp_path / "source.dss"
    source.write_text(
        "clear\nnew circuit.test basekv=12.47 pu=1 phases=3 bus1=source\n"
        f"{linecode}\n"
        "new line.sw bus1=source.3.1.2 bus2=load.3.1.2 phases=3 switch=yes "
        f"{switch_properties} normamps=400\n"
        f"new load.test bus1=load phases=3 kv=12.47 kw=100 kvar=40 {load_properties}\n"
        "set voltagebases=[12.47]\ncalcvoltagebases\nsolve\n"
    )
    return source


SEQUENCE_PROPERTIES = "length=0.02 r1=0.12 x1=0.21 r0=0.45 x0=0.6 c1=3 c0=1.5 units=km"


@pytest.mark.parametrize("closed", [[True, True, True], [True, False, True], [False] * 3])
def test_sequence_switch_json_and_dss_roundtrip(tmp_path, monkeypatch, closed):
    system = Reader(make_circuit(tmp_path, SEQUENCE_PROPERTIES)).get_system()
    switch = system.get_component(SequenceImpedanceSwitch, "sw")
    switch.is_closed = closed
    assert [phase.value for phase in switch.phases] == ["C", "A", "B"]
    assert switch.length.to("km").magnitude == pytest.approx(0.02)
    assert switch.equipment.pos_seq_resistance.to("ohm/km").magnitude == pytest.approx(0.12)
    expected = switch.equipment.to_matrix_equipment()
    filename = tmp_path / "generic.json"
    system.to_json(filename)
    raw = json.loads(filename.read_text())
    assert raw["supplemental_attributes"] == []
    assert "ditto" not in filename.read_text()
    original_import = importlib.import_module

    def reject_ditto(name, package=None):
        assert not name.startswith("ditto")
        return original_import(name, package)

    with monkeypatch.context() as patch:
        patch.setattr(importlib, "import_module", reject_ditto)
        restored = DistributionSystem.from_json(filename)
    output = tmp_path / "output"
    Writer(restored).write(output, separate_substations=False, separate_feeders=False)
    odd.Basic.ClearAll()
    odd.Text.Command(f'redirect "{output / OpenDSSFileTypes.MASTER_FILE.value}"')
    odd.Lines.Name("sw")
    assert odd.Lines.IsSwitch()
    assert odd.Lines.Length() == pytest.approx(0.02)
    np.testing.assert_allclose(
        np.reshape(odd.Lines.RMatrix(), (3, 3)), expected.r_matrix.to("ohm/km").magnitude
    )
    np.testing.assert_allclose(
        np.reshape(odd.Lines.XMatrix(), (3, 3)), expected.x_matrix.to("ohm/km").magnitude
    )
    np.testing.assert_allclose(
        np.reshape(odd.Lines.CMatrix(), (3, 3)), expected.c_matrix.to("nanofarad/km").magnitude
    )
    assert odd.CktElement.BusNames() == ["source.3.1.2", "load.3.1.2"]
    assert [not odd.CktElement.IsOpen(1, i) for i in (1, 2, 3)] == closed


@pytest.mark.parametrize("closed", [[True] * 3, [True, False, True]])
def test_unbalanced_matrix_switch_remains_matrix(tmp_path, closed):
    source = make_circuit(
        tmp_path,
        "linecode=unbalanced length=0.02 units=km",
        linecode="new linecode.unbalanced nphases=3 rmatrix=[.1|.01 .2|.02 .03 .3] "
        "xmatrix=[.4|.01 .5|.02 .03 .6] cmatrix=[3|-1 4|-1 -1 5] units=km",
    )
    with source.open("a") as stream:
        stream.write("edit line.sw linecode=unbalanced length=.02 units=km\nsolve\n")
    system = Reader(source).get_system()
    switch = system.get_component(MatrixImpedanceSwitch, "sw")
    switch.is_closed = closed
    assert list(system.get_components(SequenceImpedanceSwitch)) == []
    np.testing.assert_allclose(np.diag(switch.equipment.r_matrix.magnitude), [0.1, 0.2, 0.3])
    output = tmp_path / "matrix-output"
    Writer(system).write(output, separate_substations=False, separate_feeders=False)
    odd.Basic.ClearAll()
    odd.Text.Command(f'redirect "{output / OpenDSSFileTypes.MASTER_FILE.value}"')
    odd.Lines.Name("sw")
    np.testing.assert_allclose(
        np.reshape(odd.Lines.RMatrix(), (3, 3)), switch.equipment.r_matrix.to("ohm/km").magnitude
    )
    assert [not odd.CktElement.IsOpen(1, i) for i in (1, 2, 3)] == closed


@pytest.mark.parametrize(
    "properties, expected_model",
    [
        ("model=1", 1),
        ("model=2", 2),
        ("model=3", 3),
        ("model=4 cvrwatts=.8 cvrvars=3", 4),
        ("model=5", 5),
        ("model=8 zipv=[.2 .3 .5 .1 .2 .7 .65]", 8),
    ],
)
def test_load_translation_uses_generic_equipment(tmp_path, properties, expected_model):
    system = Reader(make_circuit(tmp_path, SEQUENCE_PROPERTIES, properties)).get_system()
    load = system.get_component(DistributionLoad, "test")
    mapper = DistributionLoadMapper(load, system)
    mapper.populate_opendss_dictionary()
    assert mapper.opendss_dict["Model"] == expected_model
    if expected_model == 8:
        np.testing.assert_allclose(
            mapper.opendss_dict["ZIPV"], [0.2, 0.3, 0.5, 0.1, 0.2, 0.7, 0.65]
        )
        assert load.equipment.phase_loads[0].cutoff_voltage_pu == 0.65
    assert "opendss_model" not in type(load).model_fields


@pytest.mark.parametrize("suffix, nodes", [("2", [2, 2, 3]), ("3", [3, 2, 3])])
@pytest.mark.parametrize("closed", [[True] * 3, [True, False, True], [False] * 3])
def test_repeated_switch_connections_roundtrip(tmp_path, suffix, nodes, closed):
    source = tmp_path / "source.dss"
    source.write_text(
        "clear\nnew circuit.test basekv=12.47 pu=1 phases=3 bus1=source\n"
        f"new line.sw bus1=source.{suffix} bus2=load.{suffix} switch=yes "
        f"{SEQUENCE_PROPERTIES}\n"
        "new load.test bus1=load.2.3 phases=1 conn=delta kv=12.47 kw=10 kvar=4\n"
        "set voltagebases=[12.47]\ncalcvoltagebases\nsolve\n"
    )
    system = Reader(source).get_system()
    odd.Lines.Name("sw")
    expected_r = odd.Lines.RMatrix()
    expected_x = odd.Lines.XMatrix()
    expected_c = odd.Lines.CMatrix()
    expected_y = odd.CktElement.YPrim()
    switch = system.get_component(MatrixImpedanceSwitch, "sw")
    phases = {1: Phase.A, 2: Phase.B, 3: Phase.C}
    assert switch.phases == list(dict.fromkeys(phases[node] for node in nodes))
    assert switch.conductor_phases == [phases[node] for node in nodes]
    assert switch.num_conductors == 3
    switch.is_closed = closed
    filename = tmp_path / "system.json"
    system.to_json(filename)
    assert "ditto" not in filename.read_text()
    restored = DistributionSystem.from_json(filename)
    output = tmp_path / "output"
    Writer(restored).write(output, separate_substations=False, separate_feeders=False)
    odd.Basic.ClearAll()
    odd.Text.Command(f'redirect "{output / "Master.dss"}"')
    odd.Lines.Name("sw")
    assert odd.CktElement.NodeOrder() == nodes + nodes
    assert odd.CktElement.NumConductors() == 3
    np.testing.assert_allclose(odd.Lines.RMatrix(), expected_r)
    np.testing.assert_allclose(odd.Lines.XMatrix(), expected_x)
    np.testing.assert_allclose(odd.Lines.CMatrix(), expected_c)
    assert [not odd.CktElement.IsOpen(1, i) for i in (1, 2, 3)] == closed
    if all(closed):
        np.testing.assert_allclose(odd.CktElement.YPrim(), expected_y, rtol=1e-9, atol=1e-9)


def test_split_phase_mapping_preserves_order():
    from ditto.readers.opendss.graph_utils import _mapped_phases

    assert _mapped_phases({Phase.A: Phase.S1, Phase.B: Phase.S2}, [Phase.B, Phase.A]) == [
        Phase.S2,
        Phase.S1,
    ]


def test_cim_rejects_parallel_switch_conductors():
    from ditto.writers.cim_iec_61968_13.equipment_emitters.switch import emit_switch

    switch = MatrixImpedanceSwitch(
        **(
            dict(MatrixImpedanceSwitch.example())
            | {
                "phases": [Phase.B, Phase.C],
                "conductor_phases": [Phase.B, Phase.B, Phase.C],
            }
        )
    )
    with pytest.raises(ValueError, match="cannot preserve conductor-to-phase mapping"):
        emit_switch(None, ET.Element("root"), switch, {}, {}, {})


def test_split_phase_parallel_switch_preserves_conductor_mapping():
    import networkx as nx

    from ditto.readers.opendss.graph_utils import _fix_bus_phases

    switch = MatrixImpedanceSwitch(
        **(
            dict(MatrixImpedanceSwitch.example())
            | {"phases": [Phase.B, Phase.C], "conductor_phases": [Phase.B, Phase.B, Phase.C]}
        )
    )
    system = DistributionSystem(auto_add_composed_components=True)
    system.add_component(switch)
    graph = nx.Graph()
    graph.add_edge(
        switch.buses[0].name, switch.buses[1].name, type=MatrixImpedanceSwitch, name=switch.name
    )
    _fix_bus_phases("upstream", {Phase.B: Phase.S1, Phase.C: Phase.S2}, graph, system)
    restored = system.get_component(MatrixImpedanceSwitch, switch.name)
    assert restored.uuid == switch.uuid
    assert restored.phases == [Phase.S1, Phase.S2]
    assert restored.conductor_phases == [Phase.S1, Phase.S1, Phase.S2]
    assert restored.is_closed == switch.is_closed
