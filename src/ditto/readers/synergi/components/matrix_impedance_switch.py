import numpy as np
from gdm.distribution.components.matrix_impedance_switch import MatrixImpedanceSwitch
from gdm.distribution.equipment.matrix_impedance_switch_equipment import MatrixImpedanceSwitchEquipment
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.enums import LineType
from gdm.quantities import ResistancePULength, ReactancePULength, CapacitancePULength
from infrasys.quantities import Current, Distance
from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import parse_phases, phases_without_neutral, sanitize_name, safe_float
from loguru import logger


class _SwitchBaseMapper(SynergiMapper):

    synergi_database = "Model"
    _is_open_field = "SwitchIsOpen"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        section_id = str(row["SectionId"]).strip()
        section = section_id_sections.get(section_id)
        if section is None:
            return None
        buses = self.map_buses(row, section_id_sections)
        if buses[0] is None or buses[1] is None:
            return None
        phases = self.map_phases(row, section_id_sections)
        if not phases:
            return None
        feeder, substation = self._lookup_feeder_substation(str(section["FromNodeId"]).strip())
        return MatrixImpedanceSwitch(
            name=self.map_name(row),
            buses=buses,
            length=self.map_length(),
            phases=phases,
            is_closed=self.map_is_closed(row, phases),
            equipment=self.map_equipment(row, phases),
            substation=substation,
            feeder=feeder,
        )

    def map_name(self, row):
        section_id = str(row["SectionId"]).strip()
        device_id = str(row.get("UniqueDeviceId", section_id)).strip()
        return sanitize_name(f"sw_{device_id}_{section_id}")

    def map_buses(self, row, section_id_sections):
        section_id = str(row["SectionId"]).strip()
        section = section_id_sections.get(section_id, {})
        from_bus = None
        to_bus = None
        try:
            from_bus = self.system.get_component(DistributionBus, sanitize_name(str(section["FromNodeId"]).strip()))
        except Exception:
            logger.warning(f"Switch {section_id}: from bus not found")
        try:
            to_bus = self.system.get_component(DistributionBus, sanitize_name(str(section["ToNodeId"]).strip()))
        except Exception:
            logger.warning(f"Switch {section_id}: to bus not found")
        return [from_bus, to_bus]

    def map_phases(self, row, section_id_sections):
        section_id = str(row["SectionId"]).strip()
        section = section_id_sections.get(section_id, {})
        phases = phases_without_neutral(parse_phases(section.get("SectionPhases", "")))
        return phases or parse_phases(section.get("SectionPhases", ""))

    def map_is_closed(self, row, phases):
        is_open = bool(safe_float(row.get(self._is_open_field, 0)))
        return [not is_open] * len(phases)

    def map_equipment(self, row, phases):
        section_id = str(row["SectionId"]).strip()
        device_id = str(row.get("UniqueDeviceId", section_id)).strip()
        n = len(phases)
        r = np.eye(n) * 1e-4
        x = np.eye(n) * 1e-4
        c = np.eye(n) * 1e-3
        return MatrixImpedanceSwitchEquipment(
            name=sanitize_name(f"sw_equip_{device_id}_{section_id}"),
            construction=LineType.OVERHEAD,
            r_matrix=ResistancePULength(r, "ohm/km"),
            x_matrix=ReactancePULength(x, "ohm/km"),
            c_matrix=CapacitancePULength(c, "nF/km"),
            ampacity=Current(400, "ampere"),
        )

    def map_length(self):
        return Distance(1, "m")


class SwitchMapper(_SwitchBaseMapper):

    synergi_table = "InstSwitches"
    _is_open_field = "SwitchIsOpen"


class BreakerMapper(_SwitchBaseMapper):

    synergi_table = "InstBreakers"
    _is_open_field = "BreakerIsOpen"
