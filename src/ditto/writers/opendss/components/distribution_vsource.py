from gdm.distribution.enums import VoltageTypes
from gdm.distribution import DistributionSystem
from infrasys import Component


from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes


class DistributionVoltageSourceMapper(OpenDSSMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "Vsource_Z0Z1Z2"
    altdss_composition_name = "Vsource"
    opendss_file = OpenDSSFileTypes.MASTER_FILE.value

    def map_in_service(self):
        self.opendss_dict["enabled"] = self.model.in_service

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)

        profile_name = self.get_profile_name(self.model)
        if profile_name:
            self.opendss_dict["Yearly"] = profile_name

    def map_bus(self):
        self.opendss_dict["Bus1"] = self.get_opendss_safe_name(self.model.bus.name)
        for phase in self.model.phases:
            self.opendss_dict["Bus1"] += self.phase_map[phase]

    def map_phases(self):
        # Handled in the map_bus function
        self.opendss_dict["Phases"] = len(self.model.phases)
        return

    def map_equipment(self):
        r1 = 0
        x1 = 0
        r0 = 0
        x0 = 0
        voltage = self.model.equipment.sources[0].voltage
        angle = self.model.equipment.sources[0].angle
        num_phases = len(self.model.phases)
        rated_voltage = self.model.bus.rated_voltage

        for phase_source in self.model.equipment.sources:
            r1 += phase_source.r1
            r0 += phase_source.r0
            x1 += phase_source.x1
            x0 += phase_source.x0
            break

        r1 = r1.to("ohm")
        r0 = r0.to("ohm")
        x1 = x1.to("ohm")
        x0 = x0.to("ohm")
        voltage = voltage.to("kilovolt")
        rated_voltage = rated_voltage.to("kilovolt")
        angle = angle.to("degree")

        if self.model.equipment.sources[0].voltage_type == VoltageTypes.LINE_TO_GROUND:
            if num_phases == 1:
                v_mag = voltage.magnitude
            else:
                v_mag = voltage.magnitude * 1.732
        else:
            if num_phases == 1:
                v_mag = voltage.magnitude / 1.732
            else:
                v_mag = voltage.magnitude

        if self.model.bus.voltage_type == VoltageTypes.LINE_TO_GROUND:
            if num_phases == 1:
                v_nom = rated_voltage.magnitude
            else:
                v_nom = rated_voltage.magnitude * 1.732
        else:
            if num_phases == 1:
                v_nom = rated_voltage.magnitude / 1.732
            else:
                v_nom = rated_voltage.magnitude

        self.opendss_dict["Angle"] = angle.magnitude
        self.opendss_dict["pu"] = v_mag / v_nom
        self.opendss_dict["BasekV"] = v_nom
        self.opendss_dict["Z0"] = complex(r0.magnitude, x0.magnitude)
        self.opendss_dict["Z1"] = complex(r1.magnitude, x1.magnitude)
