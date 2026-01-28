# Automatic DRAWER Diagram Loader

## Overview

The application now includes automatic analysis and loading of DRAWER-format industrial electrical diagrams. When you open a DRAWER PDF, the application automatically extracts all devices, connections, and voltage information without manual annotation.

## What Gets Auto-Loaded

### 1. Device Information
From pages 26-27 (Device Tag List):
- **Device tags** (e.g., `-A1`, `+DG-M1`)
- **Technical specifications** (voltage ratings, part numbers)
- **Component types** (PLC, motor, sensor, relay, etc.)
- **Voltage classification** (24VDC, 400VAC, 230VAC, 5VDC)

### 2. Wire Connections
From pages 28-40 (Cable Routing Tables):
- **Source and target terminals** (e.g., `-A1-X5:3` → `+DG-B1:0V`)
- **Cable names** (e.g., `+CD-B1`)
- **Wire colors** (BK, RD, GN, etc.)
- **Cable specifications** (type, conductor count)

### 3. Voltage Analysis
Automatically determines:
- **Low voltage** (24VDC, 5VDC) - Control circuits
- **High voltage** (400VAC, 230VAC) - Power distribution
- **Wire color coding**:
  - RED = 24VDC (control voltage)
  - BLUE = 0V (reference/common)
  - GREEN = PE (protective earth/ground)

### 4. Component Classification
Maps device tags to industrial component types:
- **`-A1`** → PLC (Programmable Logic Controller)
- **`+DG-M1`** → Motor
- **`+DG-B1`** → Encoder (treated as sensor)
- **`-K1`** → Relay/Contactor
- **`-F7`** → Circuit breaker/Fuse
- **`-G1`** → Power supply
- **`-U1`** → VFD/Motor drive

## Cross-Page Wire Tracing

The loader can follow connections across multiple pages:

**Example:**
```
Cable +CD-B1 on page 28:
  -A1-X5:3 (PLC input on page 18)
    → +DG-B1:0V (Encoder reference on page 21)

Voltage: 24VDC → 5VDC reference
```

This enables:
- Tracing signal paths from sensor → PLC → output
- Following power distribution through the system
- Understanding multi-page interconnections
- Detecting voltage level transitions

## Using the Auto-Loader

### In the GUI Application

1. **Open a DRAWER PDF:**
   ```
   File → Open PDF → Select DRAWER.pdf
   ```

2. **Automatic Detection:**
   - Application detects DRAWER format
   - Shows "DRAWER FORMAT DETECTED - Auto-loaded!"
   - Displays component summary

3. **Review Loaded Data:**
   - See devices grouped by voltage
   - View wire connection count
   - Check power sources and sensors

4. **Run Simulation:**
   - Click "Run Simulation"
   - See voltage flow through circuit
   - Identify energized components

### Programmatically

```python
from pathlib import Path
from electrical_schematics.pdf.auto_loader import DiagramAutoLoader

# Load diagram
diagram, format_type = DiagramAutoLoader.load_diagram(Path("DRAWER.pdf"))

if format_type == "drawer":
    print(f"Auto-loaded {len(diagram.components)} components")

    # Access device info
    plc = diagram.get_component_by_designation("-A1")
    print(f"PLC: {plc.voltage_rating}")  # "24VDC"

    # Get wire connections
    plc_wires = diagram.get_wires_for_component("-A1")
    print(f"PLC has {len(plc_wires)} connections")

    # Run simulation
    from electrical_schematics.simulation import VoltageSimulator
    simulator = VoltageSimulator(diagram)
    energized = simulator.simulate()
```

## Format Detection

The loader automatically detects DRAWER format by looking for:
- "Device tag" / "Betriebsmittelkennzeichen" headers
- "Cable diagram" / "Kabelplan" sections
- Structured device list on pages 26-27
- Cable routing tables on pages 28-40

If these aren't found, the application falls back to manual annotation mode.

## Voltage Classification Rules

The loader uses these rules to determine voltage levels:

### From Technical Data String:
- Contains "24VDC" → 24VDC
- Contains "400VAC" → 400VAC
- Contains "230VAC" or "150-260VAC" → 230VAC
- Contains "5VDC" → 5VDC

### From Device Tag Pattern:
- `-G1` with 24VDC specs → Power supply (24VDC)
- `+DG-M1` with 400VAC → Motor (400VAC)
- `-U1` with KW rating → VFD/Drive (400VAC)
- `-F7` with 400VAC → Circuit breaker (400VAC)

### Wire Color Heuristics (Visual Analysis):
- **RED** wires → Typically 24VDC
- **BLUE** wires → Typically 0V/common
- **GREEN** wires → Protective earth (PE)
- **BLACK** wires → Various (check context)

## Component Type Mapping

| Device Tag | Component Type | Typical Voltage |
|-----------|----------------|-----------------|
| `-A1` | PLC | 24VDC |
| `+DG-M1` | Motor | 400VAC |
| `+DG-B1` | Encoder/Sensor | 5VDC |
| `+DG-V1` | Solenoid Valve | 230VAC |
| `-K1` | Relay | 24VDC coil |
| `-K3` | Contactor | 24VDC coil |
| `-F2`-`-F6` | Fuse/Breaker | 230VAC |
| `-F7` | Circuit Breaker | 400VAC |
| `-G1` | Power Supply | 24VDC output |
| `-U1` | VFD/Drive | 400VAC |
| `-EL1`, `-EL2` | Fan | 230VAC |

## Simulation Readiness

After auto-loading, the diagram is immediately ready for:

1. **Voltage Flow Simulation:**
   - Power sources are identified
   - Wire connections are established
   - Voltage levels are known

2. **Fault Diagnostics:**
   - Component interconnections mapped
   - Voltage paths can be traced
   - Blocking components identified

3. **State Analysis:**
   - Sensors defaulted to OFF state
   - Can be changed to simulate different conditions
   - Flow updates based on sensor states

## Example Output

When loading `DRAWER.pdf`:

```
DRAWER FORMAT DETECTED - Auto-loaded!
============================================================

Components by voltage:
  24VDC       :   3 devices
  5VDC        :   1 devices
  230VAC      :   8 devices
  400VAC      :   3 devices
  UNKNOWN     :   9 devices

Total connections: 27

Power sources: 2
  - -F7 (400VAC)
  - -G1 (24VDC)

Sensors/Switches: 1
  - +DG-B1 (Encoder)

Ready for simulation and diagnostics!

Wire Color Coding:
  • RED lines = 24VDC (control voltage)
  • BLUE lines = 0V (reference)
  • GREEN lines = PE (protective earth/ground)
```

## Testing

Run the auto-loader test:
```bash
python examples/test_auto_loader.py
```

This verifies:
- Format detection
- Device extraction
- Wire tracing
- Voltage classification
- Component type mapping
- Simulation readiness

## Technical Implementation

The auto-loader consists of:

1. **`drawer_parser.py`** - Parses DRAWER PDF format
2. **`drawer_to_model.py`** - Converts to internal data model
3. **`visual_wire_detector.py`** - Analyzes wire colors (future enhancement)
4. **`auto_loader.py`** - Orchestrates automatic loading
5. **Main window integration** - Seamless GUI experience

See `electrical_schematics/pdf/README_DRAWER.md` for detailed format documentation.
