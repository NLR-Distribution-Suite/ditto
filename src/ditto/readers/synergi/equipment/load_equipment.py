from ditto.readers.synergi.synergi_mapper import SynergiMapper
from gdm.distribution.equipment.load_equipment import LoadEquipment
from gdm.distribution.equipment.phase_load_equipment import PhaseLoadEquipment
from gdm.distribution.enums import ConnectionType
from gdm.quantities import ActivePower, ReactivePower

class LoadEquipmentMapper(SynergiMapper):
    def __init__(self, system):
        super().__init__(system)

    synergi_table = "Loads"    
    synergi_database = "Model"

    def parse(self, row):
        name = self.map_name(row)
        phase_loads = self.map_phase_loads(row)
        return LoadEquipment(name=name,
                             phase_loads=phase_loads)

    #NOTE: Names may not be unique. Should we append a number to the name?
    def map_name(self, row):
        return row['SectionId']

    # No connection type information is included
    def map_connection_type(self, row):
        return ConnectionType.WYE

    def map_phase_loads(self,row):
        phase_loads = []
        for phase in range(1,4):
            if row[f"Phase{phase}Kw"] > 0:
                mapper = PhaseLoadEquipmentMapper(self.system)
                phase_load = mapper.parse(row, phase)
                phase_loads.append(phase_load)
        return phase_loads

class PhaseLoadEquipmentMapper(SynergiMapper):
    def __init__(self, system):
        super().__init__(system)

    synergi_table = "Loads"    
    synergi_database = "Model"

    def parse(self, row, phase):
        name = self.map_name(row, phase)
        real_power = self.map_real_power(row, phase)
        reactive_power = self.map_reactive_power(row, phase)
        z_real = self.map_z_real(row)
        z_imag = self.map_z_imag(row)
        i_real = self.map_i_real(row)
        i_imag = self.map_i_imag(row)
        p_real = self.map_p_real(row)
        p_imag = self.map_p_imag(row)
        num_customers = self.map_num_customers(row, phase)
        return PhaseLoadEquipment(name=name,
                                  real_power=real_power,
                                  reactive_power=reactive_power,
                                  z_real=z_real,
                                  z_imag=z_imag,
                                  i_real=i_real,
                                  i_imag=i_imag,
                                  p_real=p_real,
                                  p_imag=p_imag,
                                  num_customers=num_customers)

    def map_name(self, row, phase):
        if phase == 1:
            return row['SectionId'] + "_A"
        if phase == 2:
            return row['SectionId'] + "_B"
        if phase == 3:
            return row['SectionId'] + "_C"

    def map_real_power(self, row, phase):
        kw = row[f"Phase{phase}Kw"]
        return ActivePower(kw, 'kilowatt')

    def map_reactive_power(self,row, phase):
        kvar = row[f"Phase{phase}Kvar"]
        return ReactivePower(kvar, 'kilovar')

    def map_z_real(self, row):
        return 1

    def map_z_imag(self, row):
        return 1

    def map_i_real(self, row):
        return 0

    def map_i_imag(self, row):
        return 0

    def map_p_real(self, row):
        return 0

    def map_p_imag(self, row):
        return 0

    def map_num_customers(self, row, phase):
        customers = int(round(row[f"Phase{phase}Customers"]))
        if customers == 0:
            customers = 1
        return customers


