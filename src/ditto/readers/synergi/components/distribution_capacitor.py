from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import parse_phases, phases_without_neutral, sanitize_name
from ditto.readers.synergi.equipment.capacitor_equipment import CapacitorEquipmentMapper
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.components.distribution_capacitor import DistributionCapacitor
from gdm.distribution.enums import Phase
from loguru import logger


class DistributionCapacitorMapper(SynergiMapper):

    synergi_table = "InstCapacitors"
    synergi_database = "Model"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        section_id = str(row.get("SectionId", "")).strip()
        section = section_id_sections.get(section_id)
        if section is None:
            logger.warning(f"Capacitor {section_id}: section not found")
            return None

        bus = self.map_bus(section_id, section)
        if bus is None:
            return None

        phases = self.map_phases(row, bus)
        if not phases:
            return None

        to_node_id = str(section.get("ToNodeId", "")).strip()
        feeder, substation = self._lookup_feeder_substation(to_node_id)

        return DistributionCapacitor(
            name=self.map_name(row),
            bus=bus,
            phases=phases,
            controllers=[],
            equipment=self.map_equipment(row, phases),
            in_service=True,
            feeder=feeder,
            substation=substation,
        )

    def map_name(self, row):
        device_id = str(row.get("UniqueDeviceId", row.get("SectionId", ""))).strip()
        return sanitize_name(f"cap_{device_id}")

    def map_bus(self, section_id, section):
        to_id = sanitize_name(str(section.get("ToNodeId", "")).strip())
        from_id = sanitize_name(str(section.get("FromNodeId", "")).strip())
        for bus_name in (to_id, from_id):
            try:
                return self.system.get_component(DistributionBus, bus_name)
            except Exception:
                pass
        logger.warning(f"Capacitor {section_id}: bus not found (tried {to_id}, {from_id})")
        return None

    def map_phases(self, row, bus):
        phases = phases_without_neutral(parse_phases(str(row.get("ConnectedPhases", "ABC"))))
        if not phases:
            phases = [p for p in bus.phases if p != Phase.N]
        bus_phases = {p for p in bus.phases if p != Phase.N}
        return [p for p in phases if p in bus_phases]

    def map_equipment(self, row, phases):
        return CapacitorEquipmentMapper(self.system).parse(row, phases)
