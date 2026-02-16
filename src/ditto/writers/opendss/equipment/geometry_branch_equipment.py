from gdm.distribution.equipment import BareConductorEquipment, ConcentricCableEquipment
from gdm.distribution.enums import WireInsulationType
from gdm.distribution import DistributionSystem
from infrasys import Component


from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes


class GeometryBranchEquipmentMapper(OpenDSSMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "LineGeometry_xh"
    altdss_composition_name = "LineGeometry"
    opendss_file = OpenDSSFileTypes.LINECODES_FILE.value

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)

    def map_common(self):
        units = []
        assert len(self.model.horizontal_positions) == len(self.model.vertical_positions)

        for i in range(len(self.model.horizontal_positions)):
            horizontal_position = self.model.horizontal_positions[i]
            vertical_position = self.model.vertical_positions[i]
            x_unit = str(horizontal_position.units)
            h_unit = str(vertical_position.units)
            assert h_unit == x_unit
            if x_unit not in self.length_units_map:
                raise ValueError(f"{x_unit} not mapped for OpenDSS")
            units.append(self.length_units_map[x_unit])
        self.opendss_dict["Units"] = units
        self.opendss_dict["NConds"] = len(self.model.conductors)

    def map_horizontal_positions(self):
        all_x = []
        for horizontal_position in self.model.horizontal_positions:
            all_x.append(horizontal_position.magnitude)
        self.opendss_dict["X"] = all_x

    def map_vertical_positions(self):
        all_h = []
        for vertical_position in self.model.vertical_positions:
            all_h.append(vertical_position.magnitude)
        self.opendss_dict["H"] = all_h

    def map_conductors(self):
        all_conductors = []
        for conductor in self.model.conductors:
            if isinstance(conductor, BareConductorEquipment):
                conductor_type = "wiredata"
            elif isinstance(conductor, ConcentricCableEquipment):
                conductor_type = "cndata"
            #            if isinstance(conductor,TapeShieldCableEqupment):
            #                conductor_type = 'tsdata'
            else:
                raise ValueError(f"Unknown conductor type {conductor}")
            all_conductors.append(f"{conductor_type}.{self.get_opendss_safe_name(conductor.name)}")
        self.opendss_dict["Conductors"] = all_conductors

    def map_insulation(self):
        for conductor in self.model.conductors:
            if isinstance(conductor, BareConductorEquipment):
                self.opendss_dict["EpsR"] = WireInsulationType.AIR.value
            elif isinstance(conductor, ConcentricCableEquipment):
                self.opendss_dict["EpsR"] = WireInsulationType.XLPE.value
            else:
                raise ValueError(f"Unknown conductor type {conductor}")
