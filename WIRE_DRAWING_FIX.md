# Wire Drawing Bug Fix Report

## Executive Summary

Wire drawing functionality is **not working** due to several critical bugs in the coordinate system and terminal detection logic. The user cannot draw wires because mouse clicks are not properly detecting terminals.

## Root Cause Analysis

### Bug 1: Terminal Radius Too Small (CRITICAL)
**File**: `electrical_schematics/gui/wire_tool.py` line 45

```python
self.terminal_radius = 10.0  # Terminal detection radius in PDF coordinates
```

**Problem**: The terminal radius of 10.0 PDF units is too small. When scaled through the zoom coordinate system, terminals become nearly impossible to click.

**Impact**: Users cannot start wire drawing because clicks don't register on terminals.

### Bug 2: Coordinate System Confusion
**Files**: `pdf_viewer.py` lines 566-593, `wire_tool.py` lines 273-286

The code has **two different coordinate transformations**:
- PDFViewer converts: `screen = pdf * zoom_level * 2`
- WireTool converts: `screen = pdf * zoom_level * 2`

This creates confusion about what "PDF coordinates" actually means.

**Problem**: Terminal positions are calculated in screen coordinates but compared against PDF coordinates without proper conversion.

### Bug 3: Terminal Detection Logic Issues
**File**: `pdf_viewer.py` line 632-639

```python
if self.wire_drawing_mode or self.wire_tool.is_drawing():
    components = [overlay.component for overlay in self.component_overlays if overlay.page == self.current_page]
    terminal_positions = self._get_all_terminal_positions()

    handled = self.wire_tool.handle_click(pdf_pos, components, terminal_positions)
```

The `_get_all_terminal_positions()` method returns positions in PDF coordinates, but they're calculated from screen coordinates via:

```python
pdf_x = term_pos.x() / (self.zoom_level * 2)
pdf_y = term_pos.y() / (self.zoom_level * 2)
```

This conversion is applied to positions that were **already** in screen coordinates from `_get_terminal_positions()`, effectively double-converting them.

## Detailed Bug Breakdown

### Terminal Position Calculation Flow (CURRENT - BROKEN)

1. **PDFViewer._get_terminal_positions()** (lines 430-491):
   - Takes `rect` in **screen coordinates**
   - Returns terminal positions in **screen coordinates** (QPoint)

2. **PDFViewer._get_all_terminal_positions()** (lines 566-593):
   - Calls `_get_terminal_positions()` with screen rect
   - Gets back screen coordinates
   - **INCORRECTLY** converts screen → PDF by dividing by `zoom_level * 2`
   - This is wrong because screen coords are NOT `pdf * zoom * 2`

3. **WireDrawingTool.handle_click()** (lines 71-115):
   - Receives PDF position from mouse click
   - Receives terminal positions (supposedly in PDF coords)
   - Compares distances directly in PDF space
   - **FAILS** because terminal positions are incorrectly calculated

### Why Clicks Don't Work

When user clicks at screen position (400, 300):
1. PDFViewer converts to PDF: `pdf_x = 400 / (zoom * 2)` = 200 (at 1x zoom)
2. Terminal at component position (100, 100) with rect offset +10:
   - Screen rect is at (100 * 1.0 * 2, 100 * 1.0 * 2) = (200, 200)
   - Terminal screen pos = (210, 200)
   - **Incorrectly** converted to PDF: (210 / 2, 200 / 2) = (105, 100)
3. Distance check:
   - Click PDF pos: (200, 100)
   - Terminal "PDF" pos: (105, 100)
   - Distance = 95 pixels
   - Required radius = 10 pixels
   - **FAIL** - terminal not detected

## The Fix

The solution requires THREE changes:

### Fix 1: Increase Terminal Detection Radius
**File**: `electrical_schematics/gui/wire_tool.py` line 45

```python
# OLD:
self.terminal_radius = 10.0

# NEW:
self.terminal_radius = 20.0  # Larger radius for easier clicking (in PDF coordinates)
```

### Fix 2: Fix Terminal Position Calculation
**File**: `electrical_schematics/gui/pdf_viewer.py` lines 566-593

The `_get_all_terminal_positions()` method needs to be completely rewritten:

```python
def _get_all_terminal_positions(self) -> Dict[str, List[QPointF]]:
    """Get terminal positions for all components in PDF coordinates.

    Returns:
        Dict mapping component_id to list of terminal positions (PDF coords)
    """
    terminal_positions = {}

    for overlay in self.component_overlays:
        if overlay.page == self.current_page:
            # Calculate terminals based on component's PDF position directly
            # NOT by converting screen coordinates
            pdf_terminals = self._get_terminal_positions_pdf(overlay.component)
            terminal_positions[overlay.component.id] = pdf_terminals

    return terminal_positions

def _get_terminal_positions_pdf(self, component: IndustrialComponent) -> List[QPointF]:
    """Calculate terminal positions for a component in PDF coordinates.

    Args:
        component: Component to get terminals for

    Returns:
        List of terminal positions in PDF coordinates
    """
    from electrical_schematics.models import IndustrialComponentType

    terminals = []
    center_x = component.x + component.width / 2
    center_y = component.y + component.height / 2

    # Define terminal positions based on component type (in PDF coords)
    component_type = component.type

    if component_type in [IndustrialComponentType.CONTACTOR, IndustrialComponentType.RELAY]:
        # Contactors/Relays: coil terminals on left, contact terminals on right
        terminals.append(QPointF(component.x + 10, center_y - 10))
        terminals.append(QPointF(component.x + 10, center_y + 10))
        terminals.append(QPointF(component.x + component.width - 10, center_y - 10))
        terminals.append(QPointF(component.x + component.width - 10, center_y + 10))

    elif component_type in [
        IndustrialComponentType.PROXIMITY_SENSOR,
        IndustrialComponentType.PHOTOELECTRIC_SENSOR,
        IndustrialComponentType.LIMIT_SWITCH,
        IndustrialComponentType.PRESSURE_SWITCH,
        IndustrialComponentType.TEMPERATURE_SENSOR
    ]:
        # Sensors: power on left, output on right
        terminals.append(QPointF(component.x + 10, center_y - 10))
        terminals.append(QPointF(component.x + 10, center_y + 10))
        terminals.append(QPointF(component.x + component.width - 10, center_y))

    elif component_type in [IndustrialComponentType.POWER_24VDC, IndustrialComponentType.POWER_400VAC]:
        # Power supplies: positive/L on top, negative/N on bottom
        terminals.append(QPointF(center_x, component.y + 10))
        terminals.append(QPointF(center_x, component.y + component.height - 10))

    elif component_type == IndustrialComponentType.MOTOR:
        # Motors: three-phase terminals at top
        terminals.append(QPointF(center_x - 15, component.y + 10))
        terminals.append(QPointF(center_x, component.y + 10))
        terminals.append(QPointF(center_x + 15, component.y + 10))

    elif component_type in [IndustrialComponentType.PLC_INPUT, IndustrialComponentType.PLC_OUTPUT]:
        # PLC modules: terminals along left edge
        num_terminals = 8
        spacing = component.height / (num_terminals + 1)
        for i in range(num_terminals):
            terminals.append(QPointF(component.x + 10, component.y + spacing * (i + 1)))

    else:
        # Default: two terminals on left and right
        terminals.append(QPointF(component.x + 10, center_y))
        terminals.append(QPointF(component.x + component.width - 10, center_y))

    return terminals
```

### Fix 3: Update _draw_terminals to Use PDF Coordinates
**File**: `electrical_schematics/gui/pdf_viewer.py` lines 405-429

```python
def _draw_terminals(self, painter: QPainter, component: IndustrialComponent, rect: QRectF) -> None:
    """Draw terminal points for a component.

    Args:
        painter: Qt painter
        component: Component to draw terminals for
        rect: Screen coordinates rectangle
    """
    # Get PDF coordinates for terminals
    pdf_terminals = self._get_terminal_positions_pdf(component)

    # Convert to screen coordinates
    screen_terminals = []
    for pdf_term in pdf_terminals:
        screen_x = pdf_term.x() * self.zoom_level * 2
        screen_y = pdf_term.y() * self.zoom_level * 2
        screen_terminals.append(QPointF(screen_x, screen_y))

    # Draw terminal circles with better visibility
    terminal_radius = max(3, 4 * self.zoom_level)  # Scale with zoom, minimum 3

    # Draw outer circle (dark border)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor(0, 0, 0, 200), 2))
    for terminal_pos in screen_terminals:
        painter.drawEllipse(terminal_pos, terminal_radius + 1, terminal_radius + 1)

    # Draw inner circle (yellow fill)
    painter.setBrush(QBrush(QColor(255, 230, 0, 255)))  # Brighter yellow
    painter.setPen(QPen(QColor(200, 180, 0), 1))
    for terminal_pos in screen_terminals:
        painter.drawEllipse(terminal_pos, terminal_radius, terminal_radius)
```

## Testing the Fix

After applying these fixes, test wire drawing:

1. **Load a PDF** with components
2. **Click "Draw Wire"** button - should turn green
3. **Hover over component** - terminals should be visible as yellow circles
4. **Click on a terminal** - should show "Drawing wire..." message
5. **Click another terminal** - wire should be created

### Expected Behavior

- Terminal detection radius: 20 PDF units (approximately 40 screen pixels at 1x zoom)
- Terminals visible as yellow circles with black borders
- Mouse cursor changes to crosshair in wire drawing mode
- Status bar shows "Drawing wire - click to add waypoints, click terminal to complete"

## Verification Steps

Run the test script:

```bash
python test_wire_drawing.py
```

Expected output:
```
=== TEST 3: Wire Drawing ===
✓ Wire tool initialized
✓ Wire type: ('24VDC', QColor(...), '24VDC')
✓ Component K1: 4 terminals
✓ Component S1: 3 terminals
✓ Terminal detected: K1.0
✓ Wire drawing started: True
✓ Waypoint added
✓ Wire created with 3 points
  From: K1
  To: S1

=== TEST 3: PASSED ===
```

## Additional Improvements

### Enhancement 1: Visual Feedback
Add visual indicator when hovering over terminals:

```python
# In PDFViewer._draw_terminals(), highlight hovered terminal
if self.wire_drawing_mode:
    # Check if mouse is near terminal
    if distance_to_terminal < terminal_radius:
        # Draw highlight circle
        painter.setBrush(QBrush(QColor(255, 255, 0, 100)))
        painter.drawEllipse(terminal_pos, terminal_radius * 1.5, terminal_radius * 1.5)
```

### Enhancement 2: Snap to Terminal
When click is close to terminal, snap to exact terminal position:

```python
# In WireDrawingTool.handle_click()
component, terminal_idx = self._find_terminal_at(pdf_pos, components, terminal_positions)
if component and terminal_idx is not None:
    # Use exact terminal position instead of click position
    exact_pos = terminal_positions[component.id][terminal_idx]
    # ... use exact_pos for wire endpoint
```

### Enhancement 3: Cancel on Right-Click
Already implemented in wire_tool.py line 126-135.

## Summary

The wire drawing feature is **completely broken** due to coordinate system confusion. The fixes are:

1. **Increase terminal radius** from 10 to 20 PDF units
2. **Rewrite terminal position calculation** to work directly in PDF coordinates
3. **Update terminal drawing** to convert PDF → screen correctly

These changes will make wire drawing functional and user-friendly.

## Files to Modify

1. `electrical_schematics/gui/wire_tool.py` - Line 45
2. `electrical_schematics/gui/pdf_viewer.py` - Lines 405-491, 566-593

Total changes: ~150 lines across 2 files.
