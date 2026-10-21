from pathlib import Path

import numpy as np
import pytest
import opendssdirect as odd

from gdm.systems.distribution.components.distribution_load import DistributionLoad
from gdm.systems.distribution.components.distribution_transformer import (
    DistributionTransformer,
)

from ditto.writers.opendss.write import Writer
from ditto.readers.opendss.reader import Reader
from ditto.enumerations import OpenDSSFileTypes
from gdm.systems.distribution.common import SequencePair
from ditto.writers.opendss.equipment.distribution_transformer_equipment import (
    DistributionTransformerEquipmentMapper,
)
from tests.helpers import get_metrics

test_folder = Path(__file__).parent.parent


TEST_MODELS = [
    test_folder
    / "data"
    / "opendss_circuit_models"
    / "ieee13"
    / OpenDSSFileTypes.MASTER_FILE.value,
    test_folder / "data" / "opendss_circuit_models" / "P4U" / OpenDSSFileTypes.MASTER_FILE.value,
]


@pytest.mark.parametrize("DSS_MODEL", TEST_MODELS)
def test_opendss_roundtrip_converion(DSS_MODEL, tmp_path):
    pre_converion_metrics = get_metrics(DSS_MODEL)
    reader = Reader(DSS_MODEL)
    writer = Writer(reader.get_system())

    assert tmp_path.exists(), f"Export path: {tmp_path}"
    writer.write(tmp_path, separate_substations=False, separate_feeders=False)
    dss_master_file = tmp_path / OpenDSSFileTypes.MASTER_FILE.value
    assert dss_master_file.exists()
    post_converion_metrics = get_metrics(dss_master_file)
    assert np.allclose(
        pre_converion_metrics, post_converion_metrics, rtol=0.01, atol=0.01
    ), f"Round trip coversion exceeds error tolerance, \npre: {pre_converion_metrics}, \npost: {post_converion_metrics}"


def _redirect_without_control_changes(master_file: Path) -> None:
    odd.Basic.ClearAll()
    odd.Text.Command(f'redirect "{master_file}"')
    odd.Solution.Solve()


def test_roundtrip_preserves_load_voltage_and_cvr_properties(tmp_path):
    """ZIP canonicalization must not discard source load operating limits."""

    source = test_folder / "data" / "opendss_circuit_models" / "ckt7" / "Master.dss"
    reader = Reader(source)
    system = reader.get_system()
    assert system.get_num_supplemental_attributes() == 0
    load = next(
        load for load in system.get_components(DistributionLoad) if load.name == "1001577-d1"
    )
    phase = load.equipment.phase_loads[0]
    assert phase.min_voltage_pu == pytest.approx(0.85)
    assert phase.max_voltage_pu == pytest.approx(1.05)
    assert phase.active_power_voltage_exponent == pytest.approx(0.8)
    assert phase.reactive_power_voltage_exponent == pytest.approx(3.0)
    Writer(system).write(tmp_path, separate_substations=False, separate_feeders=False)

    _redirect_without_control_changes(tmp_path / OpenDSSFileTypes.MASTER_FILE.value)
    odd.Loads.Name("1001577-d1")

    assert odd.Loads.Model() == 4
    assert odd.Loads.Vminpu() == pytest.approx(0.85)
    assert odd.Loads.Vmaxpu() == pytest.approx(1.05)
    assert odd.Loads.CVRwatts() == pytest.approx(0.8)
    assert odd.Loads.CVRvars() == pytest.approx(3.0)


def test_roundtrip_preserves_center_tapped_transformer_connections(tmp_path):
    """A center-tapped transformer must not be split as a generic two-phase unit."""

    source = test_folder / "data" / "opendss_circuit_models" / "SFO" / "Master.dss"
    reader = Reader(source)
    Writer(reader.get_system()).write(tmp_path, separate_substations=False, separate_feeders=False)

    _redirect_without_control_changes(tmp_path / OpenDSSFileTypes.MASTER_FILE.value)
    name = "tr(r:p10udt6041-p10udt6041lv)"
    odd.Transformers.Name(name)

    assert odd.Transformers.NumWindings() == 3
    assert odd.CktElement.NumPhases() == 1
    assert odd.CktElement.BusNames() == [
        "p10udt6041.1.3",
        "p10udt6041lv.1.0",
        "p10udt6041lv.0.2",
    ]

    odd.Transformers.Wdg(1)
    assert odd.Transformers.kV() == pytest.approx(12.47)
    odd.Transformers.Wdg(2)
    assert odd.Transformers.kV() == pytest.approx(0.12)
    odd.Transformers.Wdg(3)
    assert odd.Transformers.kV() == pytest.approx(0.12)


def test_roundtrip_preserves_transformer_magnetizing_current(tmp_path):
    """Transformer %imag must survive the GDM equipment conversion."""

    source = test_folder / "data" / "opendss_circuit_models" / "ckt7" / "Master.dss"
    reader = Reader(source)
    system = reader.get_system()
    transformer = next(
        transformer
        for transformer in system.get_components(DistributionTransformer)
        if transformer.name == "1001577_xfmr_abc"
    )
    assert transformer.equipment.magnetizing_current_pct == pytest.approx(1.0)
    Writer(system).write(tmp_path, separate_substations=False, separate_feeders=False)

    _redirect_without_control_changes(tmp_path / OpenDSSFileTypes.MASTER_FILE.value)
    odd.Text.Command("? Transformer.1001577_xfmr_abc.%imag")

    assert float(odd.Text.Result()) == pytest.approx(1.0)


def test_roundtrip_preserves_unequal_transformer_windings(tmp_path):
    source = tmp_path / "source.dss"
    source.write_text(
        "clear\nnew circuit.test bus1=source basekv=12.47 phases=3\n"
        "new transformer.test phases=1 windings=3 "
        "buses=[source.2.3 secondary.1.0 secondary.0.2] conns=[delta wye wye] "
        "kvs=[12.47 .12 .12] kvas=[50 50 50] %loadloss=.798816 "
        "%rs=[.266272 .532544 .532544] %noloadloss=.37 "
        "xhl=2.4 xht=1.6 xlt=2.4\n"
        "new load.test bus1=secondary.1 phases=1 kv=.12 kw=10 kvar=2\n"
        "set voltagebases=[12.47 .208]\ncalcvoltagebases\nsolve\n"
    )
    system = Reader(source).get_system()
    equipment = system.get_component(DistributionTransformer, "test").equipment
    assert equipment.coupling_sequences == [
        SequencePair(0, 1),
        SequencePair(0, 2),
        SequencePair(1, 2),
    ]
    assert equipment.winding_reactances == [2.4, 1.6, 2.4]
    # Reversed and shuffled pairs must still address the same winding couplings.
    equipment.coupling_sequences = [SequencePair(2, 0), SequencePair(2, 1), SequencePair(1, 0)]
    equipment.winding_reactances = [1.6, 2.4, 2.4]
    mapper = DistributionTransformerEquipmentMapper(equipment, system)
    mapper.populate_opendss_dictionary()
    assert {key: value for key, value in mapper.opendss_dict.items() if key.startswith("X")} == {
        "X12": 2.4,
        "X13": 1.6,
        "X23": 2.4,
    }
    output = tmp_path / "output"
    Writer(system).write(output, separate_substations=False, separate_feeders=False)
    _redirect_without_control_changes(output / "Master.dss")
    odd.Transformers.Name("test")
    assert odd.Transformers.Xhl() == pytest.approx(2.4)
    assert odd.Transformers.Xht() == pytest.approx(1.6)
    assert odd.Transformers.Xlt() == pytest.approx(2.4)
    for winding, expected in enumerate([0.266272, 0.532544, 0.532544], start=1):
        odd.Transformers.Wdg(winding)
        assert odd.Transformers.R() == pytest.approx(expected)


def test_center_tapped_two_winding_equipment_maps_both_secondary_reactances():
    from gdm.systems.distribution import DistributionSystem
    from gdm.systems.distribution.equipment import DistributionTransformerEquipment

    equipment = DistributionTransformerEquipment.example()
    equipment.is_center_tapped = True
    mapper = DistributionTransformerEquipmentMapper(equipment, DistributionSystem())
    mapper.populate_opendss_dictionary()
    assert mapper.opendss_dict["X12"] == equipment.winding_reactances[0]
    assert mapper.opendss_dict["X13"] == equipment.winding_reactances[0]


def test_cim_reader_uses_zero_based_transformer_pairs():
    from ditto.readers.cim_iec_61968_13.equipment.distribution_transformer_equipment import (
        DistributionTransformerEquipmentMapper as CimTransformerEquipmentMapper,
    )
    from gdm.systems.distribution import DistributionSystem

    mapper = CimTransformerEquipmentMapper(DistributionSystem())
    assert mapper.map_coupling_sequences({}) == [SequencePair(0, 1)]
