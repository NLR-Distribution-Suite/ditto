from gdm.quantities import ActivePower, ReactivePower
from gdm.distribution.enums import ConnectionType
from gdm.distribution import DistributionSystem
from infrasys import Component


from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes


class DistributionLoadMapper(OpenDSSMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "Load_kWkvar"
    altdss_composition_name = "Load"
    opendss_file = OpenDSSFileTypes.LOADS_FILE.value

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
        if (
            len(self.model.phases) == 2
            and self.model.equipment.connection_type == ConnectionType.DELTA
        ):
            self.opendss_dict["Phases"] = 1
        else:
            self.opendss_dict["Phases"] = len(self.model.phases)
        # TODO: Do we need to remove neutrals?

    def map_equipment(self):
        # TODO: We're not building equipment for the Loads. This means that there's no guarantee that we're addressing all of the attributes in the equipment in a structured way like we are for the component.
        equipment = self.model.equipment
        connection = self.connection_map[equipment.connection_type]
        self.opendss_dict["Conn"] = connection
        self.opendss_dict["Model"] = 8  # Using ZIP model

        # Solve for the co-efficients of Z, I and P terms summed accross all phases A, B and C:
        # P*a_p = P_{0A} * a_{Ap} + P_{0B} * a_{Bp} + P_{0C} * a_{Cp} = z_real
        # P*b_p = P_{0A} * b_{Ap} + P_{0B} * b_{Bp} + P_{0C} * b_{Cp} = i_real
        # P*c_p = P_{0A} * c_{Ap} + P_{0B} * c_{Bp} + P_{0C} * c_{Cp} = p_real
        # a_p + b_p + c_p = 1
        #
        # Gives:
        # P = z_real + i_real + p_real
        # a_p = z_real/ (z_real + i_real + p_real)
        # b_p = i_real/ (z_real + i_real + p_real)
        # c_p = p_real/ (z_real + i_real + p_real)
        #
        # Similar logic for reactive power.

        z_real = ActivePower(0, "kilowatt")
        i_real = ActivePower(0, "kilowatt")
        p_real = ActivePower(0, "kilowatt")
        z_imag = ReactivePower(0, "kilovar")
        i_imag = ReactivePower(0, "kilovar")
        p_imag = ReactivePower(0, "kilovar")
        for phase_load in equipment.phase_loads:
            z_real += phase_load.real_power * phase_load.z_real
            i_real += phase_load.real_power * phase_load.i_real
            p_real += phase_load.real_power * phase_load.p_real
            z_imag += phase_load.reactive_power * phase_load.z_imag
            i_imag += phase_load.reactive_power * phase_load.i_imag
            p_imag += phase_load.reactive_power * phase_load.p_imag
        z_real = z_real.to("kW")
        i_real = i_real.to("kW")
        p_real = p_real.to("kW")
        z_imag = z_imag.to("kvar")
        i_imag = i_imag.to("kvar")
        p_imag = p_imag.to("kvar")
        p_total = z_real + i_real + p_real
        q_total = z_imag + i_imag + p_imag

        if p_total.magnitude != 0:
            a_p = z_real.magnitude / p_total.magnitude
            b_p = i_real.magnitude / p_total.magnitude
            c_p = p_real.magnitude / p_total.magnitude
        else:
            # Degenerate solution - pick a_p = 1 arbitrarily in P=0 case
            a_p = 1.0
            b_p = 0.0
            c_p = 0.0

        if q_total.magnitude != 0:
            a_q = z_imag.magnitude / q_total.magnitude
            b_q = i_imag.magnitude / q_total.magnitude
            c_q = p_imag.magnitude / q_total.magnitude
        else:
            # Degenerate solution - pick a_q = 1 arbitrarily in Q=0 case
            a_q = 1.0
            b_q = 0.0
            c_q = 0.0

        self.opendss_dict["kW"] = p_total.magnitude
        self.opendss_dict["kvar"] = q_total.magnitude
        # Cut-off voltage set to 0
        self.opendss_dict["ZIPV"] = [a_p, b_p, c_p, a_q, b_q, c_q, 0]
