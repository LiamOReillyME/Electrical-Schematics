# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Industrial Wiring Diagram Analyzer is a Python + Qt desktop application for importing PDF wiring diagrams of industrial machines and providing:
- **Interactive voltage flow simulation** with real-time visualization
- **Visual overlays on PDF** showing energized/de-energized components
- **Component toggling** to simulate contactor closures, fuse trips, switch changes
- **Circuit path tracing** to understand where voltage comes from and goes to
- **Diagnostic support** for troubleshooting faults
- Support for multi-voltage systems (24VDC control, 400VAC mains)

The application supports two modes:
1. **Manual annotation**: Click on PDF diagrams to mark components interactively
2. **DRAWER format parsing**: Automatically parse structured industrial diagrams (device tag lists + cable routing tables)

### Key Features

- **Visual Overlay System**: Real-time color-coded overlays on PDF
  - Green = Energized components
  - Red = De-energized components
  - Semi-transparent highlighting preserves underlying schematic
  - Toggle visibility with toolbar button

- **Interactive Simulation**: Dual-circuit simulation (control + power)
  - 24VDC control circuit (PLC, relays, sensors)
  - 400VAC power circuit (motors, contactors, loads)
  - Real-time state updates when components are toggled
  - Circuit path tracing for coils and contacts

- **DRAWER Format Auto-Loading**: Parse industrial electrical diagrams
  - Device tags from pages 26-27
  - Cable connections from pages 28-40
  - Cross-page wire tracing
  - Automatic voltage classification

## Development Commands

### Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"
```

### Running the Application
```bash
# Run the GUI
electrical-schematics

# Or directly
python -m electrical_schematics.main

# Analyze a DRAWER-format PDF
python examples/analyze_drawer_diagram.py
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_voltage_simulator.py

# Run with coverage
pytest --cov=electrical_schematics

# Run tests for a specific function
pytest tests/test_industrial_models.py::test_sensor_normally_open_energization -v
```

### Code Quality
```bash
# Format code (auto-fix)
black .

# Lint code (check only)
ruff check .

# Lint and auto-fix
ruff check --fix .

# Type check
mypy electrical_schematics
```

## Architecture

### Application Flow
1. **PDF Import** - User loads a vector PDF wiring diagram
2. **Manual Annotation** - User clicks/drags on PDF to mark components (sensors, relays, motors, etc.)
3. **Circuit Modeling** - Components and wires are stored in a graph structure
4. **Simulation** - Voltage flow is traced through the circuit based on sensor states (ON/OFF)
5. **Diagnostics** - Rule-based analysis identifies fault causes when components don't behave as expected

### Core Data Flow
```
PDF File → PDFRenderer → Qt Display
                ↓
        User Annotations
                ↓
        WiringDiagram (graph of components + wires)
                ↓
        VoltageSimulator (NetworkX graph traversal)
                ↓
        Results: which components are energized

        OR
                ↓
        FaultAnalyzer (rule-based diagnostic logic)
                ↓
        Results: possible causes + suggested checks
```

### Key Design Patterns

**Graph-Based Voltage Simulation**: `VoltageSimulator` uses NetworkX to model the circuit:
- **Nodes** = Industrial components (sensors, relays, motors, power sources)
- **Edges** = Wires connecting components
- **Traversal** = BFS from power sources, only following paths through "energized" components
- Sensors block flow when: NO sensor is OFF, or NC sensor is ON

**State-Based Component Logic**: Each `IndustrialComponent` has:
- `is_energized()` method determines if current can flow through it
- Depends on component type and current state (for sensors/switches)
- Non-sensor components always allow current flow

**Rule-Based Diagnostics**: `FaultAnalyzer` traces why a component isn't energized:
- Finds path from power source to component
- Identifies which sensors in the path are blocking current
- Suggests common fault scenarios (blown fuse, stuck contacts, etc.)

### Module Responsibilities

- **`models/`** - Data classes for industrial components, wires, and diagrams
  - `industrial_component.py` - Component types (sensors, relays, motors, etc.) with voltage ratings
  - `wire.py` - Wire connections with voltage levels
  - `diagram.py` - Complete wiring diagram with component/wire collections

- **`pdf/`** - PDF rendering and parsing
  - `pdf_renderer.py` - Converts PDF pages to QPixmap for Qt display
  - `drawer_parser.py` - Parses DRAWER-format industrial diagrams (400+ lines)
  - `drawer_to_model.py` - Converts DRAWER format to internal WiringDiagram model
  - `auto_loader.py` - Orchestrates automatic diagram loading and format detection
  - `visual_wire_detector.py` - Framework for color-based wire detection
  - `README_DRAWER.md` - Documentation for DRAWER format

- **`gui/`** - Qt interface
  - `main_window.py` - Main application with 3-panel layout (PDF | Interactive Panel | Analysis)
  - `pdf_viewer.py` - Interactive PDF viewer with **visual overlay system**
    - ComponentOverlay class for highlighting components
    - Real-time color-coded overlays (green/red)
    - Page-aware overlay positioning
    - Zoom-adaptive rendering
  - `interactive_panel.py` - Interactive simulation control panel
    - Component list with filtering
    - Toggle controls (double-click to toggle)
    - Circuit tracing
    - Component detail display

- **`simulation/`** - Voltage flow simulation
  - `voltage_simulator.py` - Basic graph traversal to find energized components
  - `interactive_simulator.py` - **Advanced interactive simulation engine** (500+ lines)
    - Dual circuit simulation (24VDC control + 400VAC power)
    - Circuit path tracing (coil circuits and contact circuits)
    - Component toggling (contactors, switches, fuses)
    - Real-time state updates
    - VoltageNode and CircuitPath data structures

- **`diagnostics/`** - Fault analysis
  - `fault_analyzer.py` - Rule-based system for diagnosing circuit faults

### Industrial Component Types

The application models common industrial components:

**Power Sources**: 24VDC, 400VAC, 230VAC, Ground
**Sensors/Inputs**: Proximity sensors, photoelectric sensors, limit switches, pressure switches, push buttons, E-stops
**Outputs/Actuators**: Relays, contactors, solenoid valves, motors, indicator lights
**Control**: PLC inputs/outputs, timers, counters
**Protection**: Fuses, circuit breakers

Each component has:
- **Designation** (e.g., S1, K1, M1) - standard industrial naming
- **Type** - from IndustrialComponentType enum
- **Voltage rating** - e.g., "24VDC", "400VAC"
- **State** - for sensors: ON/OFF/UNKNOWN
- **Normally open/closed** - for switches

## Visual Overlay System

The visual overlay system provides real-time visual feedback directly on PDF diagrams.

### How It Works
1. **Component Analysis**: Parse component positions from DRAWER format
2. **Simulation**: Run voltage flow simulation to determine energization states
3. **Overlay Generation**: Create ComponentOverlay objects for each component
4. **Rendering**: Draw semi-transparent colored rectangles on PDF
   - Green = Energized (has voltage)
   - Red = De-energized (no voltage)
5. **Real-Time Updates**: When user toggles component, overlays update instantly

### Key Classes

```python
class ComponentOverlay:
    component: IndustrialComponent  # Component to highlight
    is_energized: bool              # Energization state
    page: int                        # PDF page number
    rect: QRectF                     # Bounding box in PDF coordinates
```

### Coordinate Mapping

```python
# Convert PDF coordinates to screen coordinates
screen_x = pdf_x * zoom_level * 2
screen_y = pdf_y * zoom_level * 2
```

### Usage

See `VISUAL_OVERLAY.md` for comprehensive documentation.

## Interactive Simulation

The interactive simulation engine allows users to:
- Toggle component states (contactors, switches, fuses)
- Trace circuit paths (where does voltage come from/go to?)
- See real-time voltage propagation
- Understand dual-circuit systems (control + power)

### Dual Circuit Architecture

**Control Circuit (24VDC)**:
- PLC inputs/outputs
- Relay/contactor coils
- Control switches and buttons
- Sensor signals

**Power Circuit (400VAC/230VAC)**:
- Motor power
- Main contactor contacts
- Circuit breakers
- Loads

### Key Methods

```python
# Trace where contactor coil gets 24VDC
coil_path = simulator.trace_coil_circuit("K1")

# Trace power supply and load paths for contacts
supply_path, load_path = simulator.trace_contact_circuit("K1")

# Toggle component state
simulator.toggle_component("-K3")

# Get all energized components
energized = simulator.get_energized_components()
```

See `INTERACTIVE_SIMULATION.md` for detailed documentation.

## Simulation Logic

### Voltage Flow Algorithm
1. Start from all power sources (24VDC, 400VAC, etc.)
2. Use BFS to traverse the circuit graph
3. At each component, check `is_energized()`:
   - For NO sensors: energized if state==ON
   - For NC sensors: energized if state==OFF
   - For other components: always energized
4. Only continue through components that allow current flow
5. Mark all reachable components as energized

### Key Behaviors
- Sensors block current based on state + NO/NC configuration
- Power sources are always energized
- All other components pass current by default
- Multiple power sources are handled independently

## Diagnostic Rules

When a component is not energized but should be:
1. Find path from power source to component
2. Identify blocking sensors in that path
3. Check for common issues:
   - Sensor stuck in wrong state
   - Blown fuse in circuit
   - Wiring disconnection
   - Relay contact failure

When a component is energized but shouldn't be:
1. Check for short circuits
2. Check for stuck relay contacts (welded closed)
3. Check NC safety interlocks

## Testing Guidelines

- Test sensor energization logic (NO vs NC, ON vs OFF states)
- Test voltage flow through multi-component circuits
- Test diagnostic reasoning with blocked paths
- Use realistic component designations (S1, K1, M1, etc.)
- Test edge cases: no power source, disconnected components, unknown sensor states

## PDF Annotation Workflow

Users interact with PDFs by:
1. Loading a PDF file
2. Clicking and dragging to select component areas
3. Entering component details in dialog (designation, type, voltage)
4. Components are stored with PDF coordinates for reference
5. Future: manually drawing wire connections between components

## DRAWER Format Parser

The application includes a specialized parser for DRAWER-style industrial electrical diagrams, commonly used in European industrial automation.

### DRAWER Format Structure

1. **Device Tag List** (typically pages 26-27):
   - Vertical layout with each device on 5 lines
   - Format: Device Tag | Page Ref | Technical Data | Type | Part Number
   - Example: `-A1` (24VDC PLC), `+DG-M1` (400VAC motor)

2. **Cable Routing Tables** (typically pages 28-40):
   - Lists all wire connections with source/target terminals
   - Format: Cable Name | Source Terminal | Target Terminal | Wire Color
   - Example: `-A1-X5:3` -> `+DG-B1:0V` (encoder connection)

### Terminal Reference Format

```
[+-]DEVICE[-TERMINAL_BLOCK][:PIN]
```

Examples:
- `-A1-X5:3`: PLC `-A1`, terminal block `X5`, pin `3`
- `+DG-M1:U1`: Motor `+DG-M1`, phase `U1`
- `-K1:13`: Relay `-K1`, contact `13`

### Device Tag Naming Convention

- **Prefix `+`**: Field devices (sensors, motors, encoders)
  - `+DG-M1`: Motor, `+DG-B1`: Encoder, `+DG-V1`: Valve

- **Prefix `-`**: Control panel devices
  - `-A1`: PLC, `-F2`: Fuse, `-K1`: Relay, `-U1`: VFD, `-G1`: Power supply
- **Prefix `+`**: Component / Device Location
  - `+DG` : Device Ground, `+CD`: Control Drawer, `+EXT`: Extractor, `+EXTERN`: External, `+AO`: Access Opening, `+OC`: Operator Console, `+OP`: Operator Panel

### Automatic Voltage Detection

The parser identifies voltage levels from technical data strings:
- `24VDC`: Control circuits, PLC I/O
- `5VDC`: Encoders, some sensors
- `230VAC`: Single-phase power
- `400VAC`: Three-phase motors, VFDs
- `UNKNOWN`: Passive components

### Usage Example

```python
from pathlib import Path
from electrical_schematics.pdf.drawer_parser import DrawerParser

# Parse diagram
parser = DrawerParser(Path("DRAWER.pdf"))
diagram = parser.parse()

# Get device info and voltage level
device = diagram.get_device("-A1")
print(f"PLC: {device.voltage_level}")  # "24VDC"

# Find all wires connected to PLC
connections = diagram.get_connections_for_device("-A1")

# Trace across pages
for conn in connections:
    src_voltage = diagram.get_voltage_level(conn.source)
    tgt_voltage = diagram.get_voltage_level(conn.target)
    print(f"{conn.source} ({src_voltage}) -> {conn.target} ({tgt_voltage})")
```

### Cross-Page Wire Tracing

The parser can follow connections across multiple pages:
1. Extract source terminal (e.g., `-A1-X5:3` on page 28)
2. Look up source device (`-A1`) in device tag list
3. Extract target terminal (e.g., `+DG-B1:0V` on page 28)
4. Look up target device (`+DG-B1`) to find it's on page 21
5. Determine voltage levels: `-A1` is 24VDC, `+DG-B1` is 5VDC

This enables:
- Tracing signal paths from sensor to PLC to output
- Identifying power distribution (400VAC to motors)
- Detecting voltage level mismatches
- Understanding system interconnections

See `examples/analyze_drawer_diagram.py` for complete example.

## Example Scripts

The `examples/` directory contains demonstration scripts:

- **`analyze_drawer_diagram.py`** - Parse and analyze DRAWER format PDFs
  - Extracts devices and connections
  - Shows voltage classification
  - Demonstrates cross-page wire tracing

- **`interactive_simulation_test.py`** - Test interactive simulation features
  - Circuit path tracing
  - Component toggling
  - State explanation
  - Voltage flow visualization

- **`visual_overlay_test.py`** - Test visual overlay system
  - Automatic overlay generation
  - Real-time state updates
  - Component toggling with visual feedback
  - Run with: `python examples/visual_overlay_test.py`

## Documentation Files

- **`CLAUDE.md`** (this file) - Main project documentation for Claude Code
- **`INTERACTIVE_SIMULATION.md`** - Comprehensive guide to interactive simulation system
- **`VISUAL_OVERLAY.md`** - Detailed documentation of visual overlay feature
- **`README_DRAWER.md`** (in `pdf/`) - DRAWER format specification and parsing guide

## Future Enhancements

Completed features:
- ✅ Visual overlay on PDF (highlight energized components)
- ✅ Interactive simulation with component toggling
- ✅ Real-time voltage flow visualization
- ✅ Circuit path tracing

Potential areas for future expansion:
- Wire path highlighting (trace energized wire segments)
- Animation of voltage flow along wires
- Current flow calculation and display
- Automatic wire detection from PDF (computer vision)
- Save/load annotated diagrams
- Export diagnostic reports
- Integration with PLC programming for state verification
- Support for additional diagram formats (EPLAN, AutoCAD Electrical)
- Time-based simulation (switching sequences)
- Fault injection and propagation visualization
