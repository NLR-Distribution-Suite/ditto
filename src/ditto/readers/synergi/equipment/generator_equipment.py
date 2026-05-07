from gdm.distribution.enums import VoltageTypes
from gdm.distribution.equipment.solar_equipment import SolarEquipment
from infrasys.quantities import ActivePower, Voltage
from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import sanitize_name, safe_float


class GeneratorEquipmentMapper(SynergiMapper):

    synergi_table = "DevGenerators"
    synergi_database = "Equipment"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        return SolarEquipment(
            name=self.map_name(row),
            rated_power=self.map_rated_power(row),
            resistance=0.0,
            reactance=self.map_reactance(row),
            rated_voltage=self.map_rated_voltage(row),
            voltage_type=self.map_voltage_type(row),
        )

    def map_name(self, row):
        gen_name = str(row.get("GeneratorName", "")).strip()
        return f"solar_equip_{sanitize_name(gen_name)}"

    def map_rated_power(self, row):
        kw = safe_float(row.get("KwRating"), 1000) or 1000
        return ActivePower(kw, "kilowatt")

    def map_reactance(self, row):
        return safe_float(row.get("PosSequenceReactance"), 0.5) or 0.5

    def map_rated_voltage(self, row):
        kv = safe_float(row.get("KvRating"), 13.2) or 13.2
        return Voltage(kv, "kilovolt")

    def map_voltage_type(self, row):
        return VoltageTypes.LINE_TO_LINE
