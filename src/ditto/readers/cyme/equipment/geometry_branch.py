from ditto.readers.cyme.cyme_mapper import CymeMapper

class BareConductorElement(CymeMapper):
    def __init__(self, system):
        super().__init__(system)
    cyme_file = 'Equipment'
    cyme_section = 'CABLE'

    def parse(self, row):
        name = self.map_name(row)
        
        return

class GeometryBranch(CymeMapper):
    def __init__(self, system):
        super().__init__(system)
    cyme_file = 'Equipment'
    cyme_section = 'CABLE'
    
    def parse(self, row):
        name = self.map_name(row)
        

