# Installation

DiTTo requires **Python 3.11 or later**.

## From PyPI

```bash
pip install nrel-ditto
```

This installs DiTTo with its core dependencies (OpenDSS, GDM, rdflib, etc.).

## From Source (Development)

```bash
git clone https://github.com/NREL-Distribution-Suites/ditto.git
cd ditto
pip install -e ".[dev]"
```

## Optional Extras

DiTTo defines optional dependency groups that can be installed as needed:

| Extra | Purpose | Command |
|-------|---------|--------|
| `dev` | Testing & linting (pytest, ruff) | `pip install nrel-ditto[dev]` |
| `doc` | Documentation builds (Sphinx, MyST) | `pip install nrel-ditto[doc]` |

## Verifying the Installation

After installation, verify that the CLI is available:

```bash
ditto_cli --help
```

You can also list the available readers and writers:

```bash
ditto_cli list-readers
ditto_cli list-writers
```
