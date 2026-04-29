from pathlib import Path

from gdm.distribution import DistributionSystem

from pydantic import ValidationError
from rich.console import Console
from infrasys import Component
from rich.table import Table
import opendssdirect as odd
from loguru import logger

from ditto.readers.opendss.components.conductors import get_conductors_equipment
from ditto.readers.opendss.components.cables import get_cables_equipment
from ditto.readers.opendss.components.sources import get_voltage_sources
from ditto.readers.opendss.components.capacitors import get_capacitors
from ditto.readers.opendss.graph_utils import update_split_phase_nodes
from ditto.readers.opendss.components.pv_systems import get_pvsystems
from ditto.readers.opendss.components.buses import get_buses
from ditto.readers.opendss.components.loads import get_loads
from ditto.readers.opendss.components.transformers import (
    get_transformer_equipments,
    get_transformers,
)
from ditto.readers.opendss.components.branches import (
    get_geometry_branch_equipments,
    get_matrix_branch_equipments,
    get_branches,
)

from ditto.readers.reader import AbstractReader


class Reader(AbstractReader):
    """Class interface for Opendss case file reader"""

    def __init__(
        self,
        Opendss_master_file: Path,
        crs: str | None = None,
        use_split_phase_representation: bool = True,
    ) -> None:
        """Constructor for the Opendss reader

        Args:
            Opendss_master_file (Path): Path to the Opendss master file
            crs (str | None, optional): Coordinate reference system name. Defaults to None.
        """

        self.system = DistributionSystem(auto_add_composed_components=True)
        self.validation_errors: list[list[str]] = []
        self.Opendss_master_file = Path(Opendss_master_file)
        self.crs = crs
        self._read(use_split_phase_representation)

    def _add_components(self, components: list[Component]):
        """Internal method to add components to the system."""

        if components:
            for component in components:
                try:
                    component.__class__.model_validate(component.model_dump())
                except ValidationError as e:
                    for error in e.errors():
                        self.validation_errors.append(
                            [
                                component.name,
                                component.__class__.__name__,
                                error["loc"][0] if error["loc"] else "On model validation",
                                error["type"],
                                error["msg"],
                            ]
                        )

            self.system.add_components(*components)

    def _read(self, use_split_phase_representation: bool = True):
        """Takes the master file path and returns instance of OpendssParser

        Raises:
            FileNotFoundError: Error raised if the file is not found
        """

        logger.debug("Loading OpenDSS model.")
        if not self.Opendss_master_file.exists():
            msg = f"File not found: {self.Opendss_master_file}"
            raise FileNotFoundError(msg)

        odd.Text.Command("Clear")
        odd.Basic.ClearAll()
        odd.Text.Command(f'Redirect "{self.Opendss_master_file}"')
        odd.Text.Command("Solve")
        logger.debug(f"Model loaded from {self.Opendss_master_file}.")

        odd.Solution.Solve()

        self._add_components(get_buses(self.crs))
        self._add_components(get_voltage_sources(self.system))
        self._add_components(get_capacitors(self.system))
        self._add_components(get_loads(self.system))
        self._add_components(get_pvsystems(self.system))
        (
            distribution_transformer_equipment_catalog,
            winding_equipment_catalog,
        ) = get_transformer_equipments(self.system)
        self._add_components(distribution_transformer_equipment_catalog.values())
        self._add_components(
            get_transformers(
                self.system, distribution_transformer_equipment_catalog, winding_equipment_catalog
            )
        )
        self._add_components(get_conductors_equipment())
        self._add_components(get_cables_equipment())
        matrix_branch_equipments_catalog, thermal_limit_catalog = get_matrix_branch_equipments()
        for catalog in matrix_branch_equipments_catalog:
            self._add_components(matrix_branch_equipments_catalog[catalog].values())

        geometry_branch_equipment_catalog, mapped_geometry = get_geometry_branch_equipments(
            self.system
        )
        self._add_components(geometry_branch_equipment_catalog.values())
        branches = get_branches(
            self.system,
            mapped_geometry,
            geometry_branch_equipment_catalog,
            matrix_branch_equipments_catalog,
            thermal_limit_catalog,
        )
        self._add_components(branches)

        logger.debug("parsing complete...")
        logger.debug(f"\n{self.system.info()}")
        logger.debug("Building graph...")
        graph = self.system.get_undirected_graph()
        logger.debug(graph)
        logger.debug("Graph build complete...")
        logger.debug("Updating graph to fix split phase representation...")
        update_split_phase_nodes(graph, self.system)
        logger.debug("System update complete...")
        self._validate_model()

    def get_system(self) -> DistributionSystem:
        """Returns an instance of DistributionSystem

        Returns:
            DistributionSystem: Instance of DistributionSystem
        """

        return self.system

    def _validate_model(self):
        if self.validation_errors:
            error_table = Table(title="Validation warning summary")
            error_table.add_column("Model", justify="right", style="cyan", no_wrap=True)
            error_table.add_column("Type", style="green")
            error_table.add_column("Field", justify="right", style="bright_magenta")
            error_table.add_column("Error", style="bright_red")
            error_table.add_column("Message", justify="right", style="turquoise2")

            for row in self.validation_errors:
                error_table.add_row(*row)

            console = Console()
            console.print(error_table)
            raise Exception(
                "Validation errors occurred when running the script. See the table above"
            )

        ...
