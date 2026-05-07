from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import sanitize_name
from gdm.distribution.equipment.load_equipment import LoadEquipment
from gdm.distribution.equipment.phase_load_equipment import PhaseLoadEquipment
from gdm.distribution.enums import ConnectionType
from gdm.quantities import ActivePower, ReactivePower

class LoadEquipmentMapper(SynergiMapper):

    synergi_table = "Loads"    
    synergi_database = "Model"

    def parse(self, row, z=1.0, i=0.0, p=0.0):
        name = self.map_name(row)
        phase_loads = self.map_phase_loads(row, z, i, p)
        return LoadEquipment(name=name,
                             phase_loads=phase_loads,
                             connection_type=ConnectionType.STAR)

    def map_name(self, row):
        return sanitize_name(f"load_equip_{row['SectionId']}")

    # No connection type information is included
    def map_connection_type(self, row):
        return ConnectionType.STAR

    def map_phase_loads(self, row, z=1.0, i=0.0, p=0.0):
        phase_loads = []
        for phase in range(1, 4):
            kw = row[f"Phase{phase}Kw"]
            kvar = row[f"Phase{phase}Kvar"]
            customers = row[f"Phase{phase}Customers"]
            if kw != 0 or kvar != 0 or customers > 0:
                mapper = PhaseLoadEquipmentMapper(self.system)
                phase_load = mapper.parse(row, phase, z, i, p)
                phase_loads.append(phase_load)
        return phase_loads

class PhaseLoadEquipmentMapper(SynergiMapper):

    synergi_table = "Loads"    
    synergi_database = "Model"

    def parse(self, row, phase, z=1.0, i=0.0, p=0.0):
        name = self.map_name(row, phase)
        real_power = self.map_real_power(row, phase)
        reactive_power = self.map_reactive_power(row, phase)
        num_customers = self.map_num_customers(row, phase)
        return PhaseLoadEquipment(name=name,
                                  real_power=real_power,
                                  reactive_power=reactive_power,
                                  z_real=z, z_imag=z,
                                  i_real=i, i_imag=i,
                                  p_real=p, p_imag=p,
                                  num_customers=num_customers)

    def map_name(self, row, phase):
        suffix = {1: "A", 2: "B", 3: "C"}[phase]
        return sanitize_name(f"phload_{row['SectionId']}_{suffix}")

    def map_real_power(self, row, phase):
        kw = row[f"Phase{phase}Kw"]
        return ActivePower(kw, 'kilowatt')

    def map_reactive_power(self,row, phase):
        kvar = row[f"Phase{phase}Kvar"]
        return ReactivePower(kvar, 'kilovar')

    def map_num_customers(self, row, phase):
        customers = int(round(row[f"Phase{phase}Customers"]))
        if customers == 0:
            customers = 1
        return customers


