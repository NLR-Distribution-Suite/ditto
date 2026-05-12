from ditto.readers.cyme.cyme_mapper import CymeMapper
from gdm.distribution.equipment.load_equipment import LoadEquipment
from gdm.distribution.equipment.phase_load_equipment import PhaseLoadEquipment
from gdm.quantities import ActivePower, ReactivePower
from gdm.distribution.enums import ConnectionType
from loguru import logger
from ditto.readers.cyme.constants import ModelUnitSystem


class LoadEquipmentMapper(CymeMapper):
    def __init__(self, system, units=ModelUnitSystem):
        super().__init__(system, units=units)

    cyme_file = "Load"
    cyme_section = "LOADS"

    def parse(self, row, network_row):
        name = self.map_name(row)
        # Connection is not included in LOOADS but in CONSUMER LOADS
        connection_type = self.map_connection_type(row)
        phase_loads = self.map_phase_loads(network_row)
        if any(pl is None for pl in phase_loads):
            return None
        return LoadEquipment.model_construct(
            name=name, phase_loads=phase_loads, connection_type=connection_type
        )

    def map_name(self, row):
        return row["DeviceNumber"]

    def map_connection_type(self, row):
        connection_number = int(row["Connection"])
        connection_map = {
            0: ConnectionType.STAR,  # Yg
            1: ConnectionType.STAR,  # Y
            2: ConnectionType.DELTA,  # Delta
            3: ConnectionType.OPEN_DELTA,  # Open Delta
            4: ConnectionType.DELTA,  # Closed Delta
            5: ConnectionType.ZIG_ZAG,  # Zg
            6: ConnectionType.STAR,  # CT
            7: ConnectionType.DELTA,  # Dg - Not sure what this is?
        }
        return connection_map[connection_number]

    def map_phase_loads(self, row):
        # Get the PhaseLoadEquipment with the same name as the Load
        phase_load_equipment_mapper = PhaseLoadEquipmentMapper(self.system)
        phase_load_equipment = phase_load_equipment_mapper.parse(row)
        phase_loads = [phase_load_equipment]
        return phase_loads


class PhaseLoadEquipmentMapper(CymeMapper):
    # CYME customer class definitions (from Load.txt [CUSTOMER CLASS])
    # Maps CustomerType to (P%, I%, Z%) tuple representing ZIP coefficients
    ZIP_MAP = {
        "Z": (0, 0, 1),  # Constant Impedance
        "I": (0, 1, 0),  # Constant Current
        "PQ": (1, 0, 0),  # Constant Power
        "Commercial": (1, 0, 0),
        "Heater": (1, 0, 0),
        "Industrial": (1, 0, 0),
        "Lighting": (1, 0, 0),
        "Other": (1, 0, 0),
        "Power_Electronics": (1, 0, 0),
        "Residential": (1, 0, 0),
        "Rotating_Machine": (1, 0, 0),
    }

    def __init__(self, system, units=ModelUnitSystem):
        super().__init__(system)

    cyme_file = "Load"
    cyme_section = "CUSTOMER LOADS"

    def parse(self, row):
        name = self.map_name(row)
        real_power = self.map_real_power(row)
        reactive_power = self.map_reactive_power(row)
        if real_power == 0 and reactive_power == 0:
            logger.warning(f"Load {name} has 0 kW and 0 kVAR. Skipping...")
            return None
        p_coeff, i_coeff, z_coeff = self.get_zip_coefficients(row)
        return PhaseLoadEquipment(
            name=name,
            real_power=real_power,
            reactive_power=reactive_power,
            z_real=z_coeff,
            z_imag=z_coeff,
            i_real=i_coeff,
            i_imag=i_coeff,
            p_real=p_coeff,
            p_imag=p_coeff,
        )

    def map_name(self, row):
        phase = row["LoadPhase"]
        return row["DeviceNumber"] + "_" + str(phase)

    def compute_powers(self, row):
        v1 = float(row["Value1"])
        v2 = float(row["Value2"])
        kw = None
        kvar = None
        value_type = int(row["ValueType"])
        # kw and kvar
        if value_type == 0:
            kw = v1
            kvar = v2
        # kva and pf
        elif value_type == 1:
            v2 = v2 / 100.0
            kw = v1 * v2
            kvar = v1 * (1 - v2**2) ** 0.5
        # kw and pf
        elif value_type == 2:
            v2 = v2 / 100.0
            kw = v1
            kvar = v1 * (1 / v2**2 - 1) ** 0.5
        # amp and pf
        else:
            pass
        return ActivePower(kw, "kilowatt"), ReactivePower(kvar, "kilovar")

    def map_real_power(self, row):
        kw, kvar = self.compute_powers(row)
        return ActivePower(kw, "kilowatt")

    def map_reactive_power(self, row):
        kw, kvar = self.compute_powers(row)
        return ReactivePower(kvar, "kilovar")

    def get_zip_coefficients(self, row):
        """Get ZIP coefficients (P%, I%, Z%) based on CustomerType."""
        customer_type = row.get("CustomerType", "PQ")
        return self.ZIP_MAP.get(customer_type, (1, 0, 0))
