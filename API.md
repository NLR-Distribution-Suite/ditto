# DiTTo API Reference

This document provides detailed API documentation for DiTTo's readers and writers.

## Table of Contents

- [Readers](#readers)
  - [OpenDSS Reader](#opendss-reader)
  - [CIM/IEC 61968-13 Reader](#cimiec-61968-13-reader)
- [Writers](#writers)
  - [OpenDSS Writer](#opendss-writer)
- [GDM DistributionSystem](#gdm-distributionsystem)
- [Utilities](#utilities)

---

## Readers

### OpenDSS Reader

**Module**: `ditto.readers.opendss.reader`

The OpenDSS reader parses OpenDSS model files and creates a GDM DistributionSystem.

#### Class: `Reader`

```python
from ditto.readers.opendss.reader import Reader
```

##### Constructor

```python
Reader(
    master_file: Path,
    crs: str | None = None
)
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `master_file` | `Path` | Path to the OpenDSS master file (.dss) |
| `crs` | `str \| None` | Coordinate Reference System for bus coordinates (optional) |

##### Methods

###### `get_system() -> DistributionSystem`

Parses the OpenDSS model and returns a populated DistributionSystem.

```python
from pathlib import Path
from ditto.readers.opendss.reader import Reader

reader = Reader(Path("IEEE13NODE.dss"))
system = reader.get_system()
```

**Returns**: `DistributionSystem` - The populated distribution system model

**Raises**:
- `FileNotFoundError` - If the master file doesn't exist
- `ValidationError` - If the model contains invalid components

#### Supported OpenDSS Elements

| Element Type | GDM Component | Notes |
|--------------|---------------|-------|
| `Bus` | `DistributionBus` | Includes coordinates if available |
| `Line` | `DistributionBranch` | With line geometry or matrix impedance |
| `Transformer` | `DistributionTransformer` | Multi-winding support |
| `Load` | `DistributionLoad` | All load models supported |
| `Capacitor` | `DistributionCapacitor` | Shunt capacitors |
| `PVSystem` | `DistributionSolar` | Solar PV systems |
| `Storage` | `DistributionStorage` | Battery storage |
| `Vsource` | `DistributionVoltageSource` | Voltage sources |
| `Fuse` | `MatrixImpedanceFuse` | Fuse elements |
| `RegControl` | `DistributionRegulatorController` | Regulator controls |
| `LoadShape` | `LoadProfile` | Time-series data |

#### Example Usage

```python
from pathlib import Path
from ditto.readers.opendss.reader import Reader

# Basic usage
reader = Reader(Path("path/to/model.dss"))
system = reader.get_system()

# With coordinate reference system
reader = Reader(
    Path("path/to/model.dss"),
    crs="EPSG:4326"
)
system = reader.get_system()

# Access components
for bus in system.get_buses():
    print(f"Bus: {bus.name}")

for load in system.get_loads():
    print(f"Load: {load.name}, kW: {load.kw}")
```

---

### CIM/IEC 61968-13 Reader

**Module**: `ditto.readers.cim_iec_61968_13.reader`

The CIM reader parses CIM/IEC 61968-13 XML files using RDF graph queries.

#### Class: `Reader`

```python
from ditto.readers.cim_iec_61968_13.reader import Reader
```

##### Constructor

```python
Reader(
    cim_file: str | Path
)
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `cim_file` | `str \| Path` | Path to the CIM XML file |

##### Methods

###### `read() -> None`

Parses the CIM XML file and populates the internal DistributionSystem.

```python
reader = Reader("ieee13_cim.xml")
reader.read()
```

###### `get_system() -> DistributionSystem`

Returns the populated DistributionSystem.

```python
system = reader.get_system()
```

**Returns**: `DistributionSystem` - The populated distribution system model

#### Supported CIM Elements

| CIM Element | GDM Component |
|-------------|---------------|
| `TopologicalNode` | `DistributionBus` |
| `PowerTransformer` | `DistributionTransformer` |
| `ACLineSegment` | `DistributionBranch` |
| `EnergyConsumer` | `DistributionLoad` |
| `LinearShuntCompensator` | `DistributionCapacitor` |
| `SynchronousMachine` | `DistributionVoltageSource` |
| `LoadBreakSwitch` | `MatrixImpedanceSwitch` |
| `RatioTapChanger` | `DistributionRegulatorController` |

#### Example Usage

```python
from pathlib import Path
from ditto.readers.cim_iec_61968_13.reader import Reader

# Read CIM file
reader = Reader("path/to/ieee13_cim.xml")
reader.read()
system = reader.get_system()

# Process components
print(f"System name: {system.name}")
print(f"Number of buses: {len(list(system.get_buses()))}")
```

---

## Writers

### OpenDSS Writer

**Module**: `ditto.writers.opendss.write`

The OpenDSS writer exports a DistributionSystem to OpenDSS format files.

#### Class: `Writer`

```python
from ditto.writers.opendss.write import Writer
```

##### Constructor

```python
Writer(
    system: DistributionSystem
)
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `system` | `DistributionSystem` | The distribution system to export |

##### Methods

###### `write(output_path, separate_substations, separate_feeders) -> None`

Writes the distribution system to OpenDSS files.

```python
writer = Writer(system)
writer.write(
    output_path=Path("./output"),
    separate_substations=True,
    separate_feeders=False
)
```

**Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_path` | `Path` | Required | Directory for output files |
| `separate_substations` | `bool` | `False` | Organize by substation |
| `separate_feeders` | `bool` | `False` | Organize by feeder |

#### Output File Structure

When `separate_substations=False` and `separate_feeders=False`:
```
output/
├── Master.dss
├── Buses/
│   └── BusCoords.dss
├── Lines.dss
├── LineCodes.dss
├── Transformers.dss
├── Loads.dss
├── Capacitors.dss
├── Regulators.dss
├── RegControllers.dss
├── Solar.dss
├── Switches.dss
├── SwitchCodes.dss
├── Fuses.dss
├── FuseCodes.dss
├── LoadShapes.dss
├── WireData.dss
└── LineGeometry.dss
```

When `separate_substations=True`:
```
output/
├── Substation_1/
│   ├── Master.dss
│   ├── ...
├── Substation_2/
│   ├── Master.dss
│   ├── ...
```

#### Supported Components

| GDM Component | OpenDSS Element |
|---------------|-----------------|
| `DistributionBus` | Bus coordinates |
| `DistributionBranch` | `Line` |
| `DistributionTransformer` | `Transformer` |
| `DistributionLoad` | `Load` |
| `DistributionCapacitor` | `Capacitor` |
| `DistributionSolar` | `PVSystem` |
| `DistributionVoltageSource` | `Vsource` |
| `DistributionRegulator` | `Transformer` + `RegControl` |
| `MatrixImpedanceBranch` | `Line` with `LineCode` |
| `MatrixImpedanceSwitch` | `Line` (switch mode) |
| `MatrixImpedanceFuse` | `Fuse` |
| `GeometryBranch` | `Line` with `LineGeometry` |
| `SequenceImpedanceBranch` | `Line` with sequence model |

#### Example Usage

```python
from pathlib import Path
from ditto.readers.opendss.reader import Reader
from ditto.writers.opendss.write import Writer

# Read a model
reader = Reader(Path("IEEE13NODE.dss"))
system = reader.get_system()

# Modify the system if needed
# ...

# Write to new location
writer = Writer(system)
writer.write(
    output_path=Path("./modified_model"),
    separate_substations=False,
    separate_feeders=False
)
```

---

## GDM DistributionSystem

The `DistributionSystem` class from Grid-Data-Models is the central data container in DiTTo.

### Import

```python
from gdm import DistributionSystem
```

### Key Methods

#### Serialization

```python
# Save to JSON
system.to_json(Path("model.json"), overwrite=True)

# Load from JSON
system = DistributionSystem.from_json(Path("model.json"))
```

#### Component Access

```python
# Get all components of a type
buses = system.get_buses()
loads = system.get_loads()
transformers = system.get_transformers()
branches = system.get_branches()
capacitors = system.get_capacitors()

# Get component by name
bus = system.get_component_by_name("bus1")

# Get all components
all_components = system.get_components()
```

#### Component Addition

```python
from gdm import DistributionBus, DistributionLoad

# Add a bus
bus = DistributionBus(name="new_bus", ...)
system.add_component(bus)

# Add a load
load = DistributionLoad(name="new_load", bus=bus, ...)
system.add_component(load)
```

---

## Utilities

### Phase Mapping

**Module**: `ditto.readers.opendss.common.phase_mapper`

Maps between OpenDSS phase notation and GDM Phase enum.

```python
from ditto.readers.opendss.common.phase_mapper import map_phases

# OpenDSS phases to GDM
phases = map_phases(".1.2.3")  # Returns [Phase.A, Phase.B, Phase.C]
phases = map_phases(".1.2")    # Returns [Phase.A, Phase.B]
phases = map_phases(".1")      # Returns [Phase.A]
```

### Unit Conversion

**Module**: `ditto.readers.opendss.common.units`

Convert between different length units.

```python
from ditto.readers.opendss.common.units import convert_length

# Convert miles to meters
length_m = convert_length(1.0, "mi", "m")

# Convert feet to kilometers
length_km = convert_length(5280, "ft", "km")
```

### OpenDSS File Types

**Module**: `ditto.enumerations`

Enumeration of standard OpenDSS file names.

```python
from ditto.enumerations import OpenDSSFileTypes

print(OpenDSSFileTypes.MASTER)      # "Master.dss"
print(OpenDSSFileTypes.LINES)       # "Lines.dss"
print(OpenDSSFileTypes.LOADS)       # "Loads.dss"
```

---

## Error Handling

DiTTo uses standard Python exceptions along with validation from Pydantic.

### Common Exceptions

```python
from pydantic import ValidationError

try:
    reader = Reader(Path("model.dss"))
    system = reader.get_system()
except FileNotFoundError:
    print("Model file not found")
except ValidationError as e:
    print(f"Model validation failed: {e}")
except Exception as e:
    print(f"Error reading model: {e}")
```

### Logging

DiTTo uses `loguru` for logging:

```python
from loguru import logger

# Enable debug logging
logger.enable("ditto")

# Disable logging
logger.disable("ditto")
```

---

## Type Hints

DiTTo is fully typed. Use type hints for better IDE support:

```python
from pathlib import Path
from gdm import DistributionSystem
from ditto.readers.opendss.reader import Reader
from ditto.writers.opendss.write import Writer

def convert_model(input_path: Path, output_path: Path) -> DistributionSystem:
    reader: Reader = Reader(input_path)
    system: DistributionSystem = reader.get_system()

    writer: Writer = Writer(system)
    writer.write(output_path)

    return system
```
