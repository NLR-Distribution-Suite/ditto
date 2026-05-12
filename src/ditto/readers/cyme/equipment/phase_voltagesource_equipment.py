from ditto.readers.cyme.cyme_mapper import CymeMapper
from ditto.constants import LL_LN_CONVERSION_FACTOR
from gdm.distribution.equipment.phase_voltagesource_equipment import PhaseVoltageSourceEquipment
from gdm.quantities import Angle, Reactance, Resistance
from gdm.distribution.enums import VoltageTypes
from gdm.quantities import Voltage
from ditto.readers.cyme.constants import ModelUnitSystem


class PhaseVoltageSourceEquipmentMapper(CymeMapper):
    def __init__(self, system, units=ModelUnitSystem):
        super().__init__(system, units=units)

    def parse(self, bus, source_voltage, source_voltage_type):
        sources = []
        num_phases = len(bus.phases)
        # Per-phase source equipment in GDM should use line-to-ground values.
        # DesiredVoltage is modeled as L-L for multi-phase sources.
        # OperatingVoltageA/B/C are per-phase and already L-N.
        phase_voltage = source_voltage
        if source_voltage_type == VoltageTypes.LINE_TO_LINE and num_phases > 1:
            phase_voltage = source_voltage / LL_LN_CONVERSION_FACTOR
        for i in range(num_phases):
            source = PhaseVoltageSourceEquipment.model_construct(
                name=f"{bus.name}-phase-source-{i + 1}",
                r0=Resistance(0.001, "ohm"),
                r1=Resistance(0.001, "ohm"),
                x0=Reactance(0.001, "ohm"),
                x1=Reactance(0.001, "ohm"),
                voltage=Voltage(phase_voltage, "kilovolt"),
                voltage_type=VoltageTypes.LINE_TO_GROUND,
                angle=Angle(i * (360.0 / num_phases), "degree"),
            )
            sources.append(source)
        return sources
