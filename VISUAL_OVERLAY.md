# Visual Overlay System

## Overview

The **Visual Overlay System** provides real-time visual feedback directly on PDF electrical diagrams, allowing you to see at a glance which components are energized and trace voltage flow through the circuit.

## Key Features

### 1. Real-Time Component Highlighting

- **Green overlays** indicate energized components (voltage present)
- **Red overlays** indicate de-energized components (no voltage)
- Semi-transparent highlighting allows you to see the underlying schematic
- Component designations labeled directly on overlays
- Bold borders for clear visibility at any zoom level

### 2. Interactive Simulation

- Toggle components (contactors, switches, fuses) in the interactive panel
- Watch PDF overlays update instantly in real-time
- See voltage propagation through the circuit
- Understand cause-and-effect relationships visually

### 3. Page-Aware Display

- Overlays automatically positioned on the correct PDF page
- Navigate between pages to see different circuit sections
- Page numbers extracted from DRAWER format metadata
- Only renders overlays for the current page (performance optimized)

### 4. Zoom-Adaptive Rendering

- Overlays scale with zoom level
- Coordinate mapping: PDF space → Screen space
- Smooth antialiased rendering
- Details remain visible at high zoom

## Usage Guide

### Basic Workflow

1. **Open PDF Diagram**
   ```
   Click "Open PDF" → Select DRAWER.pdf
   ```

2. **Automatic Analysis**
   ```
   Application auto-detects DRAWER format
   Parses devices and connections
   Builds circuit graph
   Runs initial simulation
   ```

3. **View Overlays**
   ```
   Navigate to circuit diagram pages
   Green = Components with voltage
   Red = Components without voltage
   ```

4. **Interactive Simulation**
   ```
   Middle panel: Double-click components to toggle
   PDF viewer: Watch overlays update in real-time
   Right panel: See detailed simulation results
   ```

5. **Toggle Visibility**
   ```
   Toolbar: Click "🔍 Show Overlays" to toggle on/off
   Useful when you want to see the original schematic
   ```

### Example Scenarios

#### Scenario 1: Motor Won't Start

**Initial State:**
- Motor M1: **RED** overlay (no power)
- VFD U1: **GREEN** (has power)
- Contactor K3: **RED** (not energized)

**Investigation:**
1. Look at K3 contactor coil - why is it de-energized?
2. Trace 24VDC path to K3 coil
3. Find blocking component (maybe switch S1 is open)

**Action:**
- Double-click S1 to close switch
- Watch K3 coil turn **GREEN**
- Watch K3 contacts close
- Watch motor M1 turn **GREEN**

**Result:** Circuit complete, motor energized!

#### Scenario 2: Circuit Breaker Trip

**Before Trip:**
- F7 breaker: **GREEN** (closed, conducting)
- VFD U1: **GREEN** (has 400VAC)
- Motor M1: **GREEN** (running)
- All downstream components: **GREEN**

**Action: Trip F7**
- Double-click F7 to simulate trip

**After Trip:**
- F7 breaker: **RED** (open, not conducting)
- VFD U1: **RED** (lost power)
- Motor M1: **RED** (stopped)
- All downstream components: **RED**

**Visual Feedback:** Instantly see the impact of a single component failure!

#### Scenario 3: Contactor Energization

**Question:** "Where does contactor K1 get its 24VDC from?"

**Visual Investigation:**
1. Select K1 in component list
2. Click "Trace Circuit"
3. See detailed path in analysis panel
4. On PDF: K1 has **GREEN** overlay if coil is energized

**Trace Result:**
```
Source: -G1 (24VDC Power Supply)
Path: -G1 → -F4 (Fuse) → -Q1 (Switch) → K1 (Coil)
Active: YES (all components conducting)
```

**On PDF:** All components in path have **GREEN** overlays

## Technical Implementation

### Architecture

```
┌─────────────────────────────────────────────┐
│         Interactive Simulator               │
│   - Voltage flow calculation                │
│   - Component state management              │
│   - Circuit path tracing                    │
└──────────────┬──────────────────────────────┘
               │
               │ energized_component_ids
               ▼
┌─────────────────────────────────────────────┐
│           PDF Viewer Widget                 │
│   - set_component_overlays()                │
│   - Coordinate mapping                      │
│   - QPainter rendering                      │
└─────────────────────────────────────────────┘
```

### Component Overlay Class

```python
class ComponentOverlay:
    """Visual overlay for a component."""

    component: IndustrialComponent
    is_energized: bool
    page: int
    rect: QRectF  # Bounding box
```

### Coordinate Transformation

```python
# PDF coordinates (from DRAWER parser)
pdf_x, pdf_y = component.x, component.y

# Screen coordinates (for rendering)
screen_x = pdf_x * zoom_level * 2
screen_y = pdf_y * zoom_level * 2
```

### Rendering Pipeline

1. **Base Layer:** Render PDF page to QPixmap
2. **Overlay Layer:** Draw component overlays
   - Semi-transparent fill (QBrush)
   - Bold border (QPen)
   - Component designation text
3. **Annotation Layer:** Manual annotations (if any)
4. **Selection Layer:** Current selection rectangle

### Color Scheme

```python
# Energized components
fill_color = QColor(0, 255, 0, 60)    # Green, 23% opacity
border_color = QColor(0, 200, 0, 200) # Dark green, 78% opacity

# De-energized components
fill_color = QColor(255, 0, 0, 40)    # Red, 16% opacity
border_color = QColor(200, 0, 0, 150) # Dark red, 59% opacity
```

### Performance Optimizations

- **Page Filtering:** Only render overlays for current page
- **Lazy Update:** Only repaint when simulation state changes
- **Efficient Mapping:** Pre-calculate coordinate transformations
- **Z-Order Rendering:** Minimal overdraw

## API Reference

### PDFViewer Methods

```python
def set_component_overlays(
    self,
    components: List[IndustrialComponent],
    energized_ids: List[str]
) -> None:
    """Set overlays for all components.

    Args:
        components: All components in diagram
        energized_ids: IDs of energized components
    """

def toggle_overlays(self, show: bool) -> None:
    """Show or hide overlays.

    Args:
        show: True to show, False to hide
    """

def clear_overlays(self) -> None:
    """Remove all overlays."""
```

### Integration Example

```python
# In main window, when simulation updates:
def _on_simulation_updated(self):
    # Get energized components
    energized = self.interactive_sim.get_energized_components()
    energized_ids = [comp.id for comp in energized]

    # Update PDF overlays
    self.pdf_viewer.set_component_overlays(
        self.diagram.components,
        energized_ids
    )
```

## Testing

### Manual Testing

```bash
# Run the visual overlay test
python examples/visual_overlay_test.py
```

**Test Checklist:**
- [ ] PDF loads with overlays visible
- [ ] Green overlays on energized components
- [ ] Red overlays on de-energized components
- [ ] Toggle component → Overlay color changes
- [ ] Navigate pages → Overlays follow components
- [ ] Zoom in/out → Overlays scale correctly
- [ ] "Show Overlays" button → Toggle visibility
- [ ] Component designations visible on overlays

### Automated Testing

```python
# Unit test example
def test_overlay_creation():
    component = create_test_component()
    overlay = ComponentOverlay(component, is_energized=True, page=0)

    assert overlay.is_energized == True
    assert overlay.page == 0
    assert overlay.rect.x() == component.x
```

## Future Enhancements

### Wire Path Highlighting

Extend overlays to show energized wire segments:

```python
class WireOverlay:
    """Overlay for an energized wire."""
    wire: Wire
    is_energized: bool
    voltage_type: str  # "24VDC", "400VAC"
    page: int
```

- Draw colored lines along wire paths
- Different colors for voltage levels
- Animated flow direction indicators

### Animation System

Add voltage flow animation:

- Particles flowing from source to load
- Speed indicates current magnitude
- Color indicates voltage type
- Pause/play/step controls

### Fault Visualization

Highlight fault conditions:

- **Yellow** overlays for overload conditions
- **Orange** overlays for voltage mismatches
- **Purple** overlays for open circuits
- Blinking borders for critical faults

### 3D Depth Layers

Show circuit hierarchy:

- Control circuit (24VDC) on top layer
- Power circuit (400VAC) on bottom layer
- Transparency indicates layer depth
- Toggle layer visibility

## Troubleshooting

### Overlays Not Appearing

**Check:**
1. Is "Show Overlays" button checked?
2. Are you on a page with circuit components?
3. Has simulation run at least once?
4. Are component coordinates valid?

**Solution:**
```python
# Verify components have positions
for comp in diagram.components:
    print(f"{comp.designation}: x={comp.x}, y={comp.y}")

# Force simulation update
simulator.simulate_step()
```

### Overlays in Wrong Position

**Check:**
1. Zoom level calculation
2. Coordinate transformation factor
3. PDF page dimensions

**Solution:**
```python
# Adjust coordinate factor in _draw_component_overlay()
screen_x = pdf_x * zoom_level * scale_factor
```

### Performance Issues

**Check:**
1. Number of components
2. Number of overlays per page
3. Repaint frequency

**Solution:**
```python
# Limit overlays to visible area
visible_rect = viewport.rect()
overlays = [o for o in overlays if o.rect.intersects(visible_rect)]
```

## Conclusion

The Visual Overlay System transforms the electrical schematic analyzer from a simulation tool into an **interactive learning and diagnostic platform**. By providing immediate visual feedback directly on the PDF diagram, users can:

- Quickly understand circuit behavior
- Identify problems at a glance
- Learn voltage flow patterns
- Debug complex industrial systems
- Train operators and technicians

The system bridges the gap between abstract simulation results and concrete visual understanding, making electrical diagnostics accessible and intuitive.

---

**Ready to explore your circuits visually!** 🔍⚡
