from pathlib import Path

from rdflib import Graph

from ditto.readers.opendss.reader import Reader as OpenDSSReader
from ditto.readers.cim_iec_61968_13.reader import Reader as CimReader
from ditto.readers.cim_iec_61968_13.queries import (
    query_batteries,
    query_capacitors,
    query_distribution_buses,
    query_distribution_regulators,
    query_load_break_switches,
    query_line_codes,
    query_line_segments,
    query_loads,
    query_power_transformers,
    query_regulator_controllers,
    query_source,
    query_transformer_windings,
)
from ditto.writers.cim_iec_61968_13.write import Writer as CimWriter
from gdm.distribution.components import (
    DistributionBattery,
    DistributionBus,
    DistributionCapacitor,
    DistributionRegulator,
    MatrixImpedanceSwitch,
)
from gdm.distribution import DistributionSystem
from gdm.distribution.controllers import RegulatorController
from gdm.distribution.equipment import BatteryEquipment, InverterEquipment
from gdm.distribution.enums import Phase, VoltageTypes
from gdm.quantities import ActivePower, ApparentPower, EnergyDC, ReactivePower, Voltage


_BASE = Path(__file__).parents[1]
_IEEE13_DSS = _BASE / "data" / "opendss_circuit_models" / "ieee13" / "Master.dss"


def test_cim_writer_core_reader_query_compatibility(tmp_path):
    system = OpenDSSReader(_IEEE13_DSS).get_system()
    writer = CimWriter(system)

    writer.write(output_path=tmp_path, output_mode="single")
    cim_file = tmp_path / "model.xml"

    graph = Graph()
    graph.parse(cim_file, format="xml")

    buses = query_distribution_buses(graph)
    lines = query_line_segments(graph)
    line_codes = query_line_codes(graph)
    loads = query_loads(graph)
    sources = query_source(graph)

    assert not buses.empty
    assert not lines.empty
    assert not line_codes.empty
    assert not loads.empty
    assert not sources.empty


def test_cim_writer_transformer_regulator_query_compatibility(tmp_path):
    source_system = OpenDSSReader(_IEEE13_DSS).get_system()
    source_regulators = len(list(source_system.get_components(DistributionRegulator)))
    source_controllers = len(list(source_system.get_components(RegulatorController)))
    source_capacitors = len(list(source_system.get_components(DistributionCapacitor)))
    source_switches = len(list(source_system.get_components(MatrixImpedanceSwitch)))

    writer = CimWriter(source_system)
    writer.write(output_path=tmp_path, output_mode="single")

    graph = Graph()
    graph.parse(tmp_path / "model.xml", format="xml")

    buses = query_distribution_buses(graph)
    loads = query_loads(graph)
    sources = query_source(graph)
    lines = query_line_segments(graph)
    transformers = query_power_transformers(graph)
    winding_couplings = query_transformer_windings(graph)
    regulators = query_distribution_regulators(graph)
    controllers = query_regulator_controllers(graph)
    capacitors = query_capacitors(graph)
    switches = query_load_break_switches(graph)

    assert not buses.empty
    assert not loads.empty
    assert not sources.empty
    assert not lines.empty
    assert not transformers.empty
    assert not winding_couplings.empty
    assert len(regulators) == source_regulators
    assert len(controllers) == source_controllers
    assert capacitors["capacitor"].nunique() == source_capacitors
    assert switches["switch_name"].nunique() == source_switches


def test_cim_writer_battery_query_compatibility(tmp_path):
    system = OpenDSSReader(_IEEE13_DSS).get_system()
    bus = next(iter(system.get_components(DistributionBus)))

    battery = DistributionBattery.model_construct(
        name="query_battery",
        bus=bus,
        phases=[Phase.A, Phase.B, Phase.C],
        active_power=ActivePower(30.0, "kilowatt"),
        reactive_power=ReactivePower(5.0, "kilovar"),
        controller=None,
        inverter=InverterEquipment.model_construct(
            name="query_battery_inverter",
            rated_apparent_power=ApparentPower(35.0, "kilova"),
            rise_limit=None,
            fall_limit=None,
            cutout_percent=0.1,
            cutin_percent=0.1,
            dc_to_ac_efficiency=0.96,
            eff_curve=None,
        ),
        equipment=BatteryEquipment.model_construct(
            name="query_battery_equipment",
            rated_energy=EnergyDC(120.0, "kilowatthour"),
            rated_power=ActivePower(30.0, "kilowatt"),
            charging_efficiency=0.95,
            discharging_efficiency=0.95,
            idling_efficiency=0.99,
            rated_voltage=Voltage(12.47, "kilovolt"),
            voltage_type=VoltageTypes.LINE_TO_LINE,
        ),
    )
    system.add_components(battery)

    writer = CimWriter(system)
    writer.write(output_path=tmp_path, output_mode="single")

    graph = Graph()
    graph.parse(tmp_path / "model.xml", format="xml")

    batteries = query_batteries(graph)
    assert not batteries.empty
    assert batteries["battery"].nunique() == 1
    assert batteries["battery"].iloc[0] == "query_battery"


def test_cim_writer_battery_reader_compatibility(tmp_path):
    system = DistributionSystem(auto_add_composed_components=True)
    bus = DistributionBus.model_construct(
        name="battery_bus",
        phases=[Phase.A, Phase.B, Phase.C],
        rated_voltage=Voltage(7.2, "kilovolt"),
        voltage_type=VoltageTypes.LINE_TO_GROUND,
        voltagelimits=[],
        coordinate=None,
    )
    system.add_components(bus)

    battery = DistributionBattery.model_construct(
        name="reader_battery",
        bus=bus,
        phases=[Phase.A, Phase.B, Phase.C],
        active_power=ActivePower(30.0, "kilowatt"),
        reactive_power=ReactivePower(5.0, "kilovar"),
        controller=None,
        inverter=InverterEquipment.model_construct(
            name="reader_battery_inverter",
            rated_apparent_power=ApparentPower(35.0, "kilova"),
            rise_limit=None,
            fall_limit=None,
            cutout_percent=0.1,
            cutin_percent=0.1,
            dc_to_ac_efficiency=0.96,
            eff_curve=None,
        ),
        equipment=BatteryEquipment.model_construct(
            name="reader_battery_equipment",
            rated_energy=EnergyDC(120.0, "kilowatthour"),
            rated_power=ActivePower(30.0, "kilowatt"),
            charging_efficiency=0.95,
            discharging_efficiency=0.95,
            idling_efficiency=0.99,
            rated_voltage=Voltage(12.47, "kilovolt"),
            voltage_type=VoltageTypes.LINE_TO_LINE,
        ),
    )
    system.add_components(battery)

    writer = CimWriter(system)
    writer.write(output_path=tmp_path, output_mode="single")

    reader = CimReader(tmp_path / "model.xml")
    reader.read()
    parsed_system = reader.get_system()

    parsed_batteries = list(parsed_system.get_components(DistributionBattery))
    assert len(parsed_batteries) == 1
    assert parsed_batteries[0].name == "reader_battery"
