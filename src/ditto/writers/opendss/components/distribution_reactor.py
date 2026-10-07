from gdm.distribution import DistributionSystem
from gdm.distribution.enums import Phase
from infrasys import Component

from ditto.enumerations import OpenDSSFileTypes
from ditto.writers.opendss.components.distribution_branch import DistributionBranchMapper


class DistributionReactorMapper(DistributionBranchMapper):
    """Emit a GDM DistributionReactor as an OpenDSS Reactor object."""

    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "Reactor"
    altdss_composition_name = None
    opendss_file = OpenDSSFileTypes.REACTORS_FILE.value

    def map_in_service(self):
        self.opendss_dict["Enabled"] = self.model.in_service

    def map_length(self):
        # Reactor impedance is stored directly in the equipment; the branch
        # length is only used to participate in the GDM network graph.
        pass

    def map_phases(self):
        self.opendss_dict["Phases"] = len(
            [phase for phase in self.model.phases if phase != Phase.N]
        )

    def map_equipment(self):
        resistance = self.model.equipment.resistance.to("ohm").magnitude
        reactance = self.model.equipment.reactance.to("ohm").magnitude
        self.opendss_dict["Z"] = complex(resistance, reactance)
