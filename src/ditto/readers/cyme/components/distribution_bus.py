from infrasys.location import Location
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.enums import VoltageTypes, Phase
from gdm.quantities import Voltage
from ditto.readers.cyme.cyme_mapper import CymeMapper


class DistributionBusMapper(CymeMapper):
    def __init__(self, cyme_model):
        super().__init__(cyme_model)

    cyme_file = "Network"
    cyme_section = "NODE"

    def parse(
        self, row, from_node_sections, to_node_sections, node_feeder_map, node_substation_map
    ):
        name = self.map_name(row)
        feeder = node_feeder_map.get(name, None)
        substation = node_substation_map.get(name, None)

        coordinate = self.map_coordinate(row)
        phases = self.map_phases(row, from_node_sections, to_node_sections)
        rated_voltage = self.map_rated_voltage(row)
        voltage_limits = self.map_voltagelimits(row)
        voltage_type = self.map_voltage_type(row)
        return DistributionBus.model_construct(
            name=name,
            coordinate=coordinate,
            rated_voltage=rated_voltage,
            feeder=feeder,
            substation=substation,
            phases=phases,
            voltagelimits=voltage_limits,
            voltage_type=voltage_type,
        )

    def map_name(self, row):
        name = row["NodeID"]
        return name

    def map_coordinate(self, row):
        x_key = "CoordX" if "CoordX" in row and row["CoordX"] != "" else "CoordX1"
        y_key = "CoordY" if "CoordY" in row and row["CoordY"] != "" else "CoordY1"
        # CRS is not provided in the Cyme data
        return Location(x=float(row[x_key]), y=float(row[y_key]), crs=None)

    def map_rated_voltage(self, row):
        # Placehoder voltage until assign_bus_voltages assigns voltages based on network traversal and transformer ratings
        return Voltage(float(12.47), "kilovolts")

    def map_phases(self, row, from_node_sections, to_node_sections):
        node_id = row["NodeID"]
        all_phases = set()
        if node_id in from_node_sections:
            for section in from_node_sections[node_id]:
                phases = section["Phase"]
                for phase in phases:
                    all_phases.add(phase)
        if node_id in to_node_sections:
            for section in to_node_sections[node_id]:
                phases = section["Phase"]
                for phase in phases:
                    all_phases.add(phase)

        phase_map = {"A": Phase.A, "B": Phase.B, "C": Phase.C, "N": Phase.N}
        return [phase_map[p] for p in sorted(all_phases) if p in phase_map]

    def map_voltagelimits(self, row):
        low_voltage = None
        high_voltage = None
        if row["LowVoltageLimit"] != "":
            low_voltage = Voltage(row["LowVoltageLimit"], "kilovolts")
        if row["HighVoltageLimit"] != "":
            high_voltage = Voltage(row["HighVoltageLimit"], "kilovolts")
        if low_voltage is not None and high_voltage is not None:
            return [low_voltage, high_voltage]
        else:
            return []

    def map_voltage_type(self, row):
        # Defined later in assigne_bus_voltages based on network traversal and transformer ratings
        return VoltageTypes.LINE_TO_LINE
