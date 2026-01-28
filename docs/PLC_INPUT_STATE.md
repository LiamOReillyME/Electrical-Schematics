# PLC INPUT STATE Component

## Overview

The **PLC INPUT STATE** component is a toggleable indicator that simulates PLC digital input signals. It provides visual feedback with LED-style indicators and can be used to test relay logic sequences in your electrical schematics.

## Features

- **LED Indicator**: Visual state feedback
  - Green LED when ON (energized)
  - Gray LED when OFF (de-energized)
- **Toggleable**: Double-click or use the interactive panel to toggle ON/OFF
- **PLC Address Display**: Shows the PLC input address (e.g., `I0.0`, `%IX0.0`)
- **Drag and Drop**: Can be placed on PDF schematics via component palette
- **Simulation Integration**: Behaves like a physical input switch in the voltage simulator

## Component Type

```python
IndustrialComponentType.PLC_INPUT_STATE = "plc_input_state"
```

## Creating PLC Input State Components

### Programmatically

```python
from electrical_schematics.models import (
    IndustrialComponent,
    IndustrialComponentType,
    SensorState
)

# Create a normally-open (NO) start button input
start_input = IndustrialComponent(
    id="plc_i0_0",
    type=IndustrialComponentType.PLC_INPUT_STATE,
    designation="I0.0",
    voltage_rating="24VDC",
    description="Start button - PLC Input",
    state=SensorState.OFF,  # Initially OFF
    normally_open=True      # NO contact
)

# Create a normally-closed (NC) stop button input
stop_input = IndustrialComponent(
    id="plc_i0_1",
    type=IndustrialComponentType.PLC_INPUT_STATE,
    designation="I0.1",
    voltage_rating="24VDC",
    description="Stop button - PLC Input",
    state=SensorState.ON,   # Initially ON (not pressed)
    normally_open=False     # NC contact
)
```

### Via Component Palette

1. Open the component palette in the GUI
2. Search for "PLC Input State" or "PLC_INPUT_STATE"
3. Drag the component onto your PDF schematic
4. Position it where you want the PLC input indicator
5. Set the PLC address and other properties

## Visual Symbol

The PLC input state symbol consists of:

- **Body Rectangle**: Rounded rectangle container
- **LED Indicator**: Circle on the left showing state
  - Green = ON (conducting, energized)
  - Gray = OFF (not conducting, de-energized)
- **Address Label**: PLC input address (e.g., "I0.0")
- **Designation**: Component designation below the symbol
- **Terminal**: Connection terminal on the right side

### Symbol Generation

```python
from electrical_schematics.gui.electrical_symbols import get_component_symbol

# Generate symbol in OFF state
svg_off = get_component_symbol(
    component_type="plc_input_state",
    designation="I0.0",
    address="I0.0",
    state=False  # OFF state
)

# Generate symbol in ON state
svg_on = get_component_symbol(
    component_type="plc_input_state",
    designation="I0.1",
    address="I0.1",
    state=True  # ON state
)
```

## Usage in Simulation

### Toggling State

The PLC input state component can be toggled using the interactive simulator:

```python
from electrical_schematics.simulation.interactive_simulator import InteractiveSimulator

# Create simulator
simulator = InteractiveSimulator(diagram)

# Toggle PLC input I0.0 (OFF -> ON)
simulator.toggle_component("I0.0")

# Toggle PLC input I0.1 (ON -> OFF)
simulator.toggle_component("I0.1")
```

### Double-Click Interaction

In the GUI, users can double-click on a PLC input state component to toggle its state. The LED indicator will update immediately to show the new state.

### Simulation Behavior

PLC input state components behave like sensors in the simulation:

- **Normally Open (NO)**: Conducts when state is ON
- **Normally Closed (NC)**: Conducts when state is OFF
- **State affects voltage flow**: Downstream components (relays, contactors) are energized/de-energized based on PLC input states

## Common Use Cases

### 1. Start/Stop Motor Control

```python
# Circuit: Start Button (NO) + Stop Button (NC) -> Contactor -> Motor
# When Start is pressed AND Stop is not pressed, motor runs

plc_start = IndustrialComponent(
    id="i0_0",
    type=IndustrialComponentType.PLC_INPUT_STATE,
    designation="I0.0",
    state=SensorState.OFF,
    normally_open=True  # NO
)

plc_stop = IndustrialComponent(
    id="i0_1",
    type=IndustrialComponentType.PLC_INPUT_STATE,
    designation="I0.1",
    state=SensorState.ON,  # Not pressed initially
    normally_open=False     # NC
)
```

### 2. Safety Interlock Simulation

```python
# Emergency stop as NC input
e_stop = IndustrialComponent(
    id="i0_7",
    type=IndustrialComponentType.PLC_INPUT_STATE,
    designation="I0.7",
    description="Emergency Stop",
    state=SensorState.ON,  # Not pressed
    normally_open=False     # NC
)
```

### 3. Sensor Simulation

```python
# Simulate a proximity sensor connected to PLC input
proximity = IndustrialComponent(
    id="i1_0",
    type=IndustrialComponentType.PLC_INPUT_STATE,
    designation="I1.0",
    description="Part present sensor",
    state=SensorState.OFF,  # No part detected
    normally_open=True      # NO
)
```

## Integration with Component Palette

To add PLC input state components to the component palette:

1. **Add to Database**: Add a component template with type `plc_input_state`
2. **Set Default Properties**:
   - Category: "Control" or "PLC"
   - Subcategory: "Inputs"
   - Designation Prefix: "I"
   - Default Voltage: "24VDC"
   - Component Type: "plc_input_state"

Example database template:

```python
from electrical_schematics.database.manager import ComponentTemplate

template = ComponentTemplate(
    id=None,
    category="PLC",
    subcategory="Inputs",
    name="PLC Input State Indicator",
    designation_prefix="I",
    component_type="plc_input_state",
    default_voltage="24VDC",
    description="Toggleable PLC digital input state indicator",
    manufacturer=None,
    part_number=None,
    datasheet_url=None
)
```

## Interactive Panel Display

When a PLC input state component is selected in the interactive panel:

- **State Indicator**: Shows current state (ON/OFF) with color coding
  - Green background = ON (energized)
  - Red background = OFF (de-energized)
- **Toggle Button**: Click to toggle state
- **Details Panel**: Shows:
  - Component type
  - PLC address
  - Current state
  - Normally open/closed configuration
  - Downstream components affected

## Example Circuit

See `examples/plc_input_state_demo.py` for a complete working example demonstrating:

- Creating PLC input state components
- Setting up a start/stop motor control circuit
- Toggling inputs to simulate button presses
- Observing effects on contactors and motors

## Testing

Run the demo script to verify PLC input state functionality:

```bash
python examples/plc_input_state_demo.py
```

Expected output shows:
- Initial circuit state
- Effects of pressing start button
- Effects of pressing stop button
- Motor running/stopped based on input states
- Symbol generation with correct LED colors

## Technical Details

### File Locations

- **Component Type Definition**: `electrical_schematics/models/industrial_component.py`
- **Symbol Generation**: `electrical_schematics/gui/electrical_symbols.py`
- **Simulation Logic**: `electrical_schematics/simulation/interactive_simulator.py`
- **Demo Script**: `examples/plc_input_state_demo.py`

### Key Methods

- `create_plc_input_state_symbol()` - Generate SVG symbol
- `is_sensor()` - Returns True for PLC_INPUT_STATE
- `is_energized()` - Checks if input conducts based on state/NO/NC
- `toggle_component()` - Toggle PLC input state

### Component Properties

| Property | Type | Description |
|----------|------|-------------|
| `type` | `IndustrialComponentType.PLC_INPUT_STATE` | Component type |
| `designation` | `str` | PLC address (e.g., "I0.0") |
| `state` | `SensorState` | Current state (ON/OFF/UNKNOWN) |
| `normally_open` | `bool` | True for NO, False for NC |
| `voltage_rating` | `str` | Usually "24VDC" |
| `description` | `str` | Human-readable description |

## Best Practices

1. **Use Clear Naming**: Use PLC addresses as designations (I0.0, %IX0.0, etc.)
2. **Set Initial States**: Always set initial state explicitly
3. **Document NO/NC**: Clearly indicate if input is NO or NC
4. **Group by Function**: Group related inputs (all start buttons, all stops, etc.)
5. **Voltage Consistency**: Use 24VDC for control circuits
6. **Add Descriptions**: Include functional descriptions for clarity

## Future Enhancements

Potential improvements for PLC input state components:

- **Multi-channel PLC modules**: Show 8 inputs in one component
- **Analog inputs**: Support for 4-20mA, 0-10V analog signals
- **Force values**: Ability to force inputs for testing
- **Historical state**: Track state changes over time
- **PLC program integration**: Connect to actual PLC programs for verification
- **Batch toggle**: Toggle multiple inputs at once
- **Keyboard shortcuts**: Quick toggle via keyboard (e.g., F1-F8)

## Troubleshooting

### Issue: PLC input doesn't affect downstream components

**Solution**: Check that:
- Wire connections are correct
- Voltage levels match (24VDC control circuit)
- Component `normally_open` flag is set correctly
- Simulator has been refreshed with `simulate_step()`

### Issue: LED indicator doesn't update after toggle

**Solution**: Ensure:
- GUI is using latest component state
- `_update_display()` is called after state change
- Overlay system is enabled

### Issue: Cannot find PLC_INPUT_STATE in palette

**Solution**:
- Add component template to database
- Refresh component palette
- Check component type matches exactly: "plc_input_state"

## See Also

- [Interactive Simulation Guide](INTERACTIVE_SIMULATION.md)
- [Visual Overlay System](VISUAL_OVERLAY.md)
- [Component Palette Documentation](component_palette.md)
- [Example Scripts](../examples/)
