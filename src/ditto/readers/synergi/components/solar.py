from gdm.distribution.components.distribution_solar import DistributionSolar
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.enums import Phase, VoltageTypes
from gdm.distribution.equipment.solar_equipment import SolarEquipment
from gdm.distribution.equipment.inverter_equipment import InverterEquipment
from gdm.quantities import ApparentPower, ReactivePower, Irradiance
from infrasys.quantities import ActivePower, Voltage
from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import parse_phases, phases_without_neutral, sanitize_name, safe_float
from loguru import logger

_PHASE_KEYS = [("Phase1Kw", Phase.A), ("Phase2Kw", Phase.B), ("Phase3Kw", Phase.C)]


class DistributionSolarMapper(SynergiMapper):

    synergi_table = "InstDGens"
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

        inverter_kva = self.map_inverter_kva(row, phases)
        to_id = str(section.get("ToNodeId", "")).strip()
        feeder, substation = self._lookup_feeder_substation(to_id)

        return DistributionSolar(
            name=self.map_name(row),
            bus=bus,
            phases=phases,
            equipment=self.map_equipment(row, bus, phases, inverter_kva),
            inverter=self.map_inverter(row, inverter_kva),
            irradiance=Irradiance(1000, "watt/meter**2"),
            active_power=self.map_active_power(row),
            reactive_power=self.map_reactive_power(row),
            controller=None,
            in_service=self.map_in_service(row),
            substation=substation,
            feeder=feeder,
        )

    def map_name(self, row):
        return f"solar_{sanitize_name(str(row['SectionId']).strip())}"

    def map_bus(self, row, section_id_sections):
        section_id = str(row["SectionId"]).strip()
        section = section_id_sections.get(section_id, {})
        to_id = sanitize_name(str(section.get("ToNodeId", "")).strip())
        try:
            return self.system.get_component(DistributionBus, to_id)
        except Exception:
            logger.warning(f"Solar (DGen) on section {section_id}: bus {to_id} not found")
            return None

    def map_phases(self, row, bus):
        phases = [ph for key, ph in _PHASE_KEYS if safe_float(row.get(key), 0) != 0]
        if not phases:
            phases = [p for p in bus.phases if p != Phase.N]
        bus_phases = {p for p in bus.phases if p != Phase.N}
        return [p for p in phases if p in bus_phases]

    def map_inverter_kva(self, row, phases):
        kva = safe_float(row.get("InvertRat_Kva"), None)
        if not kva or kva <= 0:
            total_kw = sum(safe_float(row.get(k), 0) for k, _ in _PHASE_KEYS)
            kva = max(total_kw, 1.0)
        return kva

    def map_equipment(self, row, bus, phases, inverter_kva):
        section_id = str(row["SectionId"]).strip()
        pct_kw = safe_float(row.get("InvertRat_PctKw"), 100) or 100
        rated_kw = max(inverter_kva * pct_kw / 100.0, 0.001)
        bus_kv = bus.rated_voltage.to("kilovolt").magnitude
        voltage_type = VoltageTypes.LINE_TO_GROUND if len(phases) == 1 else VoltageTypes.LINE_TO_LINE
        return SolarEquipment(
            name=f"solar_equip_{sanitize_name(section_id)}",
            rated_power=ActivePower(rated_kw, "kilowatt"),
            resistance=0.0,
            reactance=0.0,
            rated_voltage=Voltage(bus_kv, "kilovolt"),
            voltage_type=voltage_type,
        )

    def map_inverter(self, row, inverter_kva):
        section_id = str(row["SectionId"]).strip()
        return InverterEquipment(
            name=f"inverter_{sanitize_name(section_id)}",
            rated_apparent_power=ApparentPower(inverter_kva, "kilova"),
            rise_limit=None,
            fall_limit=None,
            dc_to_ac_efficiency=95.0,
            cutin_percent=5.0,
            cutout_percent=5.0,
            eff_curve=None,
        )

    def map_active_power(self, row):
        total_kw = sum(safe_float(row.get(k), 0) for k, _ in _PHASE_KEYS)
        return ActivePower(max(total_kw, 0.0), "kilowatt")

    def map_reactive_power(self, row):
        total_kvar = sum(safe_float(row.get(f"Phase{i}Kvar"), 0) for i in range(1, 4))
        return ReactivePower(total_kvar, "kilovar")

    def map_in_service(self, row):
        # DGenIsOn reflects Synergi dispatch state (often 0 even for installed DGs);
        # treat installed DGs as in-service for power flow studies
        return True
