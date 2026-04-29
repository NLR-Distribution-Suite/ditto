"""Base reader interface for distribution system model converters.

Ditto converts distribution system models from various source formats
(e.g., OpenDSS, CIM IEC 61968-13) into a common GDM ``DistributionSystem``
representation. Each source format implements a concrete ``Reader`` that
inherits from :class:`AbstractReader`.

Typical workflow::

    from ditto.readers.opendss import Reader

    reader = Reader("Master.dss")
    system = reader.get_system()
    reader.to_json("model.json")
"""

from abc import ABC, abstractmethod
from pathlib import Path

from loguru import logger

from infrasys.system import System


class AbstractReader(ABC):
    """Base class for all Ditto readers.

    Subclasses must implement :meth:`get_system` to parse a source model
    and return a fully-populated ``infrasys.System`` instance (typically a
    ``gdm.distribution.DistributionSystem``).

    The shared :meth:`to_json` helper serialises the resulting system to a
    JSON file, providing a convenient one-step export after parsing.
    """

    @abstractmethod
    def get_system(self) -> System:
        """Parse the source model and return the built system.

        Returns:
            System: A fully-populated ``infrasys.System`` (or subclass)
                containing all parsed distribution components.
        """
        ...

    def to_json(self, json_file: Path | str) -> None:
        """Serialise the parsed system to a JSON file.

        This is a convenience wrapper around ``System.to_json`` that
        validates the system has been built before attempting export.

        Args:
            json_file: Destination path for the exported GDM model.
                Parent directories must already exist.

        Raises:
            AttributeError: If the system has not been built yet.
                Call the reader's constructor or ``read()`` method first.
        """
        if not hasattr(self, "system"):
            raise AttributeError(
                "System has not been built yet. "
                "Ensure the reader's constructor or read() method has been called first."
            )
        json_file = Path(json_file)
        self.system.to_json(json_file, overwrite=True)
        logger.info(f"GDM model exported to {json_file}")
