from gdm.distribution.components.distribution_battery import DistributionBattery
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.enums import Phase, VoltageTypes
from gdm.distribution.equipment.battery_equipment import BatteryEquipment
from gdm.distribution.equipment.inverter_equipment import InverterEquipment
from gdm.quantities import ApparentPower, ReactivePower, EnergyDC
from infrasys.quantities import ActivePower, Voltage
from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import parse_phases, phases_without_neutral, sanitize_name, safe_float
from loguru import logger

_BATTERY_KW = {"battery", "batt"}


def _is_battery(gen_type: str, gen_equipment: dict) -> bool:
    lower = gen_type.lower()
    if any(kw in lower for kw in _BATTERY_KW):
        return True
    dev = gen_equipment.get(gen_type, {})
    return dev.get("GeneratorType", "").lower() == "battery"


class DistributionBatteryMapper(SynergiMapper):
    """Maps InstGenerators rows classified as batteries to DistributionBattery components."""

    synergi_table = "InstGenerators"
    synergi_database = "Model"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections, gen_equipment=None):
        gen_equipment = gen_equipment or {}
        gen_type = str(row.get("GeneratorType", "")).strip()
        if not _is_battery(gen_type, gen_equipment):
            return None

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

        dev = gen_equipment.get(gen_type, {})
        kw_rating = self.map_kw_rating(dev)
        kv_rating = self.map_kv_rating(dev)
        batt_kwhr = self.map_energy(row, dev)
        eff_dis = self.map_eff_discharge(dev)
        eff_chg = self.map_eff_charge(dev)

        to_id = str(section.get("ToNodeId", "")).strip()
        feeder, substation = self._lookup_feeder_substation(to_id)

        return DistributionBattery(
            name=self.map_name(row),
            bus=bus,
            phases=phases,
            equipment=self.map_equipment(row, kw_rating, kv_rating, batt_kwhr, eff_dis, eff_chg),
            inverter=self.map_inverter(row, kw_rating, eff_dis),
            active_power=self.map_active_power(row, kw_rating),
            reactive_power=ReactivePower(0, "kilovar"),
            controller=None,
            substation=substation,
            feeder=feeder,
        )

    def map_name(self, row):
        device_id = str(row.get("UniqueDeviceId", row["SectionId"])).strip()
        return f"batt_{sanitize_name(device_id)}"

    def map_bus(self, row, section_id_sections):
        section_id = str(row["SectionId"]).strip()
        section = section_id_sections.get(section_id, {})
        to_id = sanitize_name(str(section.get("ToNodeId", "")).strip())
        try:
            return self.system.get_component(DistributionBus, to_id)
        except Exception:
            device_id = str(row.get("UniqueDeviceId", section_id)).strip()
            logger.warning(f"Battery {device_id}: bus {to_id} not found")
            return None

    def map_phases(self, row, bus):
        phases = phases_without_neutral(parse_phases(str(row.get("ConnectedPhases", "ABC"))))
        bus_phases = {p for p in bus.phases if p != Phase.N}
        return [p for p in phases if p in bus_phases]

    def map_kw_rating(self, dev):
        return safe_float(dev.get("KwRating"), 1000) or 1000

    def map_kv_rating(self, dev):
        return safe_float(dev.get("KvRating"), 13.2) or 13.2

    def map_energy(self, row, dev):
        kwhr = safe_float(row.get("BattRatedKwHr"), 0) or 0
        if kwhr <= 0:
            kwhr = safe_float(dev.get("BattRatkWhr"), 4000) or 4000
        return max(kwhr, 1)

    def map_eff_discharge(self, dev):
        return safe_float(dev.get("BattRatPctEffDis"), 84) or 84

    def map_eff_charge(self, dev):
        return safe_float(dev.get("BattRatPctEffChg"), 82) or 82

    def map_equipment(self, row, kw_rating, kv_rating, batt_kwhr, eff_dis, eff_chg):
        device_id = str(row.get("UniqueDeviceId", row["SectionId"])).strip()
        return BatteryEquipment(
            name=f"batt_equip_{sanitize_name(device_id)}",
            rated_energy=EnergyDC(batt_kwhr, "kilowatthour"),
            rated_power=ActivePower(kw_rating, "kilowatt"),
            charging_efficiency=eff_chg,
            discharging_efficiency=eff_dis,
            idling_efficiency=99.0,
            rated_voltage=Voltage(kv_rating, "kilovolt"),
            voltage_type=VoltageTypes.LINE_TO_LINE,
        )

    def map_inverter(self, row, kw_rating, eff_dis):
        device_id = str(row.get("UniqueDeviceId", row["SectionId"])).strip()
        return InverterEquipment(
            name=f"batt_inverter_{sanitize_name(device_id)}",
            rated_apparent_power=ApparentPower(kw_rating, "kilova"),
            rise_limit=None,
            fall_limit=None,
            dc_to_ac_efficiency=eff_dis,
            cutin_percent=5.0,
            cutout_percent=5.0,
            eff_curve=None,
        )

    def map_active_power(self, row, kw_rating):
        output_pct = safe_float(row.get("OutputPowerPercentage"), 100) or 100
        return ActivePower(kw_rating * output_pct / 100.0, "kilowatt")
