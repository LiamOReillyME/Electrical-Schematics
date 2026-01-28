# Wire Drawing User Guide

## Overview

The wire drawing feature allows you to manually connect components on your electrical schematic by drawing colored wires between terminals. This is useful for:

- Creating custom circuit connections
- Documenting wire paths on imported PDFs
- Visualizing signal flow between components
- Annotating existing schematics

## How to Draw Wires

### Step 1: Enable Wire Drawing Mode

Click the **"Draw Wire"** button in the toolbar. The button will turn green with a bold border to indicate that wire drawing mode is active.

![Wire Mode Button](docs/images/wire-mode-button.png)

**Visual Indicators:**
- Button changes to green background
- Status bar shows: "Wire drawing mode enabled - Click on a terminal to start drawing"
- Mouse cursor changes to crosshair (✛)

### Step 2: Select Wire Type

Choose the type of wire you want to draw using the wire type buttons:

| Button | Type | Color | Use Case |
|--------|------|-------|----------|
| **24VDC** | 24V DC Power | Red | Control circuit power |
| **0V** | Ground/Return | Blue | Control circuit ground |
| **AC** | AC Power | Gray/Black | Main power circuits |

**Note:** The selected wire type button will be highlighted with the corresponding color.

### Step 3: Start Drawing

1. **Hover over a component** - yellow terminal circles will appear
2. **Click on a terminal** to start the wire
3. Status bar shows: "Drawing wire - click to add waypoints, click terminal to complete"

**What happens:**
- The starting terminal is captured
- A dashed line preview appears from the terminal to your cursor
- The starting component is locked in

### Step 4: Add Waypoints (Optional)

To route the wire around obstacles or create neat paths:

1. **Click anywhere on the PDF** (not on a terminal) to add a waypoint
2. The wire path will snap to that point
3. Status bar updates: "Added waypoint 1 - click terminal to complete or add more waypoints"
4. You can add multiple waypoints by clicking multiple times

**Waypoints:**
- Appear as small colored circles along the wire path
- Allow you to create right-angle bends
- Help route wires neatly around components

### Step 5: Complete the Wire

1. **Hover over the destination component** - terminals appear
2. **Click on a terminal** to complete the wire
3. The wire is drawn with the selected color
4. Status bar shows: "Wire completed: [type] from [component] to [component]"

**What happens:**
- Wire is saved to the diagram
- Wire appears as a solid colored line
- Connection circles appear at both endpoints
- Wire drawing mode remains active for drawing more wires

### Canceling Wire Drawing

**While drawing a wire:**
- **Right-click** anywhere to cancel the current wire
- **Press ESC** to cancel the current wire
- All waypoints are discarded
- Status bar shows: "Wire drawing cancelled"

**To exit wire drawing mode:**
- Click the **"Draw Wire"** button again (it will turn gray)
- Status bar shows: "Wire drawing mode disabled"

## Terminal Detection

### How Terminals Are Located

Components have predefined terminal positions based on their type:

**Contactors/Relays** (4 terminals):
- Left side: Coil terminals (top and bottom)
- Right side: Contact terminals (top and bottom)

**Sensors** (3 terminals):
- Left side: Power terminals (top and bottom)
- Right side: Output terminal (center)

**Power Supplies** (2 terminals):
- Top: Positive/Line
- Bottom: Negative/Neutral

**Motors** (3 terminals):
- Top: Three-phase connections (L1, L2, L3)

**PLC Modules** (8 terminals):
- Left edge: Evenly spaced along height

**Default Components** (2 terminals):
- Left center: Input
- Right center: Output

### Terminal Detection Radius

The system detects terminal clicks within a **20 PDF unit radius** (approximately 40 pixels at 1x zoom). This makes terminals easy to click even when zoomed out.

**Visual feedback when hovering:**
- Terminals appear as yellow circles with black borders
- Radius scales with zoom level (bigger when zoomed in)
- Brighter yellow fill when hovering

## Wire Colors and Voltage Levels

Wires are automatically color-coded based on their type:

| Voltage Level | Display Color | RGB | Notes |
|---------------|---------------|-----|-------|
| 24VDC | Red | (231, 76, 60) | Standard control circuit |
| 0V | Blue | (52, 152, 219) | Ground/return path |
| AC Power | Dark Gray | (44, 62, 80) | Main power lines |
| Unknown | Gray | (149, 165, 166) | Unspecified voltage |

## Advanced Features

### Multi-Point Routing

Create complex wire paths with multiple bends:

```
Component A ──┐
              │ Waypoint 1
              │
              └──┐
                 │ Waypoint 2
                 │
                 └─→ Component B
```

**Example: Routing around obstacles**
1. Start at component A terminal
2. Click waypoint to the right of A
3. Click waypoint above obstacle
4. Click waypoint to the left of B
5. End at component B terminal

Result: Clean wire path that avoids other components.

### Wire Preview

While drawing, you'll see a **dashed line** preview showing where the wire will go. This helps you:
- Visualize the final wire path
- Ensure you're clicking the correct terminal
- Plan waypoint positions

### Zoom and Wire Drawing

Wire drawing works at any zoom level:

- **Zoomed out (0.5x - 1.0x)**: Better for long-distance connections
- **Zoomed in (1.5x - 5.0x)**: Better for precise terminal selection

**Tip:** Terminal circles scale with zoom, so they're easier to see when zoomed in.

## Troubleshooting

### Problem: Can't Click Terminals

**Solution 1: Check Wire Drawing Mode**
- Ensure "Draw Wire" button is highlighted (green)
- Status bar should say "Wire drawing mode enabled"

**Solution 2: Look for Terminal Circles**
- Hover over component to see yellow terminal circles
- If no circles appear, component may not have terminals defined
- Try zooming in for better visibility

**Solution 3: Terminal Detection Radius**
- Click directly on the yellow circle
- Don't click too far from the terminal center
- Detection radius is 20 PDF units (~40 screen pixels at 1x zoom)

### Problem: Wire Won't Complete

**Possible causes:**
1. **Clicking on same component** - wires must connect different components
2. **Clicking empty space** - adds waypoint instead of completing
3. **Clicking component body** - must click on terminal (yellow circle)

**Solution:** Ensure you're clicking a terminal on a **different** component than the start.

### Problem: Wrong Wire Color

**Solution:** Select the correct wire type button **before** starting to draw:
- Click "24VDC" for red wires
- Click "0V" for blue wires
- Click "AC" for gray wires

**Note:** You cannot change wire color after it's drawn. Delete and redraw if needed.

### Problem: Accidentally Started Wire

**Solution:** Right-click or press ESC to cancel. The wire and all waypoints will be discarded.

## Best Practices

### Organized Wiring

1. **Use waypoints** to create neat right-angle bends
2. **Group wires by type** (e.g., all 24VDC wires together)
3. **Avoid diagonal lines** when possible - use horizontal and vertical segments
4. **Leave space** around components for wire routing

### Wire Routing Tips

- **Power wires first** - route high-power connections before control signals
- **Signal wires next** - add control and sensor connections
- **Ground wires last** - complete return paths

### Color Coding Standards

Follow industrial electrical standards:
- **Red** = Positive DC voltage (24VDC)
- **Blue** = Negative/Ground (0V)
- **Black** = AC Hot (or use gray for visual contrast)

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Cancel wire drawing | **ESC** or **Right-click** |
| Exit wire mode | Click "Draw Wire" button |
| Delete component (and wires) | **Delete** key |

## Example Workflows

### Simple Point-to-Point Connection

1. Click "Draw Wire" → Green highlight appears
2. Select "24VDC" → Red button highlights
3. Click terminal on -A1 (PLC)
4. Click terminal on K1 (contactor coil)
5. Wire appears in red

**Result:** Direct wire from PLC output to contactor coil

### Complex Multi-Point Route

1. Click "Draw Wire" → Enable mode
2. Select "0V" → Blue wire type
3. Click left terminal on S1 (sensor)
4. Click waypoint at (150, 100) → Corner 1
5. Click waypoint at (150, 200) → Corner 2
6. Click waypoint at (250, 200) → Corner 3
7. Click terminal on -A1 (PLC ground)
8. Wire appears with 3 bends

**Result:** Ground wire routed neatly around components

## Future Enhancements

Potential features in development:
- **Wire labels** - add text annotations to wires
- **Wire highlighting** - click wire to highlight circuit path
- **Auto-routing** - automatic waypoint generation
- **Wire bundling** - group multiple wires together
- **Import from CAD** - load wires from electrical CAD files

## Support

If wire drawing still doesn't work after trying these steps:

1. Check console output for error messages
2. Verify components have defined positions (x, y, width, height)
3. Ensure PDF is loaded and visible
4. Try restarting the application

For bug reports, include:
- Screenshot of the issue
- Steps to reproduce
- Console error messages (if any)
- Component types being connected
