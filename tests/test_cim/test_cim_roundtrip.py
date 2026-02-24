"""CIM → GDM → CIM → GDM roundtrip tests for information loss detection.

These tests verify that converting through the CIM format preserves component
counts, names, and key attributes. The roundtrip path is:
  CIM XML → (Reader) → GDM DistributionSystem → (Writer) → CIM XML → (Reader) → GDM

Known limitations
-----------------
- Solar and Fuse: The CIM writer emits them but the reader has no SPARQL queries
  to parse them back. They are excluded from roundtrip checks.
"""

from pathlib import Path

import pytest

from gdm.distribution import DistributionSystem
from gdm.distribution.components import (
    DistributionBus,
    DistributionCapacitor,
    DistributionLoad,
    DistributionRegulator,
    DistributionTransformer,
    DistributionVoltageSource,
    MatrixImpedanceBranch,
    MatrixImpedanceSwitch,
)
from gdm.distribution.enums import Phase, VoltageTypes
from gdm.distribution.equipment import (
    CapacitorEquipment,
    LoadEquipment,
    MatrixImpedanceBranchEquipment,
    MatrixImpedanceSwitchEquipment,
    PhaseCapacitorEquipment,
    PhaseLoadEquipment,
    VoltageSourceEquipment,
    PhaseVoltageSourceEquipment,
)
from gdm.quantities import (
    ActivePower,
    ReactivePower,
    Voltage,
    Resistance,
    Reactance,
    Distance,
)

from ditto.readers.cim_iec_61968_13.reader import Reader as CimReader
from ditto.writers.cim_iec_61968_13.write import Writer as CimWriter

# Component types supported by both the CIM writer and reader (can roundtrip).
ROUNDTRIP_COMPONENT_TYPES = [
    DistributionBus,
    DistributionVoltageSource,
    DistributionLoad,
    MatrixImpedanceBranch,
    DistributionTransformer,
    DistributionRegulator,
    DistributionCapacitor,
    MatrixImpedanceSwitch,
]


def _get_component_counts(system: DistributionSystem) -> dict[str, int]:
    """Return {type_name: count} for all roundtrip-safe component types."""
    return {
        cls.__name__: len(list(system.get_components(cls))) for cls in ROUNDTRIP_COMPONENT_TYPES
    }


def _get_component_names(system: DistributionSystem, component_type) -> set[str]:
    """Return the set of component names for a given type."""
    return {c.name for c in system.get_components(component_type)}


def _cim_roundtrip(system: DistributionSystem, tmp_path: Path) -> DistributionSystem:
    """Write a GDM system to CIM XML and read it back."""
    writer = CimWriter(system)
    writer.write(output_path=tmp_path, output_mode="single")
    reader = CimReader(tmp_path / "model.xml")
    reader.read()
    return reader.get_system()


def _build_synthetic_system() -> DistributionSystem:
    """Build a minimal system without transformers (which cannot roundtrip yet).

    Components: 3 buses, 1 voltage source, 1 load, 1 line, 1 capacitor, 1 switch.
    """
    from gdm.quantities import (
        CapacitancePULength,
        Current,
        ReactancePULength,
        ResistancePULength,
    )

    system = DistributionSystem(auto_add_composed_components=True)

    source_bus = DistributionBus(
        name="source_bus",
        phases=[Phase.A, Phase.B, Phase.C],
        rated_voltage=Voltage(12.47, "kilovolt"),
        voltage_type=VoltageTypes.LINE_TO_LINE,
        voltagelimits=[],
        coordinate=None,
    )
    bus_1 = DistributionBus(
        name="bus_1",
        phases=[Phase.A, Phase.B, Phase.C],
        rated_voltage=Voltage(12.47, "kilovolt"),
        voltage_type=VoltageTypes.LINE_TO_LINE,
        voltagelimits=[],
        coordinate=None,
    )
    bus_2 = DistributionBus(
        name="bus_2",
        phases=[Phase.A, Phase.B, Phase.C],
        rated_voltage=Voltage(12.47, "kilovolt"),
        voltage_type=VoltageTypes.LINE_TO_LINE,
        voltagelimits=[],
        coordinate=None,
    )

    vsource = DistributionVoltageSource(
        name="vsource_1",
        bus=source_bus,
        phases=[Phase.A, Phase.B, Phase.C],
        equipment=VoltageSourceEquipment(
            name="vsource_equip_1",
            sources=[
                PhaseVoltageSourceEquipment(
                    name=f"phase_vsource_{ph.value}",
                    r0=Resistance(0.001, "ohm"),
                    r1=Resistance(0.001, "ohm"),
                    x0=Reactance(0.001, "ohm"),
                    x1=Reactance(0.001, "ohm"),
                    voltage=Voltage(12.47, "kilovolt"),
                    voltage_type=VoltageTypes.LINE_TO_LINE,
                    angle=120.0 * i,
                )
                for i, ph in enumerate([Phase.A, Phase.B, Phase.C])
            ],
        ),
    )

    line_equipment = MatrixImpedanceBranchEquipment(
        name="line_equip_1",
        r_matrix=ResistancePULength(
            [
                [0.0881, 0.0312, 0.0306],
                [0.0312, 0.0902, 0.0316],
                [0.0306, 0.0316, 0.0865],
            ],
            "ohm/mi",
        ),
        x_matrix=ReactancePULength(
            [
                [0.2074, 0.0935, 0.0855],
                [0.0935, 0.2008, 0.0951],
                [0.0855, 0.0951, 0.2049],
            ],
            "ohm/mi",
        ),
        c_matrix=CapacitancePULength(
            [
                [2.903, -0.679, -0.350],
                [-0.679, 3.159, -0.585],
                [-0.350, -0.585, 2.810],
            ],
            "nanofarad/mi",
        ),
        ampacity=Current(400, "ampere"),
    )

    line_1 = MatrixImpedanceBranch(
        name="line_source_to_bus1",
        buses=[source_bus, bus_1],
        length=Distance(500, "meter"),
        phases=[Phase.A, Phase.B, Phase.C],
        equipment=line_equipment,
    )

    load_1 = DistributionLoad(
        name="load_1",
        bus=bus_1,
        phases=[Phase.A, Phase.B, Phase.C],
        equipment=LoadEquipment(
            name="load_equip_1",
            phase_loads=[
                PhaseLoadEquipment(
                    name=f"phase_load_{ph.value}",
                    real_power=ActivePower(100, "kilowatt"),
                    reactive_power=ReactivePower(50, "kilovar"),
                    z_real=0.0,
                    z_imag=0.0,
                    i_real=0.0,
                    i_imag=0.0,
                    p_real=1.0,
                    p_imag=1.0,
                )
                for ph in [Phase.A, Phase.B, Phase.C]
            ],
        ),
    )

    capacitor_1 = DistributionCapacitor(
        name="cap_1",
        bus=bus_2,
        phases=[Phase.A, Phase.B, Phase.C],
        controllers=[],
        equipment=CapacitorEquipment(
            name="cap_equip_1",
            rated_voltage=Voltage(12.47, "kilovolt"),
            voltage_type=VoltageTypes.LINE_TO_LINE,
            phase_capacitors=[
                PhaseCapacitorEquipment(
                    name=f"phase_cap_{ph.value}",
                    rated_reactive_power=ReactivePower(200, "kilovar"),
                    resistance=Resistance(0, "ohm"),
                    reactance=Reactance(0, "ohm"),
                    num_banks_on=1,
                    num_banks=1,
                )
                for ph in [Phase.A, Phase.B, Phase.C]
            ],
        ),
    )

    switch_equipment = MatrixImpedanceSwitchEquipment(
        name="switch_equip_1",
        r_matrix=ResistancePULength(
            [[0.0001, 0.0, 0.0], [0.0, 0.0001, 0.0], [0.0, 0.0, 0.0001]],
            "ohm/mi",
        ),
        x_matrix=ReactancePULength(
            [[0.0001, 0.0, 0.0], [0.0, 0.0001, 0.0], [0.0, 0.0, 0.0001]],
            "ohm/mi",
        ),
        c_matrix=CapacitancePULength(
            [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
            "nanofarad/mi",
        ),
        ampacity=Current(400, "ampere"),
    )

    switch_1 = MatrixImpedanceSwitch(
        name="switch_bus1_to_bus2",
        buses=[bus_1, bus_2],
        length=Distance(1, "meter"),
        phases=[Phase.A, Phase.B, Phase.C],
        equipment=switch_equipment,
        is_closed=[True, True, True],
    )

    system.add_components(
        source_bus,
        bus_1,
        bus_2,
        vsource,
        line_1,
        load_1,
        capacitor_1,
        switch_1,
    )
    return system


# ---------------------------------------------------------------------------
# Test: Synthetic system roundtrip (no transformers — they have a known bug)
# ---------------------------------------------------------------------------


class TestSyntheticCimRoundtrip:
    """Roundtrip a hand-built system through CIM write → read.

    Transformers are excluded because the CIM reader assigns the wrong bus
    voltages for transformer-connected buses (see module docstring).
    """

    @pytest.fixture()
    def original_system(self) -> DistributionSystem:
        return _build_synthetic_system()

    @pytest.fixture()
    def roundtripped_system(self, original_system, tmp_path) -> DistributionSystem:
        return _cim_roundtrip(original_system, tmp_path)

    def test_bus_count_preserved(self, original_system, roundtripped_system):
        orig = len(list(original_system.get_components(DistributionBus)))
        rt = len(list(roundtripped_system.get_components(DistributionBus)))
        assert rt == orig

    def test_bus_names_preserved(self, original_system, roundtripped_system):
        orig_names = _get_component_names(original_system, DistributionBus)
        rt_names = _get_component_names(roundtripped_system, DistributionBus)
        assert {n.lower() for n in orig_names} == {n.lower() for n in rt_names}

    def test_bus_voltages_preserved(self, original_system, roundtripped_system):
        orig_buses = {
            b.name.lower(): b.rated_voltage
            for b in original_system.get_components(DistributionBus)
        }
        for bus in roundtripped_system.get_components(DistributionBus):
            orig = orig_buses[bus.name.lower()]
            # Convert both to the same unit for comparison
            orig_volts = orig.to("volt").magnitude
            rt_volts = bus.rated_voltage.to("volt").magnitude
            assert (
                abs(rt_volts - orig_volts) < 1.0
            ), f"Bus {bus.name}: {bus.rated_voltage} != {orig}"

    def test_voltage_source_preserved(self, original_system, roundtripped_system):
        orig = list(original_system.get_components(DistributionVoltageSource))
        rt = list(roundtripped_system.get_components(DistributionVoltageSource))
        assert len(rt) == len(orig)
        assert rt[0].name.lower() == orig[0].name.lower()

    def test_load_names_preserved(self, original_system, roundtripped_system):
        """Load names survive roundtrip.

        The CIM writer splits a multi-phase load into per-phase EnergyConsumers,
        so the roundtripped system may have more load objects (one per original
        phase) than the original. We check that every original name appears.
        """
        orig_names = {ld.name.lower() for ld in original_system.get_components(DistributionLoad)}
        rt_names = {ld.name.lower() for ld in roundtripped_system.get_components(DistributionLoad)}
        assert orig_names <= rt_names or orig_names == rt_names

    def test_load_bus_assignment_preserved(self, original_system, roundtripped_system):
        """Loads remain on the same bus (checked by name match)."""
        orig_bus_map = {
            ld.name.lower(): ld.bus.name.lower()
            for ld in original_system.get_components(DistributionLoad)
        }
        for ld in roundtripped_system.get_components(DistributionLoad):
            orig_bus = orig_bus_map.get(ld.name.lower())
            if orig_bus is not None:
                assert ld.bus.name.lower() == orig_bus

    def test_line_count_and_name_preserved(self, original_system, roundtripped_system):
        orig = list(original_system.get_components(MatrixImpedanceBranch))
        rt = list(roundtripped_system.get_components(MatrixImpedanceBranch))
        assert len(rt) == len(orig)
        assert {ln.name.lower() for ln in rt} == {ln.name.lower() for ln in orig}

    def test_line_bus_connections_preserved(self, original_system, roundtripped_system):
        orig_lines = {
            ln.name.lower(): tuple(sorted(b.name.lower() for b in ln.buses))
            for ln in original_system.get_components(MatrixImpedanceBranch)
        }
        for ln in roundtripped_system.get_components(MatrixImpedanceBranch):
            assert tuple(sorted(b.name.lower() for b in ln.buses)) == orig_lines[ln.name.lower()]

    def test_line_length_preserved(self, original_system, roundtripped_system):
        orig_lines = {
            ln.name.lower(): ln.length.to("meter").magnitude
            for ln in original_system.get_components(MatrixImpedanceBranch)
        }
        for ln in roundtripped_system.get_components(MatrixImpedanceBranch):
            rt_m = ln.length.to("meter").magnitude
            assert abs(rt_m - orig_lines[ln.name.lower()]) < 1.0

    def test_capacitor_names_preserved(self, original_system, roundtripped_system):
        """Capacitor names survive roundtrip.

        Like loads, the CIM writer may split a multi-phase capacitor into
        per-phase LinearShuntCompensators, so the count may increase.
        """
        orig_names = {
            c.name.lower() for c in original_system.get_components(DistributionCapacitor)
        }
        rt_names = {
            c.name.lower() for c in roundtripped_system.get_components(DistributionCapacitor)
        }
        assert orig_names <= rt_names or orig_names == rt_names

    def test_switch_count_and_name_preserved(self, original_system, roundtripped_system):
        orig = list(original_system.get_components(MatrixImpedanceSwitch))
        rt = list(roundtripped_system.get_components(MatrixImpedanceSwitch))
        assert len(rt) == len(orig)
        assert {s.name.lower() for s in rt} == {s.name.lower() for s in orig}

    def test_switch_bus_connections_preserved(self, original_system, roundtripped_system):
        orig_sw = {
            sw.name.lower(): tuple(sorted(b.name.lower() for b in sw.buses))
            for sw in original_system.get_components(MatrixImpedanceSwitch)
        }
        for sw in roundtripped_system.get_components(MatrixImpedanceSwitch):
            assert tuple(sorted(b.name.lower() for b in sw.buses)) == orig_sw[sw.name.lower()]


# ---------------------------------------------------------------------------
# Test: CIM → GDM → CIM → GDM  (IEEE 13-node, full model)
# ---------------------------------------------------------------------------


class TestCimRoundtripIEEE13:
    """Full roundtrip tests using the IEEE 13-node CIM XML fixture."""

    @pytest.fixture()
    def original_system(self, ieee13_node_xml_file) -> DistributionSystem:
        reader = CimReader(ieee13_node_xml_file)
        reader.read()
        return reader.get_system()

    @pytest.fixture()
    def roundtripped_system(
        self, original_system: DistributionSystem, tmp_path
    ) -> DistributionSystem:
        return _cim_roundtrip(original_system, tmp_path)

    def test_component_counts_are_preserved(self, original_system, roundtripped_system):
        """Every supported component type retains the same count.

        The CIM writer splits multi-phase loads and capacitors into per-phase
        CIM objects, so the roundtripped count may be higher for those types.
        We allow ``actual >= expected`` for them instead of strict equality.
        """
        # Types where per-phase splitting can increase the count on roundtrip.
        PER_PHASE_SPLIT_TYPES = {"DistributionLoad", "DistributionCapacitor"}

        original_counts = _get_component_counts(original_system)
        roundtripped_counts = _get_component_counts(roundtripped_system)
        for type_name, expected in original_counts.items():
            actual = roundtripped_counts.get(type_name, 0)
            if type_name in PER_PHASE_SPLIT_TYPES:
                assert (
                    actual >= expected
                ), f"{type_name}: expected at least {expected}, got {actual}"
            else:
                assert actual == expected, f"{type_name}: expected {expected}, got {actual}"

    @pytest.mark.parametrize(
        "component_type",
        ROUNDTRIP_COMPONENT_TYPES,
        ids=[c.__name__ for c in ROUNDTRIP_COMPONENT_TYPES],
    )
    def test_component_names_are_preserved(
        self, original_system, roundtripped_system, component_type
    ):
        """Component names survive the roundtrip (case-insensitive)."""
        original_names = {n.lower() for n in _get_component_names(original_system, component_type)}
        roundtripped_names = {
            n.lower() for n in _get_component_names(roundtripped_system, component_type)
        }
        missing = original_names - roundtripped_names
        assert not missing, f"{component_type.__name__}: names lost in roundtrip: {missing}"

    def test_bus_rated_voltages_preserved(self, original_system, roundtripped_system):
        orig_buses = {
            b.name.lower(): b.rated_voltage
            for b in original_system.get_components(DistributionBus)
        }
        for bus in roundtripped_system.get_components(DistributionBus):
            orig = orig_buses.get(bus.name.lower())
            if orig is None:
                continue
            assert abs(bus.rated_voltage.to("volt").magnitude - orig.to("volt").magnitude) < 1.0

    def test_line_lengths_preserved(self, original_system, roundtripped_system):
        orig_lines = {
            ln.name.lower(): ln.length
            for ln in original_system.get_components(MatrixImpedanceBranch)
        }
        for ln in roundtripped_system.get_components(MatrixImpedanceBranch):
            orig = orig_lines.get(ln.name.lower())
            if orig is None:
                continue
            assert abs(ln.length.to("meter").magnitude - orig.to("meter").magnitude) < 1.0

    def test_load_bus_assignments_preserved(self, original_system, roundtripped_system):
        orig_loads = {
            ld.name.lower(): ld.bus.name.lower()
            for ld in original_system.get_components(DistributionLoad)
        }
        for ld in roundtripped_system.get_components(DistributionLoad):
            orig_bus = orig_loads.get(ld.name.lower())
            if orig_bus is None:
                continue
            assert ld.bus.name.lower() == orig_bus


# ---------------------------------------------------------------------------
# Test: OpenDSS → GDM → CIM → GDM  (IEEE 13-node)
# ---------------------------------------------------------------------------


class TestOpenDSSToCimRoundtrip:
    """Read IEEE 13-node from OpenDSS, write CIM, read CIM back, compare."""

    @pytest.fixture()
    def opendss_system(self) -> DistributionSystem:
        from ditto.readers.opendss.reader import Reader as OpenDSSReader

        master_file = (
            Path(__file__).parent.parent
            / "data"
            / "opendss_circuit_models"
            / "ieee13"
            / "Master.dss"
        )
        reader = OpenDSSReader(master_file)
        return reader.get_system()

    @pytest.fixture()
    def roundtripped_system(
        self, opendss_system: DistributionSystem, tmp_path
    ) -> DistributionSystem:
        return _cim_roundtrip(opendss_system, tmp_path)

    def test_component_counts_within_tolerance(self, opendss_system, roundtripped_system):
        """Component counts preserved or only slightly reduced."""
        original_counts = _get_component_counts(opendss_system)
        roundtripped_counts = _get_component_counts(roundtripped_system)

        for type_name, expected in original_counts.items():
            if expected == 0:
                continue
            actual = roundtripped_counts.get(type_name, 0)
            loss_pct = (expected - actual) / expected * 100
            assert loss_pct <= 1, f"{type_name}: lost {loss_pct:.0f}% ({expected} → {actual})"

    def test_buses_survive_roundtrip(self, opendss_system, roundtripped_system):
        original_names = {b.name.lower() for b in opendss_system.get_components(DistributionBus)}
        roundtripped_names = {
            b.name.lower() for b in roundtripped_system.get_components(DistributionBus)
        }
        missing = original_names - roundtripped_names
        loss_pct = len(missing) / len(original_names) * 100 if original_names else 0
        assert loss_pct <= 1, f"Lost {len(missing)}/{len(original_names)} buses"

    def test_loads_survive_roundtrip(self, opendss_system, roundtripped_system):
        original = len(list(opendss_system.get_components(DistributionLoad)))
        roundtripped = len(list(roundtripped_system.get_components(DistributionLoad)))
        if original > 0:
            loss_pct = (original - roundtripped) / original * 100
            assert loss_pct <= 1

    def test_lines_survive_roundtrip(self, opendss_system, roundtripped_system):
        original = len(list(opendss_system.get_components(MatrixImpedanceBranch)))
        roundtripped = len(list(roundtripped_system.get_components(MatrixImpedanceBranch)))
        if original > 0:
            loss_pct = (original - roundtripped) / original * 100
            assert loss_pct <= 1
