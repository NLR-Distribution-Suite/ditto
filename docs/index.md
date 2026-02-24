# Distribution Transformation Tool (DiTTo)

DiTTo is an open-source *many-to-one-to-many* converter for electrical distribution system models. It reads models from various industry-standard formats, builds a validated intermediate representation using [Grid-Data-Models (GDM)](https://github.com/NLR-Distribution-Suite/grid-data-models), and writes them back to any supported output format.

## Architecture

```{mermaid}
flowchart LR
    A["Source Format\n(OpenDSS, CIM, …)"] -->|Reader| B["GDM\nDistributionSystem"]
    B -->|Writer| C["Target Format\n(OpenDSS, …)"]
    B -->|Serialize| D["JSON on disk"]
```

**Readers** parse source files into GDM components.  
**Writers** export a GDM `DistributionSystem` to a target format.  
The intermediate GDM representation can also be serialised to JSON for inspection or re-use.

## Supported Formats

| Format | Reader | Writer |
|--------|:------:|:------:|
| OpenDSS | ✅ | ✅ |
| CIM IEC 61968-13 | ✅ | ✅ |

## Quick Start

```bash
pip install nrel-ditto
```

```python
from ditto.readers.opendss.reader import Reader

reader = Reader("Master.dss")
system = reader.get_system()
reader.to_json("model.json")
```

See the {doc}`install` and {doc}`usage` pages for full details.

## Contributors

- **Tarek Elgindy**
- **Aadil Latif**
- **Kapil Duwadi**
- **Daniel Thompson**
- **Jeremy Keen**

```{toctree}
:caption: Getting Started
:hidden: true

install.md
```

```{toctree}
:caption: Usage
:hidden: true

usage.md
```

```{toctree}
:caption: API Reference
:hidden: true

reference.md
```

