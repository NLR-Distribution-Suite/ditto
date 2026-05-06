import numpy as np
from gdm.distribution.components.matrix_impedance_fuse import MatrixImpedanceFuse
from gdm.distribution.equipment.matrix_impedance_fuse_equipment import MatrixImpedanceFuseEquipment
from gdm.distribution.common.curve import TimeCurrentCurve
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.enums import LineType
from gdm.quantities import ResistancePULength, ReactancePULength, CapacitancePULength
from infrasys.quantities import Current, Distance, Time
from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import parse_phases, phases_without_neutral, sanitize_name, safe_float
from loguru import logger


class FuseMapper(SynergiMapper):

    synergi_table = "InstFuses"
    synergi_database = "Model"

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
        amp_rating = self.map_amp_rating(row)
        feeder, substation = self._lookup_feeder_substation(str(section["FromNodeId"]).strip())
        return MatrixImpedanceFuse(
            name=self.map_name(row),
            buses=buses,
            length=self.map_length(),
            phases=phases,
            is_closed=self.map_is_closed(row, phases),
            equipment=self.map_equipment(row, phases, amp_rating),
            substation=substation,
            feeder=feeder,
        )

    def map_name(self, row):
        section_id = str(row["SectionId"]).strip()
        device_id = str(row.get("UniqueDeviceId", section_id)).strip()
        return sanitize_name(f"fuse_{device_id}_{section_id}")

    def map_buses(self, row, section_id_sections):
        section_id = str(row["SectionId"]).strip()
        section = section_id_sections.get(section_id, {})
        from_bus = None
        to_bus = None
        try:
            from_bus = self.system.get_component(DistributionBus, sanitize_name(str(section["FromNodeId"]).strip()))
        except Exception:
            logger.warning(f"Fuse {section_id}: from bus not found")
        try:
            to_bus = self.system.get_component(DistributionBus, sanitize_name(str(section["ToNodeId"]).strip()))
        except Exception:
            logger.warning(f"Fuse {section_id}: to bus not found")
        return [from_bus, to_bus]

    def map_phases(self, row, section_id_sections):
        section_id = str(row["SectionId"]).strip()
        section = section_id_sections.get(section_id, {})
        phases = phases_without_neutral(parse_phases(section.get("SectionPhases", "")))
        return phases or parse_phases(section.get("SectionPhases", ""))

    def map_is_closed(self, row, phases):
        is_open = bool(safe_float(row.get("FuseIsOpen", 0)))
        return [not is_open] * len(phases)

    def map_amp_rating(self, row):
        return safe_float(row.get("AmpRating"), 200.0) or 200.0

    def map_equipment(self, row, phases, amp_rating):
        section_id = str(row["SectionId"]).strip()
        device_id = str(row.get("UniqueDeviceId", section_id)).strip()
        n = len(phases)
        r = np.eye(n) * 1e-4
        x = np.eye(n) * 1e-4
        c = np.eye(n) * 1e-3
        tcc = TimeCurrentCurve(
            name=sanitize_name(f"tcc_fuse_{device_id}_{section_id}"),
            curve_x=Current(np.array([amp_rating * m for m in [1.5, 2.0, 5.0, 10.0]]), "ampere"),
            curve_y=Time(np.array([300.0, 10.0, 0.1, 0.01]), "second"),
        )
        return MatrixImpedanceFuseEquipment(
            name=sanitize_name(f"fuse_equip_{device_id}_{section_id}"),
            construction=LineType.OVERHEAD,
            r_matrix=ResistancePULength(r, "ohm/km"),
            x_matrix=ReactancePULength(x, "ohm/km"),
            c_matrix=CapacitancePULength(c, "nF/km"),
            ampacity=Current(amp_rating, "ampere"),
            delay=Time(0.01, "second"),
            tcc_curve=tcc,
        )

    def map_length(self):
        return Distance(1, "m")
