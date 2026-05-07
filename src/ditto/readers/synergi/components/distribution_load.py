from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.equipment.load_equipment import LoadEquipmentMapper
from ditto.readers.synergi.utils import sanitize_name, safe_float
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.components.distribution_load import DistributionLoad
from gdm.distribution.enums import Phase
from loguru import logger

class DistributionLoadMapper(SynergiMapper):

    synergi_table = "Loads"    
    synergi_database = "Model"


    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        name = self.map_name(row)
        section = section_id_sections.get(str(row["SectionId"]).strip(), {})
        bus = self.map_bus(row, section_id_sections)
        if bus is None:
            return None
        phases = self.map_phases(row, bus)
        if len(phases) == 0:
            logger.warning(f"Load {name} has no kW values. Skipping...")
            return None
        z, i, p = self.map_zip(row, section)
        equipment = self.map_equipment(row, z, i, p)
        feeder, substation = self._lookup_feeder_substation(str(section.get("FromNodeId", "")).strip())
        return DistributionLoad(name=name,
                                bus=bus,
                                phases=phases,
                                equipment=equipment,
                                substation=substation,
                                feeder=feeder)
        

    def map_name(self, row):
        return sanitize_name(f"load_{row['SectionId']}")

    def map_bus(self, row, section_id_sections):
        section_id = str(row["SectionId"]).strip()
        section = section_id_sections.get(section_id, {})
        for node_key in ("ToNodeId", "FromNodeId"):
            bus_name = sanitize_name(str(section.get(node_key, "")).strip())
            try:
                return self.system.get_component(DistributionBus, bus_name)
            except Exception:
                pass
        logger.warning(f"Load {section_id}: no bus found, skipping")
        return None

    def map_phases(self, row, bus):
        bus_wire_phases = {ph for ph in bus.phases if ph != Phase.N}
        phase_map = {1: Phase.A, 2: Phase.B, 3: Phase.C}
        phases = []
        for ph_idx, phase in phase_map.items():
            kw = safe_float(row.get(f"Phase{ph_idx}Kw"), 0.0)
            kvar = safe_float(row.get(f"Phase{ph_idx}Kvar"), 0.0)
            customers = safe_float(row.get(f"Phase{ph_idx}Customers"), 0.0)
            if (kw != 0.0 or kvar != 0.0 or customers > 0) and phase in bus_wire_phases:
                phases.append(phase)
        return phases

    def map_zip(self, row, section):
        is_spot = bool(row.get("IsSpotLoad", False))
        if is_spot:
            pct_z = safe_float(section.get("PercentSpotLoadConstImpedance"), 0.0)
            pct_i = safe_float(section.get("PercentSpotLoadConstCurrent"), 0.0)
        else:
            pct_z = safe_float(section.get("PercentDistLoadConstImpedance"), 0.0)
            pct_i = safe_float(section.get("PercentDistLoadConstCurrent"), 0.0)
        z = max(0.0, min(1.0, pct_z / 100.0))
        i = max(0.0, min(1.0, pct_i / 100.0))
        p = max(0.0, 1.0 - z - i)
        return z, i, p

    def map_equipment(self, row, z, i, p):
        mapper = LoadEquipmentMapper(self.system)
        equipment = mapper.parse(row, z, i, p)
        return equipment

