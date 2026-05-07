import re

from gdm.distribution.components.geometry_branch import GeometryBranch
from gdm.distribution.components.matrix_impedance_branch import MatrixImpedanceBranch
from gdm.distribution.equipment.geometry_branch_equipment import GeometryBranchEquipment
from gdm.distribution.equipment.matrix_impedance_branch_equipment import MatrixImpedanceBranchEquipment
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.quantities import Distance
from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import parse_phases, phases_without_neutral, sanitize_name, safe_float
from ditto.readers.synergi.length_units import length_units
from loguru import logger


class LineSectionMapper(SynergiMapper):

    synergi_table = "InstSection"
    synergi_database = "Model"

    def __init__(self, system, node_feeder_map=None):
        super().__init__(system, node_feeder_map)
        self._matrix_equip_cache = None

    def _build_matrix_equip_cache(self):
        cache = {}
        for equip in self.system.get_components(MatrixImpedanceBranchEquipment):
            m = re.search(r'_(\d+)ph$', equip.name)
            if not m:
                continue
            n_ph = int(m.group(1))
            base = equip.name[: equip.name.rfind(f'_{n_ph}ph')]
            key = (base.lower(), n_ph)
            if key not in cache:
                cache[key] = equip
        return cache

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections, devices_on_section=None):
        section_id = str(row["SectionId"]).strip()
        if devices_on_section and section_id in devices_on_section:
            return None
        from_node_id = str(row["FromNodeId"]).strip()
        to_node_id = str(row["ToNodeId"]).strip()

        try:
            from_bus = self.system.get_component(DistributionBus, sanitize_name(from_node_id))
        except Exception:
            logger.warning(f"Section {section_id}: from bus {from_node_id} not found")
            return None

        try:
            to_bus = self.system.get_component(DistributionBus, sanitize_name(to_node_id))
        except Exception:
            logger.warning(f"Section {section_id}: to bus {to_node_id} not found")
            return None

        phases = parse_phases(row["SectionPhases"])
        wire_phases = phases_without_neutral(phases)
        if not wire_phases:
            logger.warning(f"Section {section_id}: no wire phases found")
            return None

        length_val = safe_float(row.get("SectionLength_MUL"), 1.0) or 1.0
        length = Distance(length_val, length_units[unit_type]["MUL"]).to("m")
        feeder, substation = self._lookup_feeder_substation(from_node_id)

        geometry_equip = self._find_geometry_equipment(row, phases)
        if geometry_equip is not None:
            return GeometryBranch(
                name=sanitize_name(section_id),
                buses=[from_bus, to_bus],
                length=length,
                phases=phases,
                equipment=geometry_equip,
                substation=substation,
                feeder=feeder,
            )

        matrix_equip = self._find_matrix_equipment(row, wire_phases)
        if matrix_equip is None:
            logger.warning(f"Section {section_id}: no equipment found, skipping")
            return None

        return MatrixImpedanceBranch(
            name=sanitize_name(section_id),
            buses=[from_bus, to_bus],
            length=length,
            phases=wire_phases,
            equipment=matrix_equip,
            substation=substation,
            feeder=feeder,
        )

    def _find_geometry_equipment(self, row, phases):
        config_id = str(row.get("ConfigurationId", "")).strip()
        if not config_id or config_id == "Unknown":
            return None

        conductor_names = []
        for phase_char in str(row["SectionPhases"]).replace(" ", ""):
            if phase_char == "N":
                conductor_names.append(str(row["NeutralConductorId"]).strip())
            else:
                conductor_names.append(str(row["PhaseConductorId"]).strip())

        equip_name = config_id + "_" + "_".join(conductor_names)
        try:
            equip = self.system.get_component(GeometryBranchEquipment, equip_name)
            if len(equip.horizontal_positions) == len(phases):
                return equip
            logger.warning(
                f"Section {row['SectionId']}: geometry {config_id} has wrong position count "
                f"({len(equip.horizontal_positions)} vs {len(phases)} phases), falling back to matrix impedance"
            )
        except Exception:
            logger.warning(
                f"Section {row['SectionId']}: geometry {config_id} not found, falling back to matrix impedance"
            )
        return None

    def _find_matrix_equipment(self, row, wire_phases):
        if self._matrix_equip_cache is None:
            self._matrix_equip_cache = self._build_matrix_equip_cache()
        conductor_name = str(row["PhaseConductorId"]).strip()
        n_cond = len(wire_phases)
        base_key = sanitize_name(conductor_name).lower()
        return self._matrix_equip_cache.get((base_key, n_cond))

