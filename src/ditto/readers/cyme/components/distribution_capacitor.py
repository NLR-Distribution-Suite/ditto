from ditto.readers.cyme.cyme_mapper import CymeMapper
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.components.distribution_capacitor import DistributionCapacitor
from gdm.distribution.enums import Phase, VoltageTypes
from gdm.quantities import ReactivePower, Voltage
from gdm.distribution.equipment.phase_capacitor_equipment import PhaseCapacitorEquipment
from gdm.distribution.equipment.capacitor_equipment import CapacitorEquipment
from loguru import logger
from ditto.readers.cyme.constants import ModelUnitSystem


class DistributionCapacitorMapper(CymeMapper):
    def __init__(self, system, units=ModelUnitSystem):
        super().__init__(system, units=units)

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

        # Some CYME datasets (e.g. 13-node sample) encode capacitor phase in
        # the `Phase` column and kvar in aggregate `KVAR`/`ThreePhaseKVAR`.
        # Fall back to section phase parsing when per-phase kvar columns are
        # not present or all zero.
        if phases == []:
            phase_text = str(row.get("Phase", "")).strip().upper()
            phase_map = {"A": Phase.A, "B": Phase.B, "C": Phase.C}
            phases = [phase_map[ch] for ch in ("A", "B", "C") if ch in phase_text]

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

    def _map_voltage_type(self, row):
        connection = row.get("Connection", "Y")
        if connection in ("Y", "YNG"):
            return VoltageTypes.LINE_TO_GROUND
        return VoltageTypes.LINE_TO_LINE

    def _safe_float(self, value, default=0.0):
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _phase_kvar_map_from_row(self, row):
        return {
            Phase.A: self._safe_float(row.get("FixedKVARA", 0.0)),
            Phase.B: self._safe_float(row.get("FixedKVARB", 0.0)),
            Phase.C: self._safe_float(row.get("FixedKVARC", 0.0)),
        }

    def _apply_aggregate_kvar_fallback(self, row, phases, phase_kvar_map):
        if any(value > 0 for value in phase_kvar_map.values()) or len(phases) == 0:
            return phase_kvar_map

        three_phase_kvar = self._safe_float(row.get("ThreePhaseKVAR", 0.0))
        kvar = self._safe_float(row.get("KVAR", 0.0))
        if three_phase_kvar > 0:
            per_phase_kvar = three_phase_kvar / len(phases)
        elif kvar > 0:
            # CYME SHUNT CAPACITOR SETTING commonly stores per-phase
            # kvar in KVAR for multi-phase rows (e.g. Phase=ABC).
            per_phase_kvar = kvar
        else:
            per_phase_kvar = 0.0

        if per_phase_kvar > 0:
            for phase in phases:
                phase_kvar_map[phase] = per_phase_kvar
        return phase_kvar_map

    def _build_phase_capacitors(self, row, phases, phase_kvar_map):
        phase_capacitors = []
        for phase in phases:
            kvar_value = phase_kvar_map[phase]
            if kvar_value <= 0:
                continue
            phase_capacitor = PhaseCapacitorEquipment(
                name=self._phase_name(row, phase),
                rated_reactive_power=ReactivePower(kvar_value, "kilovar"),
                num_banks_on=1,
            )
            phase_capacitors.append(phase_capacitor)
        return phase_capacitors

    def map_equipment(self, row, phases):
        """Map equipment using actual phase-specific kvar values from Network row.

        Instead of reading generic equipment template from Equipment.txt,
        read the actual installed phase-specific values from SHUNT CAPACITOR SETTING.
        """
        rated_voltage = Voltage(float(row["KV"]), "kilovolt")
        voltage_type = self._map_voltage_type(row)
        phase_kvar_map = self._phase_kvar_map_from_row(row)
        phase_kvar_map = self._apply_aggregate_kvar_fallback(row, phases, phase_kvar_map)
        phase_capacitors = self._build_phase_capacitors(row, phases, phase_kvar_map)

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
