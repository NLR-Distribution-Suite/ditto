# CIM IEC 61968-13 Reader

The CIM reader parses an IEC 61968-13 CIM/XML file into a GDM
`DistributionSystem`. It uses [rdflib](https://rdflib.readthedocs.io/) to query
the RDF graph embedded in the XML and maps CIM classes to GDM components.

## Parsed Component Coverage

The reader currently maps CIM data into these primary GDM components:

- `DistributionBus`
- `DistributionLoad`
- `DistributionCapacitor`
- `DistributionVoltageSource`
- `DistributionBattery`
- `MatrixImpedanceBranch`
- `DistributionTransformer`
- `DistributionRegulator`
- `MatrixImpedanceSwitch`

Battery support is provided through CIM `BatteryUnit` and
`PowerElectronicsConnection` data.

## Reader Interface

```{eval-rst}
.. automodule:: ditto.readers.cim_iec_61968_13.reader
   :members:
   :show-inheritance:
```

## SPARQL Queries

```{eval-rst}
.. automodule:: ditto.readers.cim_iec_61968_13.queries
   :members:
```

## CIM-to-GDM Mapper

```{eval-rst}
.. automodule:: ditto.readers.cim_iec_61968_13.cim_mapper
   :members:
```

## Utility Functions

```{eval-rst}
.. automodule:: ditto.readers.cim_iec_61968_13.common
   :members:

.. automodule:: ditto.readers.cim_iec_61968_13.length_units
   :members:
```
