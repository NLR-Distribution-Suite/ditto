# CIM Writer

The CIM writer exports a GDM `DistributionSystem` to CIM IEC 61968-13 XML.

## Supported GDM Components

The writer currently serialises the following component types:

- `DistributionBus`
- `DistributionVoltageSource`
- `DistributionLoad`
- `MatrixImpedanceBranch`
- `DistributionTransformer`
- `DistributionRegulator`
- `DistributionCapacitor`
- `MatrixImpedanceSwitch`
- `DistributionSolar`
- `DistributionBattery`
- `MatrixImpedanceFuse`

## Output Modes

The writer supports two output modes:

- `single`: write one RDF/XML file named `model.xml`
- `package`: write grouped files plus a package `manifest.xml`

In `package` mode, outputs can be separated by:

- substation (`separate_substations=True`)
- feeder (`separate_feeders=True`)
- equipment type (`separate_equipment_types=True`)

## Writer Interface

```{eval-rst}
.. automodule:: ditto.writers.cim_iec_61968_13.write
   :members:
   :show-inheritance:
```
