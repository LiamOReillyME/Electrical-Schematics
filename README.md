# Industrial Wiring Diagram Analyzer

A desktop application for importing PDF wiring diagrams of industrial machines and providing interactive voltage flow analysis and diagnostic support. Handles 24VDC control circuits, 400VAC mains, sensor wiring, and fault diagnostics.

## Features

- **PDF Import**: Load machine wiring diagrams from vector PDF files
- **Interactive Annotation**: Click to mark components, sensors, relays, and connections
- **Voltage Flow Simulation**: Trace voltage flow based on sensor states (ON/OFF)
- **Multi-Voltage Support**: Handle 24VDC control, 400VAC mains, and mixed circuits
- **Diagnostic Engine**: Query with fault conditions and get troubleshooting guidance
- **State Simulation**: See how the circuit behaves with different sensor/switch states

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

## Running the Application

```bash
# Run the GUI application
electrical-schematics

# Or directly with Python
python -m electrical_schematics.main
```

## Quick Start Example

See `examples/example_usage.py` for a programmatic example:

```bash
python examples/example_usage.py
```

This demonstrates creating a simple motor control circuit with:
- 24VDC power supply
- Emergency stop (NC)
- Start button (NO)
- Contactor
- Motor

The example shows voltage flow simulation and fault diagnostics.

## Development

```bash
# Run tests
pytest

# Run specific test file
pytest tests/test_voltage_simulator.py

# Run with coverage
pytest --cov=electrical_schematics

# Format code
black .

# Lint code
ruff check .

# Type check
mypy electrical_schematics
```

## Usage Workflow

### Automatic Mode (DRAWER Format)

For DRAWER-style industrial diagrams, the application automatically:

1. **Load PDF**: Open the PDF - format is auto-detected
2. **Auto-Extract**: All devices and connections are automatically loaded:
   - Device tags from pages 26-27
   - Wire connections from pages 28-40
   - Voltage levels (24VDC, 400VAC) automatically classified
3. **Simulate**: Run voltage flow simulation immediately
4. **Diagnose**: Query fault conditions for troubleshooting

**Wire Color Coding:**
- **RED** lines = 24VDC (control voltage)
- **BLUE** lines = 0V (reference/ground)
- **GREEN** lines = PE (protective earth)

### Manual Mode (Other PDFs)

For non-DRAWER diagrams:

1. **Load PDF**: Open a machine wiring diagram PDF file
2. **Annotate Components**: Click and drag to select component areas, then enter details:
   - Designation (S1, K1, M1, etc.)
   - Type (sensor, relay, motor, etc.)
   - Voltage rating
3. **Set Sensor States**: Define which sensors/switches are ON or OFF
4. **Run Simulation**: See which components receive voltage
5. **Diagnose Faults**: Enter fault symptoms to get troubleshooting guidance

## Project Structure

- `electrical_schematics/` - Main application package
  - `gui/` - Qt-based user interface with PDF viewer
  - `pdf/` - PDF rendering with PyMuPDF
  - `models/` - Data models for industrial components, wires, diagrams
  - `simulation/` - Voltage flow simulation engine
  - `diagnostics/` - Rule-based fault analysis
- `tests/` - Test suite
- `examples/` - Example usage and sample diagrams

## License

MIT
# Electrical-Schematics
