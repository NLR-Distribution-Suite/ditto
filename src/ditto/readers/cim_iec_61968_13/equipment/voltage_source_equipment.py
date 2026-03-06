from math import pi

from gdm.distribution.equipment import VoltageSourceEquipment, PhaseVoltageSourceEquipment
from gdm.quantities import Resistance, Reactance, Angle, Voltage
from gdm.distribution.enums import VoltageTypes

from ditto.readers.cim_iec_61968_13.cim_mapper import CimMapper


class VoltageSourceEquipmentMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row):
        return VoltageSourceEquipment(
            name=self.map_name(row),
            sources=self.map_sources(row),
        )

    def map_name(self, row):
        return row["source"] + "_equipment"

    def map_sources(self, row):
        return [
            PhaseVoltageSourceEquipmentMapper(self.system).parse(row, phase)
            for phase in ["A", "B", "C"]
        ]


class PhaseVoltageSourceEquipmentMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row, phase):
        return PhaseVoltageSourceEquipment(
            name=self.map_name(row, phase),
            r0=self.map_r0(row),
            r1=self.map_r1(row),
            x0=self.map_x0(row),
            x1=self.map_x1(row),
            voltage=self.map_voltage(row),
            voltage_type=VoltageTypes.LINE_TO_GROUND,
            angle=self.map_angle(row),
        )

    def map_name(self, row, phase):
        return row["source"] + "_phase_voltage_source_equipment_" + phase

    def map_r0(self, row):
        return Resistance(float(row["r0"]), "ohm")

    def map_r1(self, row):
        return Resistance(float(row["r1"]), "ohm")

    def map_x0(self, row):
        return Reactance(float(row["x0"]), "ohm")

    def map_x1(self, row):
        return Reactance(float(row["x1"]), "ohm")

    def map_voltage(self, row):
        return Voltage(float(row["src_voltage"]) / 1.732, "volt")

    def map_angle(self, row):
        return Angle(float(row["src_angle"]) * 180 / pi, "degree")
