from gdm.distribution.components.distribution_battery import DistributionBattery
from gdm.distribution import DistributionSystem

from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes


class DistributionBatteryMapper(OpenDSSMapper):
    def __init__(self, model: DistributionBattery, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "Storage_kWRatedkvar"
    altdss_composition_name = "Storage"
    opendss_file = OpenDSSFileTypes.STORAGE_FILE.value

    def map_in_service(self):
        self.opendss_dict["Enabled"] = self.model.in_service

    def map_name(self):
        self.opendss_dict["Name"] = self.model.name

        profile_name = self.get_profile_name(self.model)
        if profile_name:
            self.opendss_dict["Yearly"] = profile_name

    def map_bus(self):
        num_phases = len(self.model.phases)
        self.opendss_dict["Bus1"] = self.model.bus.name
        for phase in self.model.phases:
            self.opendss_dict["Bus1"] += self.phase_map[phase]
        nom_voltage = self.model.bus.rated_voltage.to("kV").magnitude
        self.opendss_dict["kV"] = nom_voltage if num_phases == 1 else nom_voltage * 1.732

    def map_phases(self):
        self.opendss_dict["Phases"] = len(self.model.phases)

    def map_active_power(self):
        ...

    def map_reactive_power(self):
        self.opendss_dict["kvar"] = self.model.reactive_power.to("kilovar").magnitude

    def map_controller(self):
        ...

    def map_inverter(self):
        # OpenDSS has a unified Storage representation
        ...

    def map_equipment(self):
        equipment = self.model.equipment
        inverter = self.model.inverter
        self.opendss_dict["kWRated"] = equipment.rated_power.to("kilowatt").magnitude
        self.opendss_dict["kWhRated"] = equipment.rated_energy.to("kilowatthour").magnitude
        self.opendss_dict["kVA"] = inverter.rated_apparent_power.to("kilova").magnitude
        self.opendss_dict["pctEffCharge"] = equipment.charging_efficiency
        self.opendss_dict["pctEffDischarge"] = equipment.discharging_efficiency
        self.opendss_dict["pctIdlingkW"] = 100.0 - equipment.idling_efficiency
        self.opendss_dict["pctCutIn"] = inverter.cutin_percent
        self.opendss_dict["pctCutOut"] = inverter.cutout_percent
        if self.model.controller:
            self.opendss_dict["VarFollowInverter"] = self.model.controller.night_mode
            self.opendss_dict["WattPriority"] = self.model.controller.prioritize_active_power
