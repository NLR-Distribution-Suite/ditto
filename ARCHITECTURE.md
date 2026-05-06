# DiTTo Architecture Guide

This document provides a detailed overview of DiTTo's architecture, design patterns, and component structure.

## Table of Contents

- [Overview](#overview)
- [Core Design: Many-to-One-to-Many](#core-design-many-to-one-to-many)
- [Component Architecture](#component-architecture)
- [Readers](#readers)
- [Writers](#writers)
- [Data Flow](#data-flow)
- [Extending DiTTo](#extending-ditto)

## Overview

DiTTo (Distribution Transformation Tool) is designed around a modular, extensible architecture that enables conversion between various distribution system model formats. The core principle is separation of concerns: reading, representation, and writing are handled by distinct, independent modules.

## Core Design: Many-to-One-to-Many

The fundamental architecture pattern in DiTTo is **many-to-one-to-many**:

```
                         ┌──────────────────────────────────────┐
                         │                                      │
    ┌─────────────┐      │   GDM DistributionSystem            │      ┌─────────────┐
    │   OpenDSS   │──┐   │   (Intermediate Representation)     │   ┌──│   OpenDSS   │
    └─────────────┘  │   │                                      │   │  └─────────────┘
    ┌─────────────┐  │   │  ┌────────┐ ┌────────┐ ┌────────┐   │   │  ┌─────────────┐
    │ CIM/IEC     │──┼──▶│  │  Bus   │ │  Load  │ │ Xfmr   │   │──┼──▶│    JSON     │
    └─────────────┘  │   │  └────────┘ └────────┘ └────────┘   │   │  └─────────────┘
    ┌─────────────┐  │   │  ┌────────┐ ┌────────┐ ┌────────┐   │   │  ┌─────────────┐
    │    CYME     │──┘   │  │  PV    │ │  Cap   │ │ Branch │   │   └──│    CYME     │
    └─────────────┘      │  └────────┘ └────────┘ └────────┘   │      └─────────────┘
                         │                                      │
       READERS           └──────────────────────────────────────┘        WRITERS
```

### Benefits of This Design

1. **Modularity**: Each reader/writer is independent; adding a new format doesn't affect existing code
2. **Consistency**: All formats convert to the same intermediate representation
3. **Validation**: Validation logic is centralized in the GDM layer
4. **Extensibility**: New readers and writers can be added without modifying existing ones
5. **Maintainability**: Changes to one format's handling don't ripple through the system

## Component Architecture

### Directory Structure

```
src/ditto/
├── __init__.py              # Package initialization, version
├── enumerations.py          # Shared enumerations (OpenDSSFileTypes)
│
├── readers/                 # Input format parsers
│   ├── reader.py            # AbstractReader base class
│   ├── opendss/             # OpenDSS format reader
│   │   ├── reader.py        # Main reader class
│   │   ├── common/          # Shared utilities
│   │   ├── components/      # Component parsers
│   │   ├── equipment/       # Equipment parsers
│   │   └── controllers/     # Controller parsers
│   ├── cim_iec_61968_13/    # CIM/IEC reader
│   │   ├── reader.py        # Main reader class
│   │   ├── queries.py       # SPARQL queries
│   │   ├── components/      # Component parsers
│   │   ├── equipment/       # Equipment parsers
│   │   └── controllers/     # Controller parsers
│   └── cyme/                # CYME reader (in progress)
│
└── writers/                 # Output format exporters
    ├── abstract_writer.py   # AbstractWriter base class
    └── opendss/             # OpenDSS format writer
        ├── write.py         # Main writer class
        ├── opendss_mapper.py # Mapping utilities
        ├── components/      # Component mappers
        ├── equipment/       # Equipment mappers
        └── controllers/     # Controller mappers
```

### Grid-Data-Models (GDM) Integration

DiTTo uses [Grid-Data-Models](https://github.com/NREL-Distribution-Suites/grid-data-models) as its intermediate representation. The core class is `DistributionSystem`, which serves as a container for all distribution system components.

```python
from gdm import DistributionSystem

# The DistributionSystem holds all components
system = DistributionSystem(name="my_system")

# Components are accessed through typed getters
buses = system.get_buses()
loads = system.get_loads()
transformers = system.get_transformers()
```

## Readers

Readers are responsible for parsing input files and populating a `DistributionSystem` object.

### AbstractReader Base Class

All readers inherit from `AbstractReader`:

```python
from abc import ABC, abstractmethod
from gdm import DistributionSystem

class AbstractReader(ABC):
    """Base class for all DiTTo readers."""

    def __init__(self):
        self.system = DistributionSystem()

    @abstractmethod
    def read(self) -> None:
        """Parse input files and populate self.system."""
        pass

    def get_system(self) -> DistributionSystem:
        """Return the populated distribution system."""
        return self.system
```

### OpenDSS Reader

**Location**: `src/ditto/readers/opendss/`

The OpenDSS reader uses `opendssdirect.py` to interface with the OpenDSS engine:

```python
from ditto.readers.opendss.reader import Reader

reader = Reader(Path("model.dss"))
system = reader.get_system()
```

**Architecture**:
- Uses OpenDSS's COM interface via `opendssdirect`
- Component parsers in `components/` handle specific element types
- Equipment parsers in `equipment/` handle equipment definitions
- Common utilities provide phase mapping, unit conversion

**Component Modules**:
| Module | Purpose |
|--------|---------|
| `buses.py` | Parse bus/node data |
| `branches.py` | Parse line segments |
| `transformers.py` | Parse transformer data |
| `loads.py` | Parse load data |
| `capacitors.py` | Parse capacitor banks |
| `pv_systems.py` | Parse solar/PV systems |
| `storage.py` | Parse energy storage |
| `sources.py` | Parse voltage sources |
| `fuses.py` | Parse fuse elements |
| `loadshapes.py` | Parse time-series profiles |

### CIM/IEC 61968-13 Reader

**Location**: `src/ditto/readers/cim_iec_61968_13/`

The CIM reader parses XML files using RDF graph queries:

```python
from ditto.readers.cim_iec_61968_13.reader import Reader

reader = Reader("model.xml")
reader.read()
system = reader.get_system()
```

**Architecture**:
- Uses `rdflib` for RDF/XML graph parsing
- SPARQL-like queries defined in `queries.py`
- Component mappers convert CIM objects to GDM components

## Writers

Writers export a `DistributionSystem` to a specific output format.

### AbstractWriter Base Class

```python
from abc import ABC, abstractmethod
from pathlib import Path
from gdm import DistributionSystem

class AbstractWriter(ABC):
    """Base class for all DiTTo writers."""

    def __init__(self, system: DistributionSystem):
        self.system = system

    @abstractmethod
    def write(self, output_path: Path, **kwargs) -> None:
        """Write the system to output files."""
        pass
```

### OpenDSS Writer

**Location**: `src/ditto/writers/opendss/`

The OpenDSS writer generates complete DSS model files:

```python
from ditto.writers.opendss.write import Writer

writer = Writer(system)
writer.write(
    output_path=Path("./output"),
    separate_substations=True,
    separate_feeders=True
)
```

**Architecture**:
- Mapper pattern: Each GDM component type has a corresponding mapper
- Uses `altdss_schema` for DSS output validation
- Generates organized file structure

**Output Files Generated**:
```
output/
├── Master.dss           # Main entry point
├── Buses/
│   └── BusCoords.dss    # Bus coordinates
├── Lines.dss            # Line definitions
├── LineCodes.dss        # Line code specifications
├── Transformers.dss     # Transformer definitions
├── Loads.dss            # Load definitions
├── Capacitors.dss       # Capacitor banks
├── Regulators.dss       # Voltage regulators
├── RegControllers.dss   # Regulator controllers
├── Solar.dss            # PV systems
└── LoadShapes.dss       # Time-series profiles
```

**Writer Options**:
| Option | Description |
|--------|-------------|
| `separate_substations` | Organize output by substation |
| `separate_feeders` | Organize output by feeder |

## Data Flow

### Complete Conversion Flow

```
1. INPUT FILE(S)
        │
        ▼
2. READER
   ├── Parse input format
   ├── Create GDM components
   ├── Validate components
   └── Populate DistributionSystem
        │
        ▼
3. GDM DistributionSystem (in memory)
   ├── Buses
   ├── Branches/Lines
   ├── Transformers
   ├── Loads
   ├── Capacitors
   ├── PV Systems
   ├── Storage
   ├── Controllers
   └── Profiles
        │
        ▼
4. WRITER
   ├── Query system components
   ├── Map to output format
   ├── Generate output files
   └── Write to disk
        │
        ▼
5. OUTPUT FILE(S)
```

### Example: OpenDSS to JSON Conversion

```python
from pathlib import Path
from ditto.readers.opendss.reader import Reader

# Step 1-2: Read OpenDSS model
reader = Reader(Path("IEEE13NODE.dss"))

# Step 3: Get GDM DistributionSystem
system = reader.get_system()

# Step 4-5: Write to JSON (built into GDM)
system.to_json(Path("IEEE13NODE.json"), overwrite=True)
```

## Extending DiTTo

### Adding a New Reader

1. Create a new directory under `src/ditto/readers/`
2. Implement a `reader.py` with a class inheriting from `AbstractReader`
3. Implement component parsers as needed

```python
# src/ditto/readers/myformat/reader.py
from ditto.readers.reader import AbstractReader
from gdm import DistributionSystem

class Reader(AbstractReader):
    def __init__(self, input_file):
        super().__init__()
        self.input_file = input_file

    def read(self):
        # Parse your format and populate self.system
        # Create GDM components and add to system
        pass

    def get_system(self) -> DistributionSystem:
        self.read()
        return self.system
```

### Adding a New Writer

1. Create a new directory under `src/ditto/writers/`
2. Implement a `write.py` with a class inheriting from `AbstractWriter`
3. Implement component mappers as needed

```python
# src/ditto/writers/myformat/write.py
from pathlib import Path
from ditto.writers.abstract_writer import AbstractWriter
from gdm import DistributionSystem

class Writer(AbstractWriter):
    def __init__(self, system: DistributionSystem):
        super().__init__(system)

    def write(self, output_path: Path, **kwargs):
        # Convert GDM components to your format
        # Write output files
        pass
```

### Component Mapping Pattern

When implementing readers/writers, use a consistent pattern for component handling:

```python
# Reader pattern: Format-specific -> GDM
def parse_load(self, raw_data) -> Load:
    return Load(
        name=raw_data["name"],
        bus=self.get_bus(raw_data["bus"]),
        phases=self.map_phases(raw_data["phases"]),
        kw=raw_data["kw"],
        kvar=raw_data["kvar"]
    )

# Writer pattern: GDM -> Format-specific
def write_load(self, load: Load) -> str:
    return f"New Load.{load.name} bus={load.bus.name} kW={load.kw} kvar={load.kvar}"
```

## Key Design Decisions

### Why GDM as Intermediate Format?

1. **Standardization**: GDM provides a well-defined, validated component model
2. **Rich Type System**: Pydantic-based validation ensures data integrity
3. **Serialization**: Built-in JSON serialization/deserialization
4. **Extensibility**: GDM is actively maintained with new component types
5. **Shared Ecosystem**: Other NREL tools use GDM, enabling interoperability

### Why Separate Component/Equipment/Controller Directories?

This organization mirrors the logical structure of distribution systems:
- **Components**: Physical network elements (buses, branches, loads)
- **Equipment**: Equipment specifications (line codes, transformer ratings)
- **Controllers**: Control logic (regulator controllers, capacitor controllers)

This separation makes it easier to find and maintain related code.
