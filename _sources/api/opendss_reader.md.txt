# OpenDSS Reader

The OpenDSS reader parses an OpenDSS master file (`.dss`) and all referenced
include files into a GDM `DistributionSystem`. It uses
[OpenDSSDirect.py](https://github.com/dss-extensions/OpenDSSDirect.py) to drive
the OpenDSS engine and extract component data.

## Reader Interface

```{eval-rst}
.. automodule:: ditto.readers.opendss.reader
   :members:
   :show-inheritance:
```

## Component Parsers

Each component type is handled by a dedicated module that queries the OpenDSS
engine and maps the results to GDM objects.

```{eval-rst}
.. automodule:: ditto.readers.opendss.components.branches
   :members:

.. automodule:: ditto.readers.opendss.components.buses
   :members:

.. automodule:: ditto.readers.opendss.components.cables
   :members:

.. automodule:: ditto.readers.opendss.components.capacitors
   :members:

.. automodule:: ditto.readers.opendss.components.conductors
   :members:

.. automodule:: ditto.readers.opendss.components.loads
   :members:

.. automodule:: ditto.readers.opendss.components.pv_systems
   :members:

.. automodule:: ditto.readers.opendss.components.transformers
   :members:
```

## Utility Functions

```{eval-rst}
.. automodule:: ditto.readers.opendss.graph_utils
   :members:

.. automodule:: ditto.readers.opendss.common
   :members:
```