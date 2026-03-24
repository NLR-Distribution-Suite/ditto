from loguru import logger
from ditto.readers.cyme.cyme_mapper import CymeMapper
from gdm.distribution.equipment.distribution_transformer_equipment import DistributionTransformerEquipment   
from gdm.distribution.equipment.distribution_transformer_equipment import WindingEquipment
from gdm.quantities import ActivePower, ReactivePower, Voltage
from gdm.distribution.common.sequence_pair import SequencePair
from gdm.distribution.enums import ConnectionType, VoltageTypes

class DistributionTransformerThreeWindingEquipmentMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = 'Equipment'
    cyme_section = 'THREE WINDING TRANSFORMER'

    def parse(self, row, network_row):
        
        name = self.map_name(row)
        pct_no_load_loss = self.map_pct_no_load_loss(row)
        pct_full_load_loss = self.map_pct_full_load_loss(row)
        is_center_tapped = self.map_is_center_tapped(row)
        windings = self.map_windings(row, network_row)
        winding_reactances = self.map_winding_reactances(row)
        coupling_sequences = self.map_coupling(row)

        return DistributionTransformerEquipment.model_construct(name=name,
                                                pct_no_load_loss=pct_no_load_loss,
                                                pct_full_load_loss=pct_full_load_loss,
                                                windings=windings,
                                                winding_reactances=winding_reactances,
                                                is_center_tapped=is_center_tapped,
                                                coupling_sequences=coupling_sequences)

    def map_name(self, row):
        name = row['ID']
        return name

    def map_pct_no_load_loss(self, row):
        no_load_loss = float(row['NoLoadLosses'])
        kva = float(row['PrimaryRatedCapacity'])
        pct_no_load_loss = no_load_loss/kva*100
        return pct_no_load_loss

    def map_pct_full_load_loss(self, row):

        I1 = float(row['PrimaryRatedCapacity']) * 1000 / (float(row['PrimaryVoltage']) * 1000) 
        I2 = float(row['SecondaryRatedCapacity']) * 1000 / (float(row['PrimaryVoltage']) * 1000)
        I3 = float(row['TertiaryRatedCapacity']) * 1000 / (float(row['PrimaryVoltage']) * 1000)

        Rpu_12 = float(row['PrimaryToSecondaryZ1']) / 100 / ((1 + float(row['PrimaryToSecondaryXR1'])**2)**0.5)
        Rpu_13 = float(row['PrimaryToTertiaryZ1']) / 100 / ((1 + float(row['PrimaryToTertiaryXR1'])**2)**0.5)
        Rpu_23 = float(row['SecondaryToTertiaryZ1']) / 100 / ((1 + float(row['SecondaryToTertiaryXR1'])**2)**0.5)

        R12 = Rpu_12 * (float(row['PrimaryVoltage'])**2 * 1000) / float(row['PrimaryRatedCapacity'])
        R13 = Rpu_13 * (float(row['PrimaryVoltage'])**2 * 1000) / float(row['PrimaryRatedCapacity'])
        R23 = Rpu_23 * (float(row['PrimaryVoltage'])**2 * 1000) / float(row['PrimaryRatedCapacity'])

        R1 = (R12 + R13 - R23)/2
        R2 = (R12 + R23 - R13)/2
        R3 = (R13 + R23 - R12)/2

        full_load_loss = (I1**2 * R1 + I2**2 * R2 + I3**2 * R3)

        va = float(row['PrimaryRatedCapacity']) * 1000
        pct_full_load_loss = 100 * full_load_loss / va
        return pct_full_load_loss

    def map_winding_reactances(self, row):
        winding_reactances = []
        
        xr_ratio12 = float(row['PrimaryToSecondaryXR1'])
        if xr_ratio12 == 0:
            xr_ratio12 = 0.01
        rx_ratio12 = 1/xr_ratio12
        reactance_pu12 = float(row['PrimaryToSecondaryZ1']) / 100 /((1+rx_ratio12**2)**0.5)
        winding_reactances.append(reactance_pu12)

        xr_ratio13 = float(row['PrimaryToTertiaryXR1'])
        if xr_ratio13 == 0:
            xr_ratio13 = 0.01
        rx_ratio13 = 1/xr_ratio13
        reactance_pu13 = float(row['PrimaryToTertiaryZ1']) / 100 /((1+rx_ratio13**2)**0.5)
        winding_reactances.append(reactance_pu13)

        xr_ratio23 = float(row['SecondaryToTertiaryXR1'])
        if xr_ratio23 == 0:
            xr_ratio23 = 0.01
        rx_ratio23 = 1/xr_ratio23
        reactance_pu23 = float(row['SecondaryToTertiaryZ1']) / 100 /((1+rx_ratio23**2)**0.5)
        winding_reactances.append(reactance_pu23)

        return winding_reactances

    def map_is_center_tapped(self, row):
        return False

    def map_windings(self, row, network_row):
        windings = []

        winding_mapper1 = ThreeWindingEquipmentMapper(self.system)
        winding_1 = winding_mapper1.parse(row, network_row, winding_number=1)
        windings.append(winding_1)

        winding_mapper2 = ThreeWindingEquipmentMapper(self.system)
        winding_2 = winding_mapper2.parse(row, network_row, winding_number=2)
        windings.append(winding_2)

        winding_mapper3 = ThreeWindingEquipmentMapper(self.system)
        winding_3 = winding_mapper3.parse(row, network_row, winding_number=3)
        windings.append(winding_3)

        return windings
    
    def map_coupling(self, row):

        coupling = [SequencePair(0,1),
                    SequencePair(0,2),
                    SequencePair(1,2)]
        return coupling

class ThreeWindingEquipmentMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = 'Equipment'
    cyme_section = 'THREE WINDING TRANSFORMER'
    connection_map = {
                0: 'Yg',
                1: 'Y',
                2: 'Delta',
                3: 'Open Delta',
                4: 'Closed Delta',
                5: 'Zg',
                6: 'CT',
                7: 'Dg',
        }

    def parse(self, row, network_row, winding_number):
        name = self.map_name(row)
        resistance = self.map_resistance(row, winding_number)
        is_grounded = self.map_is_grounded(row, winding_number)
        rated_voltage = self.map_rated_voltage(row, winding_number)
        voltage_type = self.map_voltage_type(row)
        rated_power = self.map_rated_power(row, winding_number)
        num_phases = self.map_num_phases(row)
        connection_type = self.map_connection_type(row, winding_number)
        tap_positions = self.map_tap_positions(row, winding_number, network_row)
        total_taps = self.map_total_taps(row)
        min_tap_pu = self.min_tap_pu(row)
        max_tap_pu = self.max_tap_pu(row)
        return WindingEquipment.model_construct(name=name,
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
                                max_tap_pu=max_tap_pu)

    def map_name(self, row):
        name = row['ID']
        return name

    def map_resistance(self, row, winding_number):

        Rpu_12 = float(row['PrimaryToSecondaryZ1']) / 100 / ((1 + float(row['PrimaryToSecondaryXR1'])**2)**0.5)
        Rpu_13 = float(row['PrimaryToTertiaryZ1']) / 100 / ((1 + float(row['PrimaryToTertiaryXR1'])**2)**0.5)
        Rpu_23 = float(row['SecondaryToTertiaryZ1']) / 100 / ((1 + float(row['SecondaryToTertiaryXR1'])**2)**0.5)

        R12 = Rpu_12 * (float(row['SecondaryVoltage'])**2 * 1000) / float(row['SecondaryRatedCapacity'])
        R13 = Rpu_13 * (float(row['TertiaryVoltage'])**2 * 1000) / float(row['TertiaryRatedCapacity'])
        R23 = Rpu_23 * (float(row['TertiaryVoltage'])**2 * 1000) / float(row['TertiaryRatedCapacity'])


        R1 = max(0.5 * (R12 + R13 - R23), 1e-6)
        R2 = max(0.5 * (R12 + R23 - R13), 1e-6)
        R3 = max(0.5 * (R13 + R23 - R12), 1e-6)

        if winding_number == 1:
            return R1
        elif winding_number == 2:
            return R2
        elif winding_number == 3:
            return R3


    def map_is_grounded(self, row, winding_number):
        
        connection_type = None
        if winding_number == 1:
            connection_type = row['PrimaryConnection']
        elif winding_number == 2:
            connection_type = row['SecondaryConnection']
        elif winding_number == 3:
            connection_type = row['TertiaryConnection']

        winding_type = self.connection_map.get(int(connection_type), 'Y')
        if 'Yg' in winding_type:
            grounded = True
        elif 'Dg' in winding_type:
            grounded = True
        elif 'Zg' in winding_type:
            grounded = True
        else:
            grounded = False
        return grounded

    def map_rated_voltage(self, row, winding_number):

        if winding_number == 1:
            voltage = Voltage(float(row['PrimaryVoltage']), "kilovolt")
        elif winding_number == 2:
            voltage = Voltage(float(row['SecondaryVoltage']), "kilovolt")
        elif winding_number == 3:
            voltage = Voltage(float(row['TertiaryVoltage']), "kilovolt")
    
        return voltage

    def map_voltage_type(self, row):
        return VoltageTypes.LINE_TO_LINE

    def map_rated_power(self, row, winding_number):
        if winding_number == 1:
            power = ActivePower(float(row['PrimaryRatedCapacity']), "kilowatt")
        elif winding_number == 2:
            power = ActivePower(float(row['SecondaryRatedCapacity']), "kilowatt")
        elif winding_number == 3:
            power = ActivePower(float(row['TertiaryRatedCapacity']), "kilowatt")
        return power

    def map_num_phases(self, row):
        num_phases = 3
        return num_phases

    def map_connection_type(self, row, winding_number):

        connection_type = None
        if winding_number == 1:
            connection_type = row['PrimaryConnection']
        elif winding_number == 2:
            connection_type = row['SecondaryConnection']
        elif winding_number == 3:
            connection_type = row['TertiaryConnection']
               
        winding_type = self.connection_map.get(int(connection_type), 'Y')
        if winding_type == 'Open Delta':
            connection_type = 'OPEN_DELTA'
        elif 'Delta' in winding_type:
            connection_type = 'DELTA'
        elif 'Z' in winding_type:
            connection_type = 'ZIG_ZAG'
        elif 'Y' in winding_type:
            connection_type = 'STAR'
        elif 'D' in winding_type:
            connection_type = 'DELTA'
        elif 'CT' == winding_type:
            connection_type = 'STAR'
        else:
            connection_type = 'STAR'

        return ConnectionType(connection_type)

    def map_tap_positions(self, row, winding_number, network_row):

        num_phases = 3
        tap_location = network_row['LTC1_TapLocation']
        if tap_location == '':
            return [0.0 for _ in range(num_phases)]
        if int(tap_location) != winding_number:
            return [0.0 for _ in range(num_phases)]
        

        if network_row is None:
            tap = 0.0
        else:
            tap = network_row['LTC1_InitialTapPosition']
            tap = float(tap) / 100
        tap_positions = []
        for _ in range(1, num_phases + 1):
            tap_positions.append(tap)
        return tap_positions

    def map_total_taps(self, row):
        taps = row['LTC1_NumberOfTaps']
        if taps == '' or taps is None:
            taps = 0
        total_taps = int(taps)
        return total_taps

    def min_tap_pu(self, row):
        min_tap_pu = row['LTC1_MinimumRegulationRange']
        if min_tap_pu == '' or min_tap_pu is None:
            return 0.9
        min_tap_pu = 1 - float(min_tap_pu)/100
        return float(min_tap_pu)

    def max_tap_pu(self, row):
        max_tap_pu = row['LTC1_MaximumRegulationRange']
        if max_tap_pu == '' or max_tap_pu is None:
            return 1.1
        max_tap_pu = 1 + float(max_tap_pu)/100
        return float(max_tap_pu)

