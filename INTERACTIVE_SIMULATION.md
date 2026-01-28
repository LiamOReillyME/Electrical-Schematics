# Interactive Electrical Simulation

## Overview

The application now features an **interactive simulation system** that lets you:

1. **Visualize voltage flow** in real-time
2. **Toggle components** (contactors, switches, fuses) and see effects immediately
3. **Trace circuits** - See where voltage comes from and where it goes
4. **Simulate actions** - Close contactors, trip fuses, activate sensors
5. **Understand circuit behavior** - Get detailed explanations of component states

## Key Features

### 1. Dual Circuit Simulation

The simulator handles two separate but interconnected circuits:

**Control Circuit (24VDC):**
- PLC inputs/outputs
- Relay/contactor coils
- Control switches and buttons
- Sensor signals

**Power Circuit (400VAC/230VAC):**
- Motor power
- Main contactor contacts
- Circuit breakers
- Loads

### 2. Component State Tracking

Each component has a real-time state:
- **Energized/De-energized** - Is voltage present?
- **Voltage level** - Actual voltage (24V, 400V, etc.)
- **Current flow** - Is current flowing through it?
- **Contact state** - For contactors: coil vs. contacts

### 3. Interactive Controls

**Toggle Actions:**
- **Contactors/Relays** - Energize/de-energize coil → contacts open/close
- **Switches/Sensors** - ON/OFF states
- **Fuses/Breakers** - Trip/reset
- **Push Buttons** - Press/release

**Circuit Tracing:**
- Trace where a contactor coil gets 24VDC
- Trace where main contacts get power supply
- Trace where load voltage goes
- See blocking components in path

### 4. Real-Time Updates

When you change a component:
1. Simulation instantly recalculates
2. Energization states update
3. Visual feedback shows changes
4. Analysis panel updates with current state

## Example Scenarios

### Scenario 1: Contactor K1.1 Analysis

**Question:** "Where does K1.1 contactor coil get its 24VDC from?"

```python
# In code
simulator = InteractiveSimulator(diagram)
coil_path = simulator.trace_coil_circuit("K1")

# Shows:
# Source: -G1 (24VDC Power Supply)
# Path: -G1 → -F4 (Fuse) → -Q1 (Switch) → K1 (Coil)
# Active: YES (if all components closed)
# Blocked by: -Q1 (if switch is open)
```

**In GUI:**
1. Select "K1" from component list
2. Click "Trace Circuit"
3. See full path with state of each component
4. See which component (if any) is blocking

### Scenario 2: Main Contact Power Flow

**Question:** "When contactor K1 closes, where does voltage come from and go to?"

```python
# Supply side
supply_path, load_path = simulator.trace_contact_circuit("K1")

# Supply shows:
# From: -F7 (400VAC Breaker)
# To: K1 (Main Contacts)
# Voltage: 400VAC

# Load shows:
# From: K1 (Main Contacts)
# To: +DG-M1 (Motor)
# Voltage: 400VAC
```

**In GUI:**
1. Select "K1"
2. View "Component Details"
3. See both coil circuit (24VDC) and contact circuit (400VAC)
4. Toggle K1 to see contacts close/open

### Scenario 3: Simulate Trip Fuse

**Action:** Trip circuit breaker F7 and see what de-energizes

```python
# Before: Motor M1 running
simulator.toggle_component("-F7")  # Trip breaker

# After:
# - F7 is OFF (tripped)
# - Motor M1 de-energized
# - VFD U1 de-energized
# - All 400VAC loads lost power
```

**In GUI:**
1. Double-click "-F7" (circuit breaker)
2. Breaker trips (turns red)
3. All downstream components instantly de-energize
4. See effect in real-time

### Scenario 4: Close Contactor

**Action:** Energize contactor K3 to start motor

```python
# Energize coil
simulator.toggle_component("-K3")  # Close contactor

# Effects:
# - K3 coil energized (24VDC)
# - K3 main contacts close
# - 400VAC flows to motor
# - Motor energizes
```

**In GUI:**
1. Double-click "-K3" (contactor)
2. Coil energizes (gets 24VDC)
3. Main contacts close
4. Motor downstream energizes
5. See full circuit path highlighted

## GUI Interface

### PDF Viewer (Left) - **NEW: Visual Overlays!**

**Visual Overlay System:**
- **Real-time component highlighting** directly on PDF diagrams
- Color-coded overlays:
  - **GREEN** = Energized components (has voltage)
  - **RED** = De-energized components (no voltage)
- Semi-transparent overlays show component boundaries
- Component designations labeled on overlays
- Updates instantly when components are toggled
- Toggle visibility with "🔍 Show Overlays" button

**Interactive Features:**
- Navigate pages with Previous/Next buttons
- Zoom in/out to see component details
- Click and drag to manually annotate components (manual mode)
- Overlays automatically positioned based on component location

**How It Works:**
1. Open a DRAWER-format PDF
2. Overlays automatically appear on circuit diagram pages
3. Green highlights show where voltage is present
4. Toggle components in middle panel
5. Watch overlays update in real-time on PDF

### Interactive Panel (Middle)

**Component List:**
- Shows all components grouped by type
- Color coded:
  - Green = Energized
  - Red = De-energized
- Filter by category (Contactors, Sensors, Motors, etc.)
- Double-click to toggle state

**Actions:**
- **Toggle Selected** - Change component state
- **Trace Circuit** - Show full circuit path
- **Run Simulation** - Recalculate (automatic after toggle)

**Component Details:**
- Current energization state
- Voltage level present
- For contactors:
  - Coil circuit (24VDC control)
  - Contact circuit (power side)
  - Supply and load paths

### Analysis Panel (Right)

Shows simulation results:
```
INTERACTIVE SIMULATION - Current State
============================================================

24VDC Control Circuit:
  ✓ -G1        - Power Supply (24VDC/5A)
  ✓ -A1        - PLC (PCD3.M9K47)
  ✓ -K3        - Contactor coil

400VAC Power Circuit:
  ✓ -F7        - Circuit Breaker (10A)
  ✓ -U1        - VFD (7.5KW)
  ✓ +DG-M1     - Motor (4.8KW)
```

## Programmatic Usage

### Basic Simulation

```python
from electrical_schematics.simulation.interactive_simulator import InteractiveSimulator

# Create simulator
simulator = InteractiveSimulator(diagram)

# Run simulation
nodes = simulator.simulate_step()

# Check component state
if nodes["-K3"].is_energized:
    print("K3 coil is energized")
```

### Trace Circuits

```python
# Trace coil circuit (24VDC)
coil_path = simulator.trace_coil_circuit("K3")
print(f"Coil gets 24VDC from: {coil_path.source}")
print(f"Path: {' → '.join(coil_path.path_nodes)}")
print(f"Active: {coil_path.is_active}")

# Trace power circuits (400VAC)
supply, load = simulator.trace_contact_circuit("K3")
print(f"Power supply from: {supply.source}")
print(f"Load voltage goes to: {load.destination}")
```

### Toggle Components

```python
# Close contactor
simulator.toggle_component("-K3")

# Open switch
simulator.toggle_component("-S1")

# Trip fuse
simulator.toggle_component("-F7")

# Each toggle automatically re-simulates
```

### Get Current State

```python
# Get all energized components
energized = simulator.get_energized_components()

# Get energized by voltage type
control_circuit = simulator.get_energized_components("24VDC")
power_circuit = simulator.get_energized_components("400VAC")

# Explain component state
explanation = simulator.explain_state("-K3")
print(explanation)
```

## Circuit Tracing Logic

### Coil Circuit (Control Side)

For a contactor coil:
1. Starts at 24VDC power source
2. Traces through control circuit:
   - Fuses
   - Switches
   - Safety interlocks
   - Emergency stops
3. Reaches contactor coil
4. Returns path and identifies blocking components

### Contact Circuit (Power Side)

For contactor main contacts:

**Supply Side:**
1. Starts at 400VAC/230VAC source
2. Traces through:
   - Main circuit breaker
   - Power distribution
3. Reaches contactor input
4. **Blocks if coil not energized**

**Load Side:**
1. Starts at contactor output
2. Traces to loads:
   - Motors
   - VFDs
   - Other equipment
3. Shows what loses power if contacts open

## State Propagation

When you change a component, effects propagate:

**Example: Close Contactor K3**

```
1. User toggles -K3
   ↓
2. K3 state changes to ON
   ↓
3. Simulation recalculates
   ↓
4. K3 coil checks if 24VDC present
   ↓
5. If yes → K3 contacts close
   ↓
6. 400VAC flows through contacts
   ↓
7. Downstream loads energize
   ↓
8. GUI updates:
   - K3 turns green
   - Motor turns green
   - Analysis panel updates
```

## Visual Feedback

### Component Colors

- **Green background** - Energized (has voltage)
- **Red background** - De-energized (no voltage)
- **Yellow** - Faulted (future: overload, short)

### Status Messages

- "Toggled K3 → ENERGIZED"
- "Toggled F7 → DE-ENERGIZED (Tripped)"
- "Simulation updated - 5 components changed"

### Real-Time Updates

All panels update immediately:
- Component list refreshes with new colors
- Details panel shows updated state
- Analysis panel shows new circuit state

## Advanced Features

### Comprehensive State Explanation

For complex components like contactors:

```
Component: -K3
Type: contactor
Rated: 400VAC
Status: ENERGIZED

--- COIL CIRCUIT (Control) ---
24VDC Source: -G1
Path: -G1 → -F4 → -Q1 → -K3
Active: YES
Blocking: None

--- MAIN CONTACTS (Power) ---
Supply from: -F7
Supply path: -F7 → -K3
Load to: +DG-M1
Load path: -K3 → -U1 → +DG-M1
Contacts: CLOSED
```

### Fault Detection (Future)

- Detect missing paths
- Identify broken circuits
- Find voltage mismatches
- Warn about overloads

## Testing

Run the interactive simulation test:

```bash
python examples/interactive_simulation_test.py
```

This demonstrates:
- Circuit tracing
- Component toggling
- State explanation
- Real-time updates

## Implementation Details

### Key Classes

**`InteractiveSimulator`**
- Main simulation engine
- Handles both control and power circuits
- BFS-based voltage tracing
- State management

**`InteractivePanel`**
- Qt GUI widget
- Component list with filtering
- Toggle controls
- Detail display

**`CircuitPath`**
- Represents a traced path
- Stores source → destination
- Tracks blocking components
- Active/inactive state

### Circuit Graphs

Two separate NetworkX graphs:

1. **Control Graph** (24VDC)
   - PLCs, sensors, relay coils
   - Edges = control wires

2. **Power Graph** (400VAC/230VAC)
   - Motors, loads, main contacts
   - Edges = power wires

Contactors bridge both graphs:
- Coil in control graph
- Contacts in power graph
- Contacts only close if coil energized

## Visual Overlay System

### Overview

The visual overlay system provides **real-time visual feedback** directly on the PDF diagram, making it easy to see which components are energized at a glance.

### Features

**Color-Coded Component Highlights:**
- **Green overlays** = Component has voltage (energized)
- **Red overlays** = Component has no voltage (de-energized)
- Semi-transparent fills allow you to see the underlying circuit diagram
- Bold borders for clear visibility
- Component designations labeled directly on overlays

**Automatic Page Detection:**
- Overlays only show on the correct page
- Automatically extracts page numbers from DRAWER format
- Navigate pages to see different sections of the circuit

**Real-Time Updates:**
- Toggle a component → Overlays update instantly
- Trip a fuse → Watch downstream components turn red
- Close a contactor → Watch motor turn green
- All changes propagate in real-time

### Usage

**In the GUI:**
```
1. Open DRAWER.pdf
2. Overlays automatically appear on circuit pages
3. Toggle components in middle panel (double-click)
4. Watch PDF overlays update in real-time
5. Use "Show Overlays" button to toggle visibility
6. Zoom in/out to see details
```

**Programmatically:**
```python
# Set overlays on PDF viewer
pdf_viewer.set_component_overlays(
    components=diagram.components,
    energized_ids=energized_component_ids
)

# Toggle overlay visibility
pdf_viewer.toggle_overlays(show=True)

# Clear all overlays
pdf_viewer.clear_overlays()
```

### Examples

**Example 1: Initial State**
- All power sources are green (energized)
- Components without power paths are red
- PLCs and control circuits may be energized (24VDC)
- Motors may be de-energized (waiting for contactors)

**Example 2: Close Contactor K3**
```
Before:
  K3 coil: RED (no 24VDC command)
  K3 contacts: RED (open)
  Motor M1: RED (no power)

Action: Toggle K3 (simulate energizing coil)

After:
  K3 coil: GREEN (24VDC applied)
  K3 contacts: GREEN (closed)
  Motor M1: GREEN (400VAC flowing)
```

**Example 3: Trip Circuit Breaker**
```
Before:
  F7 breaker: GREEN (closed)
  VFD U1: GREEN (has 400VAC)
  Motor M1: GREEN (running)

Action: Toggle F7 (simulate trip)

After:
  F7 breaker: RED (tripped/open)
  VFD U1: RED (lost power)
  Motor M1: RED (stopped)
```

### Technical Details

**Coordinate Mapping:**
- PDF coordinates → Screen coordinates with zoom factor
- Overlays scale with zoom level
- Position calculated: `screen_x = pdf_x * zoom * 2`

**Rendering:**
- QPainter draws semi-transparent rectangles
- Antialiasing for smooth edges
- Z-order: PDF → Overlays → Annotations → Selection

**Performance:**
- Only draws overlays on current page
- Efficient repaint on state changes
- No impact on PDF navigation speed

### Testing

Run the visual overlay test:

```bash
python examples/visual_overlay_test.py
```

This demonstrates:
- Automatic overlay generation
- Real-time state updates
- Component toggling
- Visual feedback on PDF

## Next Steps

The framework now includes:
- ✅ Visual overlay on PDF (highlight energized components)
- ✅ Real-time updates on component toggle
- ✅ Color-coded visualization (green/red)
- ✅ Page-aware overlay positioning

Ready for future enhancements:
- Animation of voltage flow along wires
- Wire path highlighting (trace energized wire segments)
- Current flow calculation and display
- Load analysis visualization
- Fault injection and propagation
- Recording/playback of simulations
- Time-based simulation (switching sequences)

You can now interactively explore your electrical diagrams and understand exactly how voltage flows through your industrial control systems - with **visual feedback directly on the PDF**!
