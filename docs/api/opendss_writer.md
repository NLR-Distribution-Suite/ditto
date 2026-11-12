# OpenDSS Writer

The OpenDSS writer exports a GDM `DistributionSystem` to OpenDSS format,
producing a set of `.dss` files that can be loaded directly by OpenDSS.

Distribution generators are written to `Generators.dss` with their power-flow
settings and equipment ratings. Generator load shapes are not preserved by
the OpenDSS reader. Concentric cable dimensions are converted to the units
declared in the output.

## Writer Interface

```{eval-rst}
.. automodule:: ditto.writers.opendss.write
   :members:
   :show-inheritance:
```

## Component Writers

```{eval-rst}
.. automodule:: ditto.writers.opendss.opendss_mapper
   :members:

.. automodule:: ditto.writers.opendss.components.distribution_generator
   :members:
```
