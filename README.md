# DiTTo - Distribution Transformation Tool


[![PyPI version](https://badge.fury.io/py/NREL-ditto.svg)](https://pypi.org/project/NREL-ditto/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD--3--Clause-yellow.svg)](https://opensource.org/license/bsd-3-clause/)
[![codecov](https://codecov.io/gh/NLR-Distribution-Suite/ditto/graph/badge.svg?token=1TSI2L9HNR)](https://codecov.io/gh/NLR-Distribution-Suite/ditto) •  [![Documentation](https://github.com/NLR-Distribution-Suite/ditto/actions/workflows/gh-pages.yml/badge.svg?branch=main)](https://github.com/NLR-Distribution-Suite/ditto/actions/workflows/gh-pages.yml) . [![pages-build-deployment](https://github.com/NLR-Distribution-Suite/ditto/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/NLR-Distribution-Suite/ditto/actions/workflows/pages/pages-build-deployment) . [![Pytest](https://github.com/NLR-Distribution-Suite/ditto/actions/workflows/pull_request_tests.yml/badge.svg)](https://github.com/NLR-Distribution-Suite/ditto/actions/workflows/pull_request_tests.yml) . [![Upload to PyPi](https://github.com/NLR-Distribution-Suite/ditto/actions/workflows/publish_to_pypi.yaml/badge.svg)](https://github.com/NLR-Distribution-Suite/ditto/actions/workflows/publish_to_pypi.yaml) • [![CodeFactor](https://www.codefactor.io/repository/github/nlr-distribution-suite/ditto/badge)](https://www.codefactor.io/repository/github/nlr-distribution-suite/ditto) • ![MCP Server](https://img.shields.io/badge/MCP_Server-enabled-brightgreen) • ![MCP Tools](https://img.shields.io/badge/MCP_Tools-12-blue) • [![PyPI Downloads](https://static.pepy.tech/personalized-badge/nrel-ditto?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/nrel-ditto)

# DiTTo


DiTTo is an open-source tool developed by NREL's Distribution Suites team for converting and modifying electrical distribution system models. It enables seamless conversion between different distribution network formats, with the primary domain being substations to customers.

> **DiTTo is a best-in-class distribution-system model conversion tool, with round-trip validation designed to deliver near-lossless conversion of topology, equipment, and operating behavior.**

## How it Works
Flexible representations for power system components are defined in [Grid-Data-Models (GDM)](https://github.com/NLR-Distribution-Suite/grid-data-models) format. 
DiTTo implements a _many-to-one-to-many_ parsing framework, making it modular and robust. The [reader modules](https://github.com/NLR-Distribution-Suite/ditto/tree/main/src/ditto/readers) parse data files of distribution system format (e.g. OpenDSS) and create an object for each electrical component. These objects are stored in a [GDM DistributionSystem](https://github.com/NLR-Distribution-Suite/grid-data-models/blob/main/src/gdm/distribution/distribution_system.py) instance. The [writer modules](https://github.com/NLR-Distribution-Suite/ditto/tree/main/src/ditto/writers) are then used to export the data stored in memory to a selected output distribution system format (e.g. OpenDSS) which are written to disk.

- **Multi-format Support**: Read and write models from OpenDSS, CIM/IEC 61968-13, and more
- **Robust Architecture**: Many-to-one-to-many parsing framework ensures modularity and extensibility
- **GDM Integration**: Built on [Grid-Data-Models (GDM)](https://github.com/NLR-Distribution-Suite/grid-data-models) for flexible power system component representation
- **Validation**: Thorough model validation during conversion
- **Serialization**: Full JSON serialization/deserialization support for converted models

## OpenDSS Round-Trip Validation

DiTTo uses round-trip comparisons to verify that a model converted through GDM
and written back to OpenDSS preserves electrical behavior. The latest corrected
comparison uses the same deterministic solve policy on both sides: regulator
and capacitor controls disabled, transformer taps fixed at 1.0 pu, and
capacitor banks on.

| Circuit | Source P (pre → post) | Source Q (pre → post) | Total loss kW (pre → post) | Line loss kW (pre → post) | Transformer loss kW (pre → post) | Dashboard Vmin (pre → post) |
|---|---:|---:|---:|---:|---:|---:|
| 123Bus | 3,482.7 → 3,480.9 (-0.050%) | 1,358.1 → 1,357.0 (-0.081%) | 96.73 → 96.62 | 96.73 → 96.61 | 0.0003 → 0.0003 | 0.926538 → 0.926634 |
| 13Bus | 3,400.7 → 3,398.9 (-0.054%) | 1,707.7 → 1,706.4 (-0.077%) | 112.57 → 112.41 | 106.47 → 106.31 | 6.10 → 6.10 | 0.905202 → 0.905286 |
| CKT7 | 76,311.2 → 76,311.2 (~0.000%) | 24,148.6 → 24,148.0 (-0.002%) | 239.07 → 238.22 | 172.17 → 171.30 | 66.91 → 66.92 | 0.813033 → 0.813158 |
| CKT24 | 50,727.1 → 50,758.4 (+0.062%) | 11,498.1 → 11,410.4 (-0.763%) | 1,002.51 → 1,003.83 | 473.19 → 473.97 | 529.32 → 529.87 | 0.863240 → 0.863664 |
| P4U | 2,254.5 → 2,254.6 (+0.004%) | 689.2 → 689.6 (+0.063%) | 172.83 → 172.93 | 21.93 → 21.94 | 150.90 → 150.99 | 0.944773 → 0.944734 |
| SFO | 5,056.4 → 5,056.3 (-0.002%) | 828.3 → 833.2 (+0.589%) | 163.99 → 163.90 | 71.82 → 70.12 | 92.16 → 93.78 | 0.959260 → 0.959116 |
| 8500-Node | 11,232.4 → 11,248.2 (+0.141%) | 1,869.1 → 1,839.3 (-1.598%) | 1,211.72 → 1,219.91 | 1,043.64 → 1,040.20 | 168.08 → 179.71 | 0.785291 → 0.785770 |

The voltage minimums use phase terminals that are actually connected in the
OpenDSS topology. This avoids treating malformed, unserved switch conductors
as energized buses. The complete machine-readable comparison is generated in
`corrected_roundtrip_comparison.csv` by the round-trip validation workflow.

## How It Works

DiTTo implements a **many-to-one-to-many** parsing framework:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   OpenDSS   │     │             │     │   OpenDSS   │
├─────────────┤     │    GDM      │     ├─────────────┤
│  CIM/IEC    │ ──▶ │ Distribution│ ──▶ │   CYME      │
├─────────────┤     │   System    │     ├─────────────┤
│    CYME     │     │             │     │    JSON     │
└─────────────┘     └─────────────┘     └─────────────┘
   READERS          INTERMEDIATE          WRITERS
```

1. **Readers** parse distribution system files and create component objects
2. All components are stored in a **GDM DistributionSystem** instance (intermediate format)
3. **Writers** export the data to the desired output format

## Installation

### From PyPI (Recommended)

```bash
pip install nrel-ditto
```

### From Source

```bash
git clone https://github.com/NREL-Distribution-Suites/ditto.git
cd ditto
pip install -e .
```

### Optional Dependencies

```bash
# For documentation building
pip install nrel-ditto[doc]

# For development (includes pytest, ruff)
pip install nrel-ditto[dev]
```

## Quick Start

### Reading an OpenDSS Model

```python
from pathlib import Path
from ditto.readers.opendss.reader import Reader

# Read an OpenDSS model
opendss_file = Path("path/to/IEEE13NODE.dss")
reader = Reader(opendss_file)
system = reader.get_system()

# Access components
print(f"Loaded {len(list(system.get_buses()))} buses")
```

### Converting CIM to OpenDSS

```python
from pathlib import Path
from ditto.readers.cim_iec_61968_13.reader import Reader
from ditto.writers.opendss.write import Writer

# Read CIM model
cim_reader = Reader("path/to/ieee13_cim.xml")
cim_reader.read()
system = cim_reader.get_system()

# Write to OpenDSS format
writer = Writer(system)
writer.write(
    output_path=Path("./output"),
    separate_substations=False,
    separate_feeders=False
)
```

### Serializing to JSON

```python
from pathlib import Path
from ditto.readers.opendss.reader import Reader

# Read and serialize
reader = Reader(Path("IEEE13NODE.dss"))
system = reader.get_system()
system.to_json(Path("IEEE13NODE.json"), overwrite=True)
```

### Loading from JSON

```python
from pathlib import Path
from gdm import DistributionSystem

# Deserialize a saved model
system = DistributionSystem.from_json(Path("IEEE13NODE.json"))
```

## Supported Formats

### Readers (Input)

| Format | Status | Description |
|--------|--------|-------------|
| OpenDSS | ✅ Complete | Full support for OpenDSS models |
| CIM/IEC 61968-13 | ✅ Complete | Common Information Model support |
| CYME | ✅ Complete | CYME network models |
| Synergi | 🚧 In Progress | Synergi network models |


### Writers (Output)

| Format | Status | Description |
|--------|--------|-------------|
| OpenDSS | ✅ Complete | Full DSS file generation |
| JSON/GDM | ✅ Complete | Serialized GDM format |
| CIM/IEC 61968-13 | ✅ Complete | Common Information Model support |

## Supported Components

DiTTo handles a comprehensive set of distribution system components:

- **Network**: Buses, Lines/Branches, Cables, Conductors
- **Transformers**: Distribution transformers with multiple windings
- **Loads**: Various load types (constant power, impedance, ZIP)
- **Generation**: PV systems, Voltage sources
- **Protection**: Fuses, Regulators with controllers
- **Storage**: Battery/energy storage systems
- **Capacitors**: Shunt capacitors
- **Time-Series**: Load shapes and profiles

## Project Structure

```
ditto/
├── src/ditto/
│   ├── readers/           # Format parsers
│   │   ├── opendss/       # OpenDSS reader
│   │   ├── cim_iec_61968_13/  # CIM reader
│   │   └── cyme/          # CYME reader
│   ├── writers/           # Format exporters
│   │   └── opendss/       # OpenDSS writer
│   └── enumerations.py    # Shared enumerations
├── tests/                 # Test suite
├── docs/                  # Documentation
└── pyproject.toml         # Project configuration
```

## Documentation

- [Architecture Guide](ARCHITECTURE.md) - System design and components
- [API Reference](API.md) - Reader and writer documentation
- [Examples](EXAMPLES.md) - Detailed usage examples
- [Contributing Guide](CONTRIBUTING.md) - How to contribute

## Requirements

- Python 3.10, 3.11, or 3.12
- Dependencies are automatically installed:
  - `grid-data-models` - GDM intermediate representation
  - `opendssdirect.py` - OpenDSS interface
  - `rdflib` - RDF/XML parsing for CIM
  - `NREL-altdss-schema` - DSS output schema

## Contributing

DiTTo is an open-source project and contributions are welcome! Whether it's a typo fix, bug report, or a new parser, we appreciate your help.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Submit a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/NLR-Distribution-Suite/ditto/issues)
- **Questions**: Contact [Tarek Elgindy](mailto:tarek.elgindy@nrel.gov)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

DiTTo is developed and maintained by the [NREL Distribution Suites](https://github.com/NLR-Distribution-Suite) team at the National Renewable Energy Laboratory.
