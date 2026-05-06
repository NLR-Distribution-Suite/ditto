import numpy as np
from gdm.distribution.components.matrix_impedance_recloser import MatrixImpedanceRecloser
from gdm.distribution.equipment.matrix_impedance_recloser_equipment import MatrixImpedanceRecloserEquipment
from gdm.distribution.equipment.recloser_controller_equipment import RecloserControllerEquipment
from gdm.distribution.controllers.distribution_recloser_controller import DistributionRecloserController
from gdm.distribution.common.curve import TimeCurrentCurve
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.enums import LineType
from gdm.quantities import ResistancePULength, ReactancePULength, CapacitancePULength
from infrasys.quantities import Current, Distance, Time
from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import parse_phases, phases_without_neutral, sanitize_name, safe_float
from loguru import logger


class RecloserMapper(SynergiMapper):

    synergi_table = "InstReclosers"
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
        return MatrixImpedanceRecloser(
            name=self.map_name(row),
            buses=buses,
            length=self.map_length(),
            phases=phases,
            is_closed=self.map_is_closed(row, phases),
            equipment=self.map_equipment(row, phases, amp_rating),
            controller=self.map_controller(row, amp_rating),
            substation=substation,
            feeder=feeder,
        )

    def map_name(self, row):
        section_id = str(row["SectionId"]).strip()
        device_id = str(row.get("UniqueDeviceId", section_id)).strip()
        return sanitize_name(f"recloser_{device_id}_{section_id}")

    def map_buses(self, row, section_id_sections):
        section_id = str(row["SectionId"]).strip()
        section = section_id_sections.get(section_id, {})
        from_bus = None
        to_bus = None
        try:
            from_bus = self.system.get_component(DistributionBus, sanitize_name(str(section["FromNodeId"]).strip()))
        except Exception:
            logger.warning(f"Recloser {section_id}: from bus not found")
        try:
            to_bus = self.system.get_component(DistributionBus, sanitize_name(str(section["ToNodeId"]).strip()))
        except Exception:
            logger.warning(f"Recloser {section_id}: to bus not found")
        return [from_bus, to_bus]

    def map_phases(self, row, section_id_sections):
        section_id = str(row["SectionId"]).strip()
        section = section_id_sections.get(section_id, {})
        phases = phases_without_neutral(parse_phases(section.get("SectionPhases", "")))
        return phases or parse_phases(section.get("SectionPhases", ""))

    def map_is_closed(self, row, phases):
        is_open = bool(safe_float(row.get("RecloserIsOpen", 0)))
        return [not is_open] * len(phases)

    def map_amp_rating(self, row):
        return safe_float(row.get("AmpRating"), 560.0) or 560.0

    def map_equipment(self, row, phases, amp_rating):
        section_id = str(row["SectionId"]).strip()
        device_id = str(row.get("UniqueDeviceId", section_id)).strip()
        n = len(phases)
        r = np.eye(n) * 1e-4
        x = np.eye(n) * 1e-4
        c = np.eye(n) * 1e-3
        return MatrixImpedanceRecloserEquipment(
            name=sanitize_name(f"recloser_equip_{device_id}_{section_id}"),
            construction=LineType.OVERHEAD,
            r_matrix=ResistancePULength(r, "ohm/km"),
            x_matrix=ReactancePULength(x, "ohm/km"),
            c_matrix=CapacitancePULength(c, "nF/km"),
            ampacity=Current(amp_rating, "ampere"),
        )

    def map_controller(self, row, amp_rating):
        section_id = str(row["SectionId"]).strip()
        device_id = str(row.get("UniqueDeviceId", section_id)).strip()
        safe_did = sanitize_name(f"{device_id}_{section_id}")
        tcc_fast = TimeCurrentCurve(
            name=f"tcc_fast_{safe_did}",
            curve_x=Current(np.array([amp_rating * m for m in [1.5, 2.0, 5.0, 10.0]]), "ampere"),
            curve_y=Time(np.array([30.0, 5.0, 0.5, 0.05]), "second"),
        )
        tcc_delayed = TimeCurrentCurve(
            name=f"tcc_delayed_{safe_did}",
            curve_x=Current(np.array([amp_rating * m for m in [1.5, 2.0, 5.0, 10.0]]), "ampere"),
            curve_y=Time(np.array([60.0, 15.0, 1.0, 0.1]), "second"),
        )
        ctrl_equip = RecloserControllerEquipment(name=f"recloser_ctrl_equip_{safe_did}")
        num_shots = 4
        return DistributionRecloserController(
            name=f"recloser_ctrl_{safe_did}",
            delay=Time(0.0, "second"),
            ground_delayed=tcc_delayed,
            ground_fast=tcc_fast,
            phase_delayed=tcc_delayed,
            phase_fast=tcc_fast,
            num_fast_ops=1,
            num_shots=num_shots,
            reclose_intervals=Time(np.array([1.0] * (num_shots - 1)), "second"),
            reset_time=Time(15.0, "second"),
            equipment=ctrl_equip,
        )

    def map_length(self):
        return Distance(1, "m")
