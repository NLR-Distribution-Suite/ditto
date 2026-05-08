from gdm.distribution.equipment import PhaseLoadEquipment, LoadEquipment
from gdm.distribution.components import DistributionBus
from gdm.quantities import ActivePower, ReactivePower
from gdm.distribution.enums import ConnectionType

from ditto.readers.cim_iec_61968_13.cim_mapper import CimMapper
from ditto.readers.cim_iec_61968_13.common import phase_mapper, normalize_phase_tokens


class LoadEquipmentMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row):
        self.phases = self._normalize_phase_tokens(row)

        phases = [phase_mapper[phase] for phase in self.phases]
        bus = self.system.get_component(component_type=DistributionBus, name=row["bus"])

        if row["grounded"] == "false" and len(phases) == 1:
            diff = list(set(bus.phases).difference(phases))
            if diff:
                self.phases.append(sorted(diff, key=lambda phase: phase.value)[0].value)

        return LoadEquipment(
            name=self.map_name(row),
            phase_loads=self.map_phase_loads(row),
            connection_type=self.map_connection_type(row),
        )

    def _normalize_phase_tokens(self, row):
        phase_value = row.get("phase") if hasattr(row, "get") else row["phase"]
        return normalize_phase_tokens(phase_value)

    # NOTE: Names may not be unique. Should we append a number to the name?
    def map_name(self, row):
        return row["load"] + "_equipment"

    # No connection type information is included
    def map_connection_type(self, row):
        return ConnectionType.DELTA if row["conn"] == "D" else ConnectionType.STAR

    def map_phase_loads(self, row):
        phase_loads = []
        n_phases = len(self.phases)
        kw = float(row["active power"]) / n_phases
        kvar = float(row["reactive power"]) / n_phases
        for phase in self.phases:
            if kw > 0:
                mapper = PhaseLoadEquipmentMapper(self.system)
                phase_load = mapper.parse(row, kw, kvar, phase)
                phase_loads.append(phase_load)
        return phase_loads


class PhaseLoadEquipmentMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row, kw, kvar, phase):
        self.kw = kw
        self.kvar = kvar
        return PhaseLoadEquipment(
            name=self.map_name(row, phase),
            real_power=self.map_real_power(kw),
            reactive_power=self.map_reactive_power(kvar),
            z_real=self.map_z_real(row),
            z_imag=self.map_z_imag(row),
            i_real=self.map_i_real(row),
            i_imag=self.map_i_imag(row),
            p_real=self.map_p_real(row),
            p_imag=self.map_p_imag(row),
            num_customers=self.map_num_customers(row),
        )

    def map_name(self, row, phase):
        return row["load"] + "_phase_load_equipment_" + phase

    def map_real_power(self, kw):
        return ActivePower(kw, "watt")

    def map_reactive_power(self, kvar):
        return ReactivePower(kvar, "var")

    def map_z_real(self, row):
        return float(row["z_p"]) / 100.0

    def map_z_imag(self, row):
        return float(row["z_q"]) / 100.0

    def map_i_real(self, row):
        return float(row["i_p"]) / 100.0

    def map_i_imag(self, row):
        return float(row["i_q"]) / 100.0

    def map_p_real(self, row):
        return float(row["p_p"]) / 100.0

    def map_p_imag(self, row):
        return float(row["p_q"]) / 100.0

    def map_num_customers(self, row):
        return None
