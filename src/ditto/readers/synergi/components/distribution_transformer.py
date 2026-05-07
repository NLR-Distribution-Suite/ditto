import math

from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import parse_phases, phases_without_neutral, sanitize_name
from gdm.distribution.equipment.distribution_transformer_equipment import DistributionTransformerEquipment
from gdm.distribution.components.distribution_transformer import DistributionTransformer
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.enums import Phase, ConnectionType, VoltageTypes
from gdm.quantities import Voltage
from loguru import logger


class DistributionTransformerMapper(SynergiMapper):

    synergi_table = "InstPrimaryTransformers"
    synergi_database = "Model"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        equipment = self.map_equipment(row)
        if equipment is None:
            return None
        name = self.map_name(row)
        buses = self.map_bus(row, section_id_sections)
        if buses[0] is None or buses[1] is None:
            return None
        winding_phases = self.map_winding_phases(row)
        section_id = str(row["SectionId"]).strip()
        section = section_id_sections.get(section_id, {})
        from_node = str(section.get("FromNodeId", "")).strip()
        feeder, substation = self._lookup_feeder_substation(from_node)

        for bus, wdg in zip(buses, equipment.windings):
            kv = wdg.rated_voltage.to("kilovolt").magnitude
            if wdg.voltage_type == VoltageTypes.LINE_TO_LINE:
                kv = kv / math.sqrt(3)
            bus.rated_voltage = Voltage(round(kv, 5), "kilovolt")

        return DistributionTransformer(
            name=name,
            buses=buses,
            winding_phases=winding_phases,
            equipment=equipment,
            substation=substation,
            feeder=feeder,
        )

    def map_name(self, row):
        device_id = str(row.get("UniqueDeviceId", row["SectionId"])).strip()
        return sanitize_name(device_id)

    def map_winding_phases(self, row):
        phases = phases_without_neutral(parse_phases(row["ConnectedPhases"]))
        return [phases, phases]

    def map_bus(self, row, section_id_sections):
        section_id = str(row["SectionId"]).strip()
        section = section_id_sections.get(section_id, {})
        from_bus_name = sanitize_name(str(section.get("FromNodeId", "")).strip())
        to_bus_name = sanitize_name(str(section.get("ToNodeId", "")).strip())
        from_bus = None
        to_bus = None
        try:
            from_bus = self.system.get_component(component_type=DistributionBus, name=from_bus_name)
        except Exception:
            logger.warning(f"Transformer {section_id}: from bus {from_bus_name} not found")
        try:
            to_bus = self.system.get_component(component_type=DistributionBus, name=to_bus_name)
        except Exception:
            logger.warning(f"Transformer {section_id}: to bus {to_bus_name} not found")
        return [from_bus, to_bus]

    def map_equipment(self, row):
        equipment_name = str(row["TransformerType"]).strip()
        try:
            return self.system.get_component(component_type=DistributionTransformerEquipment, name=equipment_name)
        except Exception:
            logger.warning(f"Transformer equipment {equipment_name!r} not found, skipping transformer")
            return None
