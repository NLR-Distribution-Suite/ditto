# CIM IEC 61968-13 Reader

The CIM reader parses an IEC 61968-13 CIM/XML file into a GDM
`DistributionSystem`. It uses [rdflib](https://rdflib.readthedocs.io/) to query
the RDF graph embedded in the XML and maps CIM classes to GDM components.

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
