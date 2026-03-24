from ditto.readers.cyme.cyme_mapper import CymeMapper
from gdm.distribution.equipment.distribution_transformer_equipment import (
    DistributionTransformerEquipment,
)
from gdm.distribution.equipment.distribution_transformer_equipment import WindingEquipment
from gdm.quantities import ActivePower, Voltage
from gdm.distribution.common.sequence_pair import SequencePair
from gdm.distribution.enums import ConnectionType, VoltageTypes


class DistributionTransformerEquipmentMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = "Equipment"
    cyme_section = "TRANSFORMER"

    def parse(self, row, network_row, phase):
        name = self.map_name(row)
        pct_no_load_loss = self.map_pct_no_load_loss(row)
        pct_full_load_loss = self.map_pct_full_load_loss(row)
        is_center_tapped = self.map_is_center_tapped(row)
        windings = self.map_windings(row, network_row, is_center_tapped, phase)
        winding_reactances = self.map_winding_reactances(row, is_center_tapped)
        coupling_sequences = self.map_coupling(row, is_center_tapped)

        return DistributionTransformerEquipment.model_construct(
            name=name,
            pct_no_load_loss=pct_no_load_loss,
            pct_full_load_loss=pct_full_load_loss,
            windings=windings,
            winding_reactances=winding_reactances,
            is_center_tapped=is_center_tapped,
            coupling_sequences=coupling_sequences,
        )

    def map_name(self, row):
        name = row["ID"]
        return name

    def map_pct_no_load_loss(self, row):
        no_load_loss = float(row["NoLoadLosses"])
        kva = float(row["KVA"])
        pct_no_load_loss = no_load_loss / kva * 100
        return pct_no_load_loss

    def map_pct_full_load_loss(self, row):
        # Need to compute rated current and rated resistance to compute full load loss
        rated_current_sec = float(row["KVA"]) * 1000 / (float(row["KVLLsec"]) * 1000)
        resistance_pu = float(row["Z1"]) / 100 / ((1 + float(row["XR"]) ** 2) ** 0.5)
        resistance_sec = resistance_pu * (float(row["KVLLsec"]) ** 2 * 1000) / float(row["KVA"])

        full_load_loss = rated_current_sec**2 * resistance_sec
        pct_full_load_loss = 100 * full_load_loss / (float(row["KVA"]) * 1000)
        return pct_full_load_loss

    def map_winding_reactances(self, row, is_center_tapped):
        xr_ratio = float(row["XR"])
        if xr_ratio == 0:
            xr_ratio = 0.01
        rx_ratio = 1 / xr_ratio
        reactance_pu = float(row["Z1"]) / 100 / ((1 + rx_ratio**2) ** 0.5)
        if is_center_tapped:
            winding_reactances = [reactance_pu * 100, reactance_pu * 100, reactance_pu * 100]
        else:
            winding_reactances = [reactance_pu * 100]
        return winding_reactances

    def map_is_center_tapped(self, row):
        # TODO Center tapped/Split phase not supported
        # This will assign it properly but handling of buses needs to be developed
        # transformer_type = row["Type"]
        # if transformer_type == '4':
        #    return True

        return False

    def map_windings(self, row, network_row, is_center_tapped, phase):
        windings = []

        winding_mapper1 = WindingEquipmentMapper(self.system)
        winding_1 = winding_mapper1.parse(row, network_row, winding_number=1, phase=phase)
        winding_mapper2 = WindingEquipmentMapper(self.system)
        winding_2 = winding_mapper2.parse(row, network_row, winding_number=2, phase=phase)
        windings.append(winding_1)
        windings.append(winding_2)
        if is_center_tapped:
            winding_mapper3 = WindingEquipmentMapper(self.system)
            winding_3 = winding_mapper3.parse(row, network_row, winding_number=3, phase=phase)
            windings.append(winding_3)
        return windings

    def map_coupling(self, row, is_center_tapped):
        if is_center_tapped:
            coupling = [SequencePair(0, 1), SequencePair(0, 2), SequencePair(1, 2)]
        else:
            coupling = [SequencePair(0, 1)]
        return coupling


class WindingEquipmentMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = "Equipment"
    cyme_section = "TRANSFORMER"

    """
    connection_map = {
        0: "Y_Y",
        1: "D_Y",
        2: "D_Y",
        3: "YNG_YNG",
        4: "D_D",
        5: "DO_DO",
        6: "YO_DO",
        7: "D_YNG",
        8: "YNG_D",
        9: "Y_YNG",
        10: "YNG_Y",
        11: "Yg_Zg",
        12: "D_Zg",
    }
    """

    # The documentation is confusing on where the below connection types are used
    # It appears they are used in the equipment file although it is reported in the network file
    # Including the above map incase this is incorrect but the below map appears to be correct based on testing with CYME data
    connection_map = {
        0: "Yg_Yg",
        1: "D_Yg",
        2: "D_D",
        3: "Y_Y",
        4: "DO_DO",
        5: "YO_D",
        6: "Yg_D",
        7: "D_Y",
        8: "Y_D",
        9: "Yg_Y",
        10: "Y_Yg",
        11: "Yg_Zg",
        12: "D_Zg",
        13: "Zg_Yg",
        14: "Zg_D",
        15: "Yg_CT",
        16: "D_CT",
        17: "Yg_DCT",
        18: "D_DCT",
        19: "Y_DCT",
        20: "DO_DOCT",
        21: "YO_DOCT",
        22: "DO_YO",
        23: "Yg_Dn",
        24: "Y_Dn",
        25: "D_Dn",
        26: "Zg_Dn",
        27: "Dn_Yg",
        28: "Dn_Y",
        29: "Dn_D",
        30: "Dn_Dn",
        31: "Dn_Zg",
        99: "Equip_Connection",
    }

    def parse(self, row, network_row, winding_number, phase):
        name = self.map_name(row)
        resistance = self.map_resistance(row, winding_number)
        is_grounded = self.map_is_grounded(row, winding_number)
        rated_voltage = self.map_rated_voltage(row, winding_number)
        voltage_type = self.map_voltage_type(row, rated_voltage)
        rated_power = self.map_rated_power(row)
        num_phases = self.map_num_phases(phase)
        connection_type = self.map_connection_type(row, winding_number)
        tap_positions = self.map_tap_positions(row, winding_number, network_row, phase)
        total_taps = self.map_total_taps(row)
        min_tap_pu = self.min_tap_pu(row)
        max_tap_pu = self.max_tap_pu(row)
        return WindingEquipment.model_construct(
            name=name,
            resistance=resistance,
            is_grounded=is_grounded,
            rated_voltage=rated_voltage,
            voltage_type=voltage_type,
            rated_power=rated_power,
            num_phases=num_phases,
            connection_type=connection_type,
            tap_positions=tap_positions,
            total_taps=total_taps,
            min_tap_pu=min_tap_pu,
            max_tap_pu=max_tap_pu,
        )

    def map_name(self, row):
        name = row["ID"]
        return name

    def map_resistance(self, row, winding_number):
        xr_ratio = float(row["XR"])
        resistance_pu = float(row["Z1"]) / 100 / ((1 + xr_ratio**2) ** 0.5)
        return resistance_pu * 100

    def map_is_grounded(self, row, winding_number):
        connection_type = row["Conn"]
        if winding_number == 1:
            winding = 0
        elif winding_number == 2:
            winding = 1
        elif winding_number == 3:
            winding = 1
        if isinstance(connection_type, int) or (
            isinstance(connection_type, str) and connection_type.isdigit()
        ):
            conn_type_int = int(connection_type)
            winding_type = self.connection_map.get(conn_type_int, "Y_Y").split("_")[winding]
        else:
            winding_type = str(connection_type)

        if "YNG" in winding_type:
            grounded = False
        elif "D" in winding_type:
            grounded = False
        elif "YO" in winding_type:
            grounded = False
        else:
            grounded = True
        return grounded

    def map_rated_voltage(self, row, winding_number):
        if winding_number == 1:
            voltage = row["KVLLprim"]
        elif winding_number == 2:
            voltage = row["KVLLsec"]
        elif winding_number == 3:
            voltage = row["KVLLsec"]

        voltage = Voltage(float(voltage), "kilovolt")
        return voltage

    def map_voltage_type(self, row, rated_voltage):
        # This is from the CYME documentation but appears to not be entirely correct
        # Clearly L-L voltages still appear with a voltage type of 1
        if "VoltageUnit" in row and (row["VoltageUnit"] == "1" or row["VoltageUnit"] == "3"):
            return VoltageTypes.LINE_TO_GROUND
        return VoltageTypes.LINE_TO_LINE

    def map_rated_power(self, row):
        power = row["KVA"]
        power = ActivePower(float(power), "kilowatt")
        return power

    def map_num_phases(self, phase):
        num_phases = len(phase)
        return num_phases

    def map_connection_type(self, row, winding_number):
        connection_type = row["Conn"]
        if winding_number == 1:
            winding = 0
        elif winding_number == 2 or winding_number == 3:
            winding = 1

        if isinstance(connection_type, int) or (
            isinstance(connection_type, str) and connection_type.isdigit()
        ):
            conn_type_int = int(connection_type)
            winding_type = self.connection_map.get(conn_type_int, "Y_Y").split("_")[winding]
        else:
            winding_type = str(connection_type)

        winding_connection_map = {
            "YO": "OPEN_STAR",
            "DO": "OPEN_DELTA",
            "DCT": "DELTA",
            "CT": "STAR",
        }

        if winding_type in winding_connection_map:
            connection_type = winding_connection_map[winding_type]
        elif "Z" in winding_type:
            connection_type = "ZIG_ZAG"
        elif "Y" in winding_type:
            connection_type = "STAR"
        elif "D" in winding_type:
            connection_type = "DELTA"
        else:
            connection_type = "STAR"

        return ConnectionType(connection_type)

    def map_tap_positions(self, row, winding_number, network_row, phase):
        num_phases = len(phase)

        tap_positions = []
        if winding_number == 1:
            if network_row is None:
                tap = 1.0
            else:
                tap = network_row.get("PrimTap", None)
                if tap is None:
                    tap = network_row.get("PrimaryTapSettingA", 100)
                tap = float(tap) / 100

        elif winding_number == 2 or winding_number == 3:
            if network_row is None:
                tap = 1.0
            else:
                tap = network_row.get("SecTap", None)
                if tap is None:
                    tap = network_row.get("SecondaryTapSettingA", 100)
                tap = float(tap) / 100

        if row["Taps"] == "" or row["Taps"] is None:
            tap = 1.0
        for phase in range(1, num_phases + 1):
            tap_positions.append(tap)
        return tap_positions

    def map_total_taps(self, row):
        taps = row["Taps"]
        if taps == "" or taps is None:
            taps = 32
        total_taps = int(taps)
        return total_taps

    def min_tap_pu(self, row):
        min_tap_pu = row["MinReg_Range"]
        if min_tap_pu == "" or min_tap_pu is None:
            return 0.9
        min_tap_pu = 1 - float(min_tap_pu) / 100
        return float(min_tap_pu)

    def max_tap_pu(self, row):
        max_tap_pu = row["MaxReg_Range"]
        if max_tap_pu == "" or max_tap_pu is None:
            return 1.1
        max_tap_pu = 1 + float(max_tap_pu) / 100
        return float(max_tap_pu)
