"""Map a distribution generator to an OpenDSS Generator."""

from ditto.enumerations import OpenDSSFileTypes
from ditto.readers.opendss.components.generators import GENERATOR_MODES
from ditto.writers.opendss.opendss_mapper import OpenDSSMapper


class DistributionGeneratorMapper(OpenDSSMapper):
    altdss_name = "Generator_kWkvar"
    altdss_composition_name = "Generator"
    opendss_file = OpenDSSFileTypes.GENERATORS_FILE.value
    inline_equipment = True

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)

    def map_in_service(self):
        self.opendss_dict["Enabled"] = self.model.in_service

    def map_bus(self):
        self.opendss_dict["Bus1"] = self.get_opendss_safe_name(self.model.bus.name) + "".join(
            self.phase_map[phase] for phase in self.model.phases
        )

    def map_phases(self):
        self.opendss_dict["Phases"] = len(self.model.phases)

    def map_equipment(self):
        equipment = self.model.equipment
        self.opendss_dict.update(
            kVA=equipment.rated_apparent_power.to("kVA").magnitude,
            kV=equipment.rated_voltage.to("kV").magnitude,
            Conn=self.connection_map[equipment.connection_type.value],
            Xd=equipment.synchronous_reactance_pu,
            Xdp=equipment.transient_reactance_pu,
            Xdpp=equipment.subtransient_reactance_pu,
            H=equipment.inertia_seconds,
            D=equipment.damping,
        )

    def map_active_power(self):
        self.opendss_dict["kW"] = self.model.active_power.to("kW").magnitude

    def map_reactive_power(self):
        self.opendss_dict["kvar"] = self.model.reactive_power.to("kvar").magnitude

    def map_operating_mode(self):
        self.opendss_dict["Model"] = next(
            number
            for number, mode in GENERATOR_MODES.items()
            if mode == self.model.operating_mode.value
        )

    def map_voltage_setpoint_pu(self):
        self.opendss_dict["Vpu"] = self.model.voltage_setpoint_pu

    def map_min_voltage_pu(self):
        self.opendss_dict["VMinpu"] = self.model.min_voltage_pu

    def map_max_voltage_pu(self):
        self.opendss_dict["VMaxpu"] = self.model.max_voltage_pu

    def map_min_reactive_power(self):
        self.opendss_dict["Minkvar"] = self.model.min_reactive_power.to("kvar").magnitude

    def map_max_reactive_power(self):
        self.opendss_dict["Maxkvar"] = self.model.max_reactive_power.to("kvar").magnitude
