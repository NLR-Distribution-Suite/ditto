from ditto.readers.cyme.cyme_mapper import CymeMapper
from ditto.readers.cyme.equipment.phase_voltagesource_equipment import (
    PhaseVoltageSourceEquipmentMapper,
)
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.components.distribution_vsource import DistributionVoltageSource
from gdm.distribution.equipment.voltagesource_equipment import VoltageSourceEquipment
from gdm.distribution.enums import VoltageTypes
from ditto.readers.cyme.constants import ModelUnitSystem


class DistributionVoltageSourceMapper(CymeMapper):
    def __init__(self, cyme_model, units=ModelUnitSystem):
        super().__init__(cyme_model, units=units)

    cyme_file = "Network"
    cyme_section = "SOURCE"

    def parse(self, row):
        name = self.map_name(row)
        bus = self.map_bus(row)
        feeder = bus.feeder
        substation = bus.substation
        if "OperatingVoltageA" in row:
            voltage = float(row["OperatingVoltageA"])
            source_voltage_type = VoltageTypes.LINE_TO_GROUND
        elif "DesiredVoltage" in row:
            voltage = float(row["DesiredVoltage"])
            source_voltage_type = VoltageTypes.LINE_TO_LINE
        else:
            raise ValueError(f"Operating voltage not found in row: {row}")

        if voltage is None or voltage == "":
            return None

        phases = [phs for phs in bus.phases]
        equipment = self.map_equipment(bus, voltage, source_voltage_type)

        return DistributionVoltageSource.model_construct(
            name=name,
            feeder=feeder,
            substation=substation,
            bus=bus,
            phases=phases,
            equipment=equipment,
        )

    def map_name(self, row):
        name = row["NodeID"]
        return name

    def map_feeder(self, row):
        feeder = row["NetworkID"]
        return feeder

    def map_bus(self, row):
        bus_name = row["NodeID"]
        bus = self.system.get_component(DistributionBus, bus_name)
        return bus

    def map_equipment(self, bus, voltage, source_voltage_type):
        mapper = PhaseVoltageSourceEquipmentMapper(self.system)
        sources = mapper.parse(bus, voltage, source_voltage_type)
        return VoltageSourceEquipment.model_construct(name=bus.name + "-source", sources=sources)
