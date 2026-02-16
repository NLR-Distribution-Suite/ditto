# Usage

DiTTo converts distribution system models through an intermediate
[Grid-Data-Models (GDM)](https://github.com/NLR-Distribution-Suite/grid-data-models)
representation. Every component is validated by GDM's Pydantic schemas during
parsing, so errors are caught early rather than at simulation time.

The general workflow is:

1. **Read** a source model into a `DistributionSystem`.
2. **Inspect / serialise** the intermediate GDM representation.
3. **Write** the system out to a target format.

## Reading a Model

Each source format has a dedicated `Reader`. The reader parses the source files
and populates a GDM `DistributionSystem`.

```python
from pathlib import Path
from ditto.readers.opendss.reader import Reader

reader = Reader(Path("IEEE13NODE.dss"))
system = reader.get_system()
```

## Serialising to JSON

A parsed system can be exported to a portable JSON file for later use:

```python
export_file = Path("IEEE13NODE.json")
system.to_json(export_file, overwrite=True)

# Or use the reader convenience method:
reader.to_json(export_file)
```

## Deserialising a Saved Model

Previously exported JSON models can be loaded back into memory:

```python
from gdm import DistributionSystem

system = DistributionSystem.from_json(Path("IEEE13NODE.json"))
```

## Writing to a Target Format

The `DistributionSystem` is the basis for all model writers. Pass it to a
`Writer` to produce output files in the desired format:

```python
from ditto.writers.opendss.write import Writer

writer = Writer(system)
writer.write(output_path=Path("output_model"))
```

## End-to-End Conversion

Combining reader and writer for a full format conversion:

```python
from pathlib import Path
from ditto.readers.cim_iec_61968_13.reader import Reader
from ditto.writers.opendss.write import Writer

# Read CIM XML
cim_reader = Reader(Path("IEEE13Nodeckt_CIM100x.xml"))
cim_reader.read()
system = cim_reader.get_system()

# Write OpenDSS
writer = Writer(system)
writer.write(output_path=Path("opendss_output"))
```

## Using the CLI

DiTTo also provides a command-line interface for conversions without writing
Python code:

```bash
# List available readers and writers
ditto_cli list-readers
ditto_cli list-writers

# Convert CIM to OpenDSS
ditto_cli convert \
  --reader cim_iec_61968_13 \
  --writer opendss \
  --input model.xml \
  --output output_dir

# Convert and save intermediate GDM JSON
ditto_cli convert \
  --reader opendss \
  --writer opendss \
  --input Master.dss \
  --output output_dir \
  --save-gdm model.json
```