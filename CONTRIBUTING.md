# Contributing to DiTTo

Thank you for your interest in contributing to DiTTo! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Adding New Readers/Writers](#adding-new-readerswriters)

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all experience levels.

## Getting Started

### Types of Contributions

We welcome many types of contributions:

- **Bug fixes**: Found a bug? Submit a fix!
- **Documentation**: Improve or add documentation
- **New features**: Add new functionality
- **New readers/writers**: Add support for new distribution system formats
- **Tests**: Improve test coverage
- **Code quality**: Refactoring and code improvements

### Finding Issues

- Check the [GitHub Issues](https://github.com/NREL-Distribution-Suites/ditto/issues) for open issues
- Look for issues labeled `good first issue` for beginner-friendly tasks
- Feel free to ask questions on any issue

## Development Setup

### Prerequisites

- Python 3.10, 3.11, or 3.12
- Git
- A virtual environment tool (venv, conda, etc.)

### Setup Steps

1. **Fork the repository**

   Click the "Fork" button on the [DiTTo GitHub page](https://github.com/NREL-Distribution-Suites/ditto)

2. **Clone your fork**

   ```bash
   git clone https://github.com/YOUR_USERNAME/ditto.git
   cd ditto
   ```

3. **Create a virtual environment**

   ```bash
   # Using venv
   python -m venv venv

   # Activate on Windows
   venv\Scripts\activate

   # Activate on macOS/Linux
   source venv/bin/activate
   ```

4. **Install development dependencies**

   ```bash
   pip install -e ".[dev]"
   ```

5. **Install pre-commit hooks**

   ```bash
   pip install pre-commit
   pre-commit install
   ```

6. **Verify setup**

   ```bash
   pytest
   ```

## Making Changes

### Branch Workflow

1. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

   Use descriptive branch names:
   - `feature/add-cyme-writer`
   - `fix/transformer-phase-mapping`
   - `docs/improve-api-reference`

2. **Make your changes**

   - Write clear, focused commits
   - Keep commits atomic (one logical change per commit)

3. **Write tests**

   Add tests for new functionality or bug fixes

4. **Run tests locally**

   ```bash
   pytest
   ```

5. **Run linting**

   ```bash
   ruff check src/
   ruff format src/
   ```

### Commit Messages

Write clear, descriptive commit messages:

```
Add CYME reader support for transformer elements

- Implement transformer parsing from CYME equipment files
- Add phase mapping for CYME transformer configurations
- Include unit tests for transformer conversion
```

## Code Style

DiTTo uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting.

### Style Guidelines

- **Line length**: 99 characters maximum
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Double quotes for strings
- **Type hints**: Use type hints for function parameters and return values

### Running Ruff

```bash
# Check for issues
ruff check src/

# Auto-fix issues
ruff check --fix src/

# Format code
ruff format src/
```

### Code Example

```python
from pathlib import Path
from typing import List, Optional

from gdm import DistributionSystem, DistributionBus
from loguru import logger


def parse_buses(
    input_file: Path,
    crs: Optional[str] = None
) -> List[DistributionBus]:
    """Parse bus data from input file.

    Args:
        input_file: Path to the input file
        crs: Coordinate reference system (optional)

    Returns:
        List of parsed distribution buses

    Raises:
        FileNotFoundError: If input file doesn't exist
    """
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    buses = []
    logger.info(f"Parsing buses from {input_file}")

    # Implementation...

    return buses
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_opendss/test_opendss_reader.py

# Run specific test
pytest tests/test_opendss/test_opendss_reader.py::test_read_ieee13

# Run with coverage
pytest --cov=ditto
```

### Writing Tests

Tests are located in the `tests/` directory. Follow existing patterns:

```python
# tests/test_opendss/test_new_feature.py
import pytest
from pathlib import Path

from ditto.readers.opendss.reader import Reader


class TestNewFeature:
    """Tests for the new feature."""

    def test_basic_functionality(self, tmp_path):
        """Test that basic functionality works."""
        # Arrange
        input_file = Path("tests/data/opendss_circuit_models/IEEE13/IEEE13Nodeckt.dss")

        # Act
        reader = Reader(input_file)
        system = reader.get_system()

        # Assert
        assert system is not None
        assert len(list(system.get_buses())) > 0

    @pytest.mark.parametrize("model_name", ["IEEE13", "ckt7", "ckt24"])
    def test_multiple_models(self, model_name):
        """Test feature works across multiple models."""
        input_file = Path(f"tests/data/opendss_circuit_models/{model_name}")
        # Test implementation...
```

### Test Data

Test data is located in `tests/data/`:
- `opendss_circuit_models/` - OpenDSS test models
- `cim_iec_61968_13/` - CIM test files
- `cyme_test_cases/` - CYME test models
- `GDM_testing/` - Serialized GDM models

## Submitting Changes

### Pull Request Process

1. **Push your branch**

   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request**

   - Go to the [DiTTo GitHub page](https://github.com/NREL-Distribution-Suites/ditto)
   - Click "Pull requests" > "New pull request"
   - Select your fork and branch
   - Fill out the PR template

3. **PR Description**

   Include:
   - What changes were made
   - Why the changes were made
   - How to test the changes
   - Any related issues (use `Fixes #123` to auto-close)

4. **Code Review**

   - Address reviewer feedback
   - Push additional commits as needed
   - Keep the PR focused and reasonably sized

### PR Checklist

Before submitting:

- [ ] Tests pass locally (`pytest`)
- [ ] Code is formatted (`ruff format src/`)
- [ ] Linting passes (`ruff check src/`)
- [ ] New code has tests
- [ ] Documentation is updated if needed
- [ ] Commit messages are clear

## Adding New Readers/Writers

### Adding a New Reader

1. **Create directory structure**

   ```
   src/ditto/readers/myformat/
   ├── __init__.py
   ├── reader.py
   ├── common/
   │   └── __init__.py
   ├── components/
   │   └── __init__.py
   └── equipment/
       └── __init__.py
   ```

2. **Implement the reader**

   ```python
   # src/ditto/readers/myformat/reader.py
   from pathlib import Path
   from typing import Optional

   from gdm import DistributionSystem
   from ditto.readers.reader import AbstractReader


   class Reader(AbstractReader):
       """Reader for MyFormat distribution system models."""

       def __init__(
           self,
           input_file: Path,
           crs: Optional[str] = None
       ):
           """Initialize the reader.

           Args:
               input_file: Path to input file
               crs: Coordinate reference system
           """
           super().__init__()
           self.input_file = input_file
           self.crs = crs

       def read(self) -> None:
           """Parse the input file and populate the system."""
           # Implementation...
           pass

       def get_system(self) -> DistributionSystem:
           """Return the populated distribution system."""
           self.read()
           return self.system
   ```

3. **Add component parsers**

   Create separate modules for each component type in `components/`

4. **Add tests**

   ```python
   # tests/test_myformat/test_myformat_reader.py
   ```

5. **Add documentation**

   Update `API.md` with the new reader documentation

### Adding a New Writer

1. **Create directory structure**

   ```
   src/ditto/writers/myformat/
   ├── __init__.py
   ├── write.py
   ├── components/
   │   └── __init__.py
   └── equipment/
       └── __init__.py
   ```

2. **Implement the writer**

   ```python
   # src/ditto/writers/myformat/write.py
   from pathlib import Path

   from gdm import DistributionSystem
   from ditto.writers.abstract_writer import AbstractWriter


   class Writer(AbstractWriter):
       """Writer for MyFormat distribution system models."""

       def __init__(self, system: DistributionSystem):
           """Initialize the writer.

           Args:
               system: The distribution system to export
           """
           super().__init__(system)

       def write(self, output_path: Path, **kwargs) -> None:
           """Write the system to output files.

           Args:
               output_path: Directory for output files
               **kwargs: Additional options
           """
           # Implementation...
           pass
   ```

3. **Add component mappers**

   Create mapper modules for each component type

4. **Add tests and documentation**

## Questions?

- Open an issue on GitHub
- Contact [Tarek Elgindy](mailto:tarek.elgindy@nrel.gov)

Thank you for contributing to DiTTo!
