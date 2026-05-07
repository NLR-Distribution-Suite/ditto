from gdm.distribution.components.distribution_solar import DistributionSolar
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.enums import Phase, VoltageTypes
from gdm.distribution.equipment.solar_equipment import SolarEquipment
from gdm.distribution.equipment.inverter_equipment import InverterEquipment
from gdm.quantities import ApparentPower, ReactivePower, Irradiance
from infrasys.quantities import ActivePower
from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import parse_phases, phases_without_neutral, sanitize_name, safe_float
from loguru import logger


class GeneratorMapper(SynergiMapper):
    """Maps InstGenerators rows to DistributionSolar.

    All generator types are modelled as solar for now since distributed
    solar is the only DG type in scope. Equipment specs are looked up
    from GeneratorEquipmentMapper-populated SolarEquipment objects.
    """

    synergi_table = "InstGenerators"
    synergi_database = "Model"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        section_id = str(row["SectionId"]).strip()
        section = section_id_sections.get(section_id)
        if section is None:
            return None

        bus = self.map_bus(row, section_id_sections)
        if bus is None:
            return None

        phases = self.map_phases(row, bus)
        if not phases:
            return None

        solar_equip = self.map_equipment(row)
        if solar_equip is None:
            return None

        to_id = str(section.get("ToNodeId", "")).strip()
        feeder, substation = self._lookup_feeder_substation(to_id)

        return DistributionSolar(
            name=self.map_name(row),
            bus=bus,
            phases=phases,
            equipment=solar_equip,
            inverter=self.map_inverter(row, solar_equip),
            irradiance=Irradiance(1000, "watt/meter**2"),
            active_power=self.map_active_power(row, solar_equip),
            reactive_power=ReactivePower(0, "kilovar"),
            controller=None,
            substation=substation,
            feeder=feeder,
        )

    def map_name(self, row):
        device_id = str(row.get("UniqueDeviceId", row["SectionId"])).strip()
        return f"solar_{sanitize_name(device_id)}"

    def map_bus(self, row, section_id_sections):
        section_id = str(row["SectionId"]).strip()
        section = section_id_sections.get(section_id, {})
        to_id = sanitize_name(str(section.get("ToNodeId", "")).strip())
        try:
            return self.system.get_component(DistributionBus, to_id)
        except Exception:
            device_id = str(row.get("UniqueDeviceId", section_id)).strip()
            logger.warning(f"Generator {device_id}: bus {to_id} not found")
            return None

    def map_phases(self, row, bus):
        phases = phases_without_neutral(parse_phases(str(row.get("ConnectedPhases", "ABC"))))
        bus_phases = {p for p in bus.phases if p != Phase.N}
        return [p for p in phases if p in bus_phases]

    def map_equipment(self, row):
        gen_type = str(row.get("GeneratorType", "")).strip()
        equip_name = f"solar_equip_{sanitize_name(gen_type)}"
        try:
            return self.system.get_component(SolarEquipment, equip_name)
        except Exception:
            logger.warning(f"Generator equipment {gen_type!r} not found in system, skipping generator")
            return None

    def map_inverter(self, row, solar_equip):
        device_id = str(row.get("UniqueDeviceId", row["SectionId"])).strip()
        kw_rating = solar_equip.rated_power.to("kilowatt").magnitude
        pf_pct = safe_float(row.get("PQPowerFactorPercentage"), 95) or 95
        kva_rating = kw_rating / (pf_pct / 100.0) if pf_pct > 0 else kw_rating
        return InverterEquipment(
            name=f"inverter_{sanitize_name(device_id)}",
            rated_apparent_power=ApparentPower(kva_rating, "kilova"),
            rise_limit=None,
            fall_limit=None,
            dc_to_ac_efficiency=95.0,
            cutin_percent=5.0,
            cutout_percent=5.0,
            eff_curve=None,
        )

    def map_active_power(self, row, solar_equip):
        kw_rating = solar_equip.rated_power.to("kilowatt").magnitude
        output_pct = safe_float(row.get("OutputPowerPercentage"), 100) or 100
        return ActivePower(kw_rating * output_pct / 100.0, "kilowatt")
