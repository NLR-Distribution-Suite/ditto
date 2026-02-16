from gdm.distribution.enums import ConnectionType
from gdm.distribution import DistributionSystem
from infrasys import Component


from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes


class DistributionCapacitorMapper(OpenDSSMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "Capacitor_kvarkV"
    altdss_composition_name = "Capacitor"
    opendss_file = OpenDSSFileTypes.CAPACITORS_FILE.value

    def map_in_service(self):
        self.opendss_dict["enabled"] = self.model.in_service

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)

    def map_bus(self):
        self.opendss_dict["Bus1"] = self.get_opendss_safe_name(self.model.bus.name)
        num_phases = len(self.model.phases)
        for phase in self.model.phases:
            self.opendss_dict["Bus1"] += self.phase_map[phase]
        # TODO: Should we include the phases its connected to here?
        nom_voltage = self.model.bus.rated_voltage.to("kV").magnitude
        self.opendss_dict["kV"] = nom_voltage if num_phases == 1 else nom_voltage * 1.732

    def map_phases(self):
        if (
            len(self.model.phases) == 2
            and self.model.equipment.connection_type == ConnectionType.DELTA
        ):
            self.opendss_dict["Phases"] = 1
        else:
            self.opendss_dict["Phases"] = len(self.model.phases)
        # TODO: Do we need to remove neutrals?

    def map_controllers(self):
        # controller = self.model.controllers
        # TODO: The controller isn't included in the capacitor mapping.
        ...

    def map_equipment(self):
        equipment = self.model.equipment
        connection = self.connection_map[equipment.connection_type]
        self.opendss_dict["Conn"] = connection
        total_resistance = []
        total_reactance = []
        total_rated_reactive_power = []
        # TODO: Note that this sets the NumSteps to be the number of phase capacitors. Is this right? Do we need to check if banked or not?
        num_banks = None
        for phase_capacitor in equipment.phase_capacitors:
            num_banks = phase_capacitor.num_banks
            total_resistance.append(phase_capacitor.resistance.to("ohm").magnitude)
            total_reactance.append(phase_capacitor.reactance.to("ohm").magnitude)
            total_rated_reactive_power.append(
                phase_capacitor.rated_reactive_power.to("kvar").magnitude
            )  # from general capacitor equipment
            self.opendss_dict["States"] = [1] * num_banks
        self.opendss_dict["R"] = [sum(total_resistance) / num_banks] * num_banks
        self.opendss_dict["XL"] = [sum(total_reactance) / num_banks] * num_banks
        total_kvar_per_bank = sum(total_rated_reactive_power) / num_banks
        self.opendss_dict["kvar"] = [total_kvar_per_bank] * num_banks

        # TODO: We're not building equipment for the Capacitors. This means that there's no guarantee that we're addressing all of the attributes in the equipment in a structured way like we are for the component.
