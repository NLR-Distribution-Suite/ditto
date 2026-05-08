import math

from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import sanitize_name, safe_float
from gdm.quantities import ReactivePower, Reactance
from gdm.distribution.equipment.phase_capacitor_equipment import PhaseCapacitorEquipment
from gdm.distribution.equipment.capacitor_equipment import CapacitorEquipment
from gdm.distribution.enums import ConnectionType, VoltageTypes, Phase
from infrasys.quantities import Resistance, Voltage


class CapacitorEquipmentMapper(SynergiMapper):

    synergi_table = "InstCapacitors"
    synergi_database = "Model"

    def parse(self, row, phases):
        device_id = str(row.get("UniqueDeviceId", row.get("SectionId", ""))).strip()
        safe_did = sanitize_name(device_id)
        return CapacitorEquipment(
            name=f"cap_equip_{safe_did}",
            phase_capacitors=self.map_phase_capacitors(row, phases, safe_did),
            connection_type=self.map_connection_type(row),
            rated_voltage=self.map_rated_voltage(row),
            voltage_type=VoltageTypes.LINE_TO_GROUND,
        )

    def map_connection_type(self, row):
        value = str(row.get("ConnectionType", "YG")).strip()
        return ConnectionType.DELTA if value == "D" else ConnectionType.STAR

    def map_rated_voltage(self, row):
        rated_kvll = safe_float(row.get("RatedKv"), 12.47)
        if rated_kvll <= 0:
            rated_kvll = 12.47
        return Voltage(rated_kvll / math.sqrt(3), "kilovolt")

    def map_phase_capacitors(self, row, phases, safe_did):
        fixed_kvar = {
            Phase.A: safe_float(row.get("FixedKvarPhase1"), 0.0),
            Phase.B: safe_float(row.get("FixedKvarPhase2"), 0.0),
            Phase.C: safe_float(row.get("FixedKvarPhase3"), 0.0),
        }
        # Switched module banks (Module1..3 each add kvar per phase when on)
        modules = [
            (safe_float(row.get("Module1On"), 0.0), safe_float(row.get("Module1KvarPerPhase"), 0.0)),
            (safe_float(row.get("Module2On"), 0.0), safe_float(row.get("Module2KvarPerPhase"), 0.0)),
            (safe_float(row.get("Module3On"), 0.0), safe_float(row.get("Module3KvarPerPhase"), 0.0)),
        ]

        phase_caps = []
        for phase in phases:
            fkvar = fixed_kvar.get(phase, 0.0)
            total_kvar = fkvar
            num_banks = 1 if fkvar > 0 else 0
            num_banks_on = num_banks

            for m_on, m_kvar in modules:
                if m_on and m_kvar > 0:
                    total_kvar += m_kvar
                    num_banks += 1
                    num_banks_on += 1

            if num_banks == 0:
                num_banks = 1
            if total_kvar <= 0:
                total_kvar = 100.0

            phase_caps.append(PhaseCapacitorEquipment(
                name=f"phcap_{safe_did}_{phase.value}",
                resistance=Resistance(0.0, "ohm"),
                reactance=Reactance(0.0, "ohm"),
                rated_reactive_power=ReactivePower(total_kvar, "kilovar"),
                num_banks_on=num_banks_on,
                num_banks=num_banks,
            ))
        return phase_caps
