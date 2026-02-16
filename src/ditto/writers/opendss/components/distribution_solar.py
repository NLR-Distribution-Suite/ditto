from gdm.distribution.components import DistributionSolar
from gdm.distribution import DistributionSystem


from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes


class DistributionSolarMapper(OpenDSSMapper):
    def __init__(self, model: DistributionSolar, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "PVSystem_kvar"
    altdss_composition_name = "PVSystem"
    opendss_file = OpenDSSFileTypes.SOLAR_FILE.value

    def map_in_service(self):
        self.opendss_dict["enabled"] = self.model.in_service

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)

        profile_name = self.get_profile_name(self.model)
        if profile_name:
            self.opendss_dict["Yearly"] = profile_name

    def map_bus(self):
        num_phases = len(self.model.phases)
        self.opendss_dict["Bus1"] = self.get_opendss_safe_name(self.model.bus.name)
        for phase in self.model.phases:
            self.opendss_dict["Bus1"] += self.phase_map[phase]
        # TODO: Should we include the phases its connected to here?
        nom_voltage = self.model.bus.rated_voltage.to("kV").magnitude
        self.opendss_dict["kV"] = nom_voltage if num_phases == 1 else nom_voltage * 1.732

    def map_phases(self):
        self.opendss_dict["Phases"] = len(self.model.phases)

    def map_irradiance(self):
        self.opendss_dict["Irradiance"] = self.model.irradiance.to("kilowatt / meter**2").magnitude

    def map_active_power(self):
        ...

    def map_reactive_power(self):
        self.opendss_dict["kvar"] = self.model.reactive_power.to("kilovar").magnitude

    def map_controller(self):
        ...

    def map_inverter(self):
        # OpenDSS has a unified representation
        ...

    def map_equipment(self):
        equipment = self.model.equipment
        inverter = self.model.inverter
        self.opendss_dict["Pmpp"] = equipment.rated_power.to("kilowatt").magnitude
        self.opendss_dict["kVA"] = inverter.rated_apparent_power.to("kilova").magnitude
        self.opendss_dict["kvarMaxAbs"] = inverter.rated_apparent_power.to("kilova").magnitude
        self.opendss_dict["pctR"] = equipment.resistance
        self.opendss_dict["pctX"] = equipment.reactance
        self.opendss_dict["pctPmpp"] = inverter.dc_to_ac_efficiency
        self.opendss_dict["pctCutIn"] = inverter.cutin_percent
        self.opendss_dict["pctCutOut"] = inverter.cutout_percent
        if self.model.controller:
            self.opendss_dict["VarFollowInverter"] = self.model.controller.night_mode
            self.opendss_dict["WattPriority"] = self.model.controller.prioritize_active_power
