# Manual Annotation System - User Guide

## Overview

The Industrial Wiring Diagram Analyzer now includes a comprehensive manual annotation system that allows you to:
- Place components from a library onto PDF schematics
- Draw wires with multi-point routing
- Save and load projects
- Import component data from DigiKey
- Run circuit simulations on annotated diagrams

## Quick Start

### 1. Launch the Application

```bash
python3 -m electrical_schematics.gui
```

### 2. Open a PDF

**File → Open PDF** or **Ctrl+O**

- Select your electrical schematic PDF
- The PDF will load in the viewer
- Auto-detection will attempt to parse DRAWER format (if applicable)

### 3. Add Components

**Two Methods:**

#### A. Drag from Component Palette (Recommended)
1. Browse the Component Library panel on the left
2. Find your component (e.g., "Contactor 9A 24VDC Coil")
3. Drag the component onto the PDF
4. Drop at desired location
5. Properties dialog appears:
   - **Basic Info Tab**: Designation, type, voltage, size
   - **DigiKey Info Tab**: Manufacturer, part number, image, specs
   - **Advanced Tab**: Sensor state, terminal information
6. Click OK to place component

#### B. Manual Area Selection
1. Click and drag on PDF to create selection box
2. Release to open component properties dialog
3. Fill in details manually
4. Click OK to create component

### 4. Draw Wires

**Step-by-Step:**
1. Select wire type from toolbar:
   - **⚡ 24VDC** - Red wires for DC control
   - **⏚ 0V** - Blue wires for ground
   - **~ AC** - Black wires for AC power

2. **Ctrl+Click** on a component terminal (yellow circle) to start wire

3. Click anywhere on PDF to add waypoints (routing points)

4. Click on another component's terminal to complete wire

5. **ESC** or **Right-Click** to cancel

### 5. Edit Components

**Double-click** any component to edit:
- Change designation, type, voltage
- Adjust size
- Set sensor state (ON/OFF/UNKNOWN)
- View DigiKey information

### 6. Save Your Work

**File → Save Project** or **Ctrl+S**

- Enter project name and description
- All components, wires, and settings saved to database
- Auto-enables on first component/wire placement

### 7. Load Saved Projects

**File → Load Project** or **Ctrl+L**

- Browse list of saved projects
- Shows component count, wire count, last modified date
- Select and click Open
- Full state restoration (PDF, components, wires, simulation)

## Component Library

### Pre-Populated Components (47 total)

**Power Supplies (6)**
- 24VDC: 2.5A, 5A, 10A
- 5VDC: 3A
- 400VAC distribution

**Contactors/Relays (7)**
- ABB, Schneider, Siemens contactors
- 24VDC relays (SPDT, DPDT)

**Sensors (15)**
- Optical: through-beam, retroreflective, diffuse
- Proximity: inductive, capacitive
- Light curtains
- Limit switches
- Reflective sensors

**PLCs (6)**
- Generic input/output modules (8ch, 16ch)

**Motors (5)**
- AC motors: 0.5kW - 5.5kW
- DC motors: 24V

**Protection (8)**
- Fuses: 2A - 16A
- Circuit breakers: 10A - 40A

### Adding Components from DigiKey

1. Click **"➕ Add from DigiKey"** in Component Palette
2. Enter part number (DigiKey or manufacturer)
3. Click **Search**
4. Select category, subcategory, prefix, and type
5. Click **OK**
6. Component added to library (ready to drag)

*Note: Full DigiKey API integration requires internet connection*

## Terminal System

Terminals are automatically positioned based on component type:

| Component Type | Terminal Layout |
|---------------|-----------------|
| Contactors/Relays | 4 terminals (2 coil left, 2 contact right) |
| Sensors | 3 terminals (2 power left, 1 output right) |
| Power Supplies | 2 terminals (top/bottom) |
| Motors | 3 terminals (three-phase at top) |
| PLCs | 8 terminals (along left edge) |
| Default | 2 terminals (left/right) |

**Yellow circles** indicate terminal positions. Snap radius is 10 pixels (PDF coordinates).

## Wire Routing

### Multi-Point Routing
- Wires support unlimited waypoints
- Click to add routing points between terminals
- Wires automatically color-coded:
  - **Red**: 24VDC
  - **Blue**: 0V/Ground
  - **Black**: AC Power
- Wire endpoints show connection circles

### Best Practices
- Use waypoints to route wires around components
- Match wire voltage to connected components
- Complete one wire before starting another
- Use Ctrl+Click to start from terminal (prevents accidental selection)

## Simulation Features

### Interactive Simulation
After placing components and wires:

1. **Interactive Panel** (middle) shows toggleable sensors/switches
2. Click component designations to toggle states
3. **PDF Overlays** show energization:
   - **Green**: Energized components
   - **Red**: De-energized components
   - **Yellow**: Selected component

### Circuit Analysis
- **Voltage Flow Simulation**: Traces current paths
- **Fault Diagnostics**: Troubleshoot circuit issues
- Works with both auto-loaded and manually annotated diagrams

## Project Management

### Save Options

**Save Project (Ctrl+S)**
- Saves to database with current name
- If new project, prompts for name

**Save Project As (Ctrl+Shift+S)**
- Save with new name
- Creates new project entry
- Original remains unchanged

**Export to JSON**
- Export project as .json file
- Human-readable format
- Useful for backups, sharing

**Import from JSON**
- Load external .json project
- Adds to database
- Optionally load immediately

### Project Info Displayed
- Name
- Component count
- Wire count
- Last modified timestamp
- Description

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New Project |
| Ctrl+O | Open PDF |
| Ctrl+S | Save Project |
| Ctrl+Shift+S | Save Project As |
| Ctrl+L | Load Project |
| Ctrl+Q | Exit |
| Ctrl+Click | Start wire drawing |
| ESC | Cancel wire drawing |
| Delete | Delete selected component |

## Menu Reference

### File Menu
- New Project
- Open PDF
- Save Project
- Save Project As
- Load Project
- Export to JSON
- Import from JSON
- Exit

### Edit Menu
- Delete Component

### View Menu
- Toggle Component Palette
- Show/Hide Overlays

## Component Dialog Tabs

### Basic Info
- Designation (e.g., K1, S1)
- Component Type
- Description
- Voltage Rating
- Position (read-only, shows placement)
- Size (width/height in PDF points)

### DigiKey Info
*(Only shown for library components)*
- Manufacturer
- Part Number
- Datasheet link (clickable)
- Component image preview
- Technical specifications table

### Advanced
- Sensor/Switch State (ON/OFF/UNKNOWN)
- Contact Type (Normally Open/Closed)
- Terminal information (reference guide)

## Tips & Tricks

1. **Zoom for Precision**: Use zoom controls to place components accurately
2. **Component Selection**: Click component once to select (yellow border), double-click to edit
3. **Wire Preview**: See dashed preview line while routing
4. **Modified Flag**: Save action enables when project is modified
5. **Terminal Snapping**: Get close to yellow terminal circles for automatic connection
6. **Undo Wire**: Press ESC if you make a mistake while drawing
7. **Component Sizing**: Adjust width/height in dialog for better visual fit
8. **Search Components**: Use search bar in palette to filter library

## Troubleshooting

**Components not appearing on PDF**
- Check "Show Overlays" button is enabled (toolbar)
- Verify components have valid positions
- Ensure PDF is loaded

**Wires not connecting**
- Ctrl+Click directly on terminal (yellow circle)
- Verify wire drawing mode is active (status bar message)
- Check terminal detection radius (10 pixels)

**Save button disabled**
- Make at least one change (add component/wire)
- Save action auto-enables after first modification

**DigiKey search not working**
- Component placeholder created even without API
- Full integration requires: pip install requests requests-oauthlib
- OAuth credentials configured in settings

## Database Location

Projects and component library stored in:
```
~/.electrical_schematics/components.db
```

Configuration file:
```
~/.electrical_schematics/config.json
```

## Future Enhancements

Planned features:
- Wire energization visualization
- Auto-routing algorithm
- Component symbol editor
- Export annotated PDF
- Cloud sync for component library
- Collaborative editing

## Support

For issues, feature requests, or questions:
- GitHub: https://github.com/anthropics/claude-code/issues
- Check logs for error details

---

**Version**: 1.0
**Last Updated**: 2026-01-26
