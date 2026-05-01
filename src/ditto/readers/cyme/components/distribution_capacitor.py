from ditto.readers.cyme.cyme_mapper import CymeMapper
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.components.distribution_capacitor import DistributionCapacitor
from gdm.distribution.enums import Phase, VoltageTypes
from gdm.quantities import ReactivePower, Voltage
from gdm.distribution.equipment.phase_capacitor_equipment import PhaseCapacitorEquipment
from gdm.distribution.equipment.capacitor_equipment import CapacitorEquipment
from loguru import logger


class DistributionCapacitorMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = "Network"
    cyme_section = "SHUNT CAPACITOR SETTING"

    def parse(self, row, section_id_sections):
        name = self.map_name(row)
        bus = self.map_bus(row, section_id_sections)
        phases = self.map_phases(row, section_id_sections)
        controllers = self.map_controllers(row)
        equipment = self.map_equipment(row, phases)
        in_service = self.map_in_service(row)
        return DistributionCapacitor.model_construct(
            name=name,
            bus=bus,
            phases=phases,
            controllers=controllers,
            equipment=equipment,
            in_service=in_service,
        )

    def map_name(self, row):
        return row["DeviceNumber"]

    def map_phases(self, row, section_id_sections):
        phases = []

        # Check which phases have non-zero kvar values
        if "FixedKVARA" in row and float(row.get("FixedKVARA", 0.0)) > 0:
            phases.append(Phase.A)
        if "FixedKVARB" in row and float(row.get("FixedKVARB", 0.0)) > 0:
            phases.append(Phase.B)
        if "FixedKVARC" in row and float(row.get("FixedKVARC", 0.0)) > 0:
            phases.append(Phase.C)

        if phases == []:
            raise ValueError(
                f"Could not determine phases for capacitor {row['DeviceNumber']} on section {row['SectionID']} - no phases have kvar > 0"
            )
        return phases

    def map_bus(self, row, section_id_sections):
        section_id = row["SectionID"]
        section = section_id_sections[section_id]
        from_bus_name = section["FromNodeID"]
        to_bus_name = section["ToNodeID"]
        to_bus = None
        from_bus = None

        from_bus = self.system.get_component(component_type=DistributionBus, name=from_bus_name)

        to_bus = self.system.get_component(component_type=DistributionBus, name=to_bus_name)

        if from_bus is None:
            if to_bus is None:
                logger.warning(f"Capacitor {section_id} has no bus")
                return None
            return to_bus
        return from_bus

    def map_controllers(self, row):
        return []

    def map_equipment(self, row, phases):
        """Map equipment using actual phase-specific kvar values from Network row.

        Instead of reading generic equipment template from Equipment.txt,
        read the actual installed phase-specific values from SHUNT CAPACITOR SETTING.
        """
        # Get the voltage from the row (KV column in SHUNT CAPACITOR SETTING)
        rated_voltage = Voltage(float(row["KV"]), "kilovolt")

        # Determine connection type for voltage type
        connection = row.get("Connection", "Y")
        if connection in ("Y", "YNG"):
            voltage_type = VoltageTypes.LINE_TO_GROUND
        else:
            voltage_type = VoltageTypes.LINE_TO_LINE

        # Build phase capacitors from actual phase-specific kvar values
        phase_capacitors = []
        phase_kvar_map = {
            Phase.A: float(row.get("FixedKVARA", 0.0)),
            Phase.B: float(row.get("FixedKVARB", 0.0)),
            Phase.C: float(row.get("FixedKVARC", 0.0)),
        }

        for phase in phases:
            kvar_value = phase_kvar_map[phase]
            # Only create phase capacitor if it has non-zero kvar
            if kvar_value > 0:
                phase_capacitor = PhaseCapacitorEquipment(
                    name=self._phase_name(row, phase),
                    rated_reactive_power=ReactivePower(kvar_value, "kilovar"),
                    num_banks_on=1,  # Assume 1 bank is on
                )
                phase_capacitors.append(phase_capacitor)

        # Create the equipment object with actual values
        equipment = CapacitorEquipment(
            name=row["DeviceNumber"],
            phase_capacitors=phase_capacitors,
            rated_voltage=rated_voltage,
            voltage_type=voltage_type,
        )
        return equipment

    def _phase_name(self, row, phase):
        """Generate phase-specific name for phase capacitor."""
        base_name = row["DeviceNumber"]
        if phase == Phase.A:
            return base_name + "_A"
        elif phase == Phase.B:
            return base_name + "_B"
        elif phase == Phase.C:
            return base_name + "_C"
        return base_name

    def map_in_service(self, row):
        return True if int(row["ConnectionStatus"]) == 0 else False
