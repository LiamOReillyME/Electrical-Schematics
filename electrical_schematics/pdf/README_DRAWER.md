# DRAWER Format Parser

This parser handles DRAWER-style industrial electrical diagrams commonly used in European industrial automation.

## Format Overview

DRAWER diagrams are structured PDFs with:

### Device Tag List (Typically Pages 26-27)
Lists all electrical devices with technical specifications in a vertical layout:

```
Device Tag | Page Ref | Technical Data | Type Designation | Part Number
```

**Example:**
```
-A1
18 0
24VDC 24xD-IN 8xD-OUT 4xCO
PCD3.M9K47
6223994
```

### Cable Diagrams (Typically Pages 28-40)
Shows wire routing with source/target terminal references:

```
Cable Name: +CD-B1
Cable Type: BMGH-Typ:STS24 8x0,25 qmm

Source Terminal | Function | Wire Color | Target Terminal
-A1-X5:3       | Encoder  | BK         | +DG-B1:0V
```

## Terminal Reference Format

Terminal references follow this pattern:
```
[+-]DEVICE[-TERMINAL_BLOCK][:PIN]
```

**Examples:**
- `-A1-X5:3` = Device `-A1`, terminal block `X5`, pin `3`
- `+DG-B1:0V` = Device `+DG-B1`, terminal `0V`
- `-K1:13` = Device `-K1`, pin `13`

## Device Tag Naming Convention

- **Prefix `+`**: Field devices (sensors, motors, encoders)
  - `+DG-M1`: Motor 1
  - `+DG-B1`: Encoder 1
  - `+DG-V1`: Valve 1

- **Prefix `-`**: Control panel devices
  - `-A1`: PLC/Controller
  - `-F2`: Fuse 2
  - `-K1`: Relay 1
  - `-U1`: VFD/Inverter 1
  - `-G1`: Power supply 1

## Voltage Detection

The parser automatically classifies devices by voltage level based on technical data:

- **24VDC**: Control circuits, PLC I/O, sensors
- **5VDC**: Encoders, some sensors
- **230VAC**: Single-phase power, fans, small motors
- **400VAC**: Three-phase motors, VFDs, high power equipment
- **UNKNOWN**: Passive components (relays, resistors, filters)

## Usage Example

```python
from pathlib import Path
from electrical_schematics.pdf.drawer_parser import DrawerParser

# Parse diagram
parser = DrawerParser(Path("DRAWER.pdf"))
diagram = parser.parse()

# Get device info
device = diagram.get_device("-A1")
print(f"PLC: {device.tech_data}")
print(f"Voltage: {device.voltage_level}")

# Find all connections for a device
connections = diagram.get_connections_for_device("-A1")
for conn in connections:
    print(f"{conn.source} -> {conn.target} (cable {conn.cable_name})")

# Check voltage level of a terminal
voltage = diagram.get_voltage_level("-A1-X5:3")
print(f"Terminal voltage: {voltage}")
```

## Key Features

1. **Cross-Page Tracing**: Follow wires from source to destination across multiple pages
2. **Voltage Classification**: Automatically distinguish 24VDC control vs 400VAC power
3. **Terminal Parsing**: Extract device tags from complex terminal references
4. **Cable Analysis**: Group conductors by cable name and type
5. **Device Lookup**: Fast lookup of device specifications by tag

## Limitations

- Assumes standard DRAWER format (vertical device list, cable routing tables)
- Does not parse actual schematic diagrams (ladder logic, circuit drawings)
- Wire routing is text-based only (no visual/geometric information)
- Some complex terminal references may need manual verification

## Data Model

### DeviceInfo
- `tag`: Device identifier (e.g., "-A1")
- `page_ref`: Page location in diagram
- `tech_data`: Technical specifications
- `type_designation`: Manufacturer type/model
- `part_number`: Order/article number
- `voltage_level`: Auto-detected voltage (24VDC, 400VAC, etc.)

### CableConnection
- `cable_name`: Cable identifier (e.g., "+CD-B1")
- `cable_type`: Cable specification
- `source`: Source terminal reference
- `target`: Target terminal reference
- `wire_color`: Conductor color code
- `function_source/target`: Function description
- `conductor_num`: Position in cable

### DrawerDiagram
- `devices`: Dictionary of all devices
- `connections`: List of all wire connections
- Methods for device lookup and connection tracing

## Testing

See `examples/analyze_drawer_diagram.py` for a complete analysis example.

Run with:
```bash
python examples/analyze_drawer_diagram.py
```
