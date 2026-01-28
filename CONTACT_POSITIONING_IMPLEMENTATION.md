# Contact Positioning Implementation Summary

## Status: PARTIALLY COMPLETE

### Completed
1. ✅ **Diagnostic Analysis** - Identified root cause
2. ✅ **ComponentPositionFinder Update** - Added `find_contact_positions()` method
3. ✅ **Testing** - Verified contact detection works correctly

### Test Results
```
Contact suffix .0: Found 3 positions  (likely coil references)
Contact suffix .1: Found 12 positions (first auxiliary contact 13-14)
Contact suffix .2: Found 12 positions (second contact 23-24 or 21-22)
Contact suffix .3: Found 13 positions (third contact 33-34 or 31-32)
```

## Remaining Implementation

### 1. Update IndustrialComponent Model
**File**: `/home/liam-oreilly/claude.projects/electricalSchematics/electrical_schematics/models/industrial_component.py`

Add to IndustrialComponent class (around line 162):

```python
# Contact instance positions (for relays/contactors)
# Key: contact suffix (e.g., '.1', '.2', '.3')
# Value: Dict[page, PagePosition] - positions on each page
contact_positions: Dict[str, Dict[int, PagePosition]] = field(default_factory=dict)

def add_contact_position(
    self,
    contact_suffix: str,  # e.g., '.1', '.2', '.3'
    page: int,
    x: float,
    y: float,
    width: float,
    height: float,
    confidence: float = 1.0
) -> None:
    """Add position for a contact instance on a specific page.
    
    Args:
        contact_suffix: Contact instance suffix (e.g., '.1', '.2')
        page: PDF page number (0-indexed)
        x, y: Position in PDF points
        width, height: Size in PDF points
        confidence: Match confidence
    """
    if contact_suffix not in self.contact_positions:
        self.contact_positions[contact_suffix] = {}
    
    self.contact_positions[contact_suffix][page] = PagePosition(
        page=page,
        x=x,
        y=y,
        width=width,
        height=height,
        confidence=confidence
    )

def get_contact_position(
    self,
    contact_suffix: str,
    page: int
) -> Optional[PagePosition]:
    """Get position of a contact instance on a specific page.
    
    Args:
        contact_suffix: Contact instance (e.g., '.1')
        page: PDF page number
        
    Returns:
        PagePosition if contact found on page, None otherwise
    """
    if contact_suffix in self.contact_positions:
        return self.contact_positions[contact_suffix].get(page)
    return None
```

### 2. Update Auto Loader
**File**: `/home/liam-oreilly/claude.projects/electricalSchematics/electrical_schematics/pdf/auto_loader.py`
or
**File**: `/home/liam-oreilly/claude.projects/electricalSchematics/electrical_schematics/pdf/drawer_to_model.py`

After creating components, populate contact positions:

```python
def populate_contact_positions(
    components: List[IndustrialComponent],
    pdf_path: Path
) -> None:
    """Populate contact positions for relays and contactors.
    
    Args:
        components: List of components
        pdf_path: Path to PDF
    """
    from electrical_schematics.pdf.component_position_finder import ComponentPositionFinder
    from electrical_schematics.models import IndustrialComponentType
    
    with ComponentPositionFinder(pdf_path) as finder:
        for component in components:
            # Only process relays and contactors
            if component.type not in [
                IndustrialComponentType.RELAY,
                IndustrialComponentType.CONTACTOR
            ]:
                continue
            
            # Find contact positions
            contact_pos_dict = finder.find_contact_positions(component.designation)
            
            for suffix, positions in contact_pos_dict.items():
                for pos in positions:
                    component.add_contact_position(
                        suffix,
                        pos.page,
                        pos.x,
                        pos.y,
                        pos.width,
                        pos.height,
                        pos.confidence
                    )

# Call this after creating components:
# populate_contact_positions(components, pdf_path)
```

### 3. Update PDF Viewer
**File**: `/home/liam-oreilly/claude.projects/electricalSchematics/electrical_schematics/gui/pdf_viewer.py`

Add after `_draw_component_overlay` method (around line 401):

```python
def _draw_component_overlay(self, painter: QPainter, overlay: ComponentOverlay) -> None:
    """Draw a component overlay on the PDF."""
    # ... existing coil/device rendering code ...
    
    # Draw contact instances if this is a relay/contactor
    if overlay.component.contact_positions:
        self._draw_contact_instances(painter, overlay)

def _draw_contact_instances(
    self,
    painter: QPainter,
    overlay: ComponentOverlay
) -> None:
    """Draw contact symbols at their actual positions on the schematic.
    
    Args:
        painter: Qt painter
        overlay: Component overlay with contact positions
    """
    component = overlay.component
    
    # Only draw contacts on current page
    for contact_suffix, page_positions in component.contact_positions.items():
        if self.current_page not in page_positions:
            continue
        
        pos = page_positions[self.current_page]
        
        # Convert to screen coordinates
        screen_rect = QRectF(
            pos.x * self.zoom_level * 2,
            pos.y * self.zoom_level * 2,
            pos.width * self.zoom_level * 2,
            pos.height * self.zoom_level * 2
        )
        
        # Get contact block info
        contact_block = self._get_contact_block_for_suffix(
            component, contact_suffix
        )
        
        # Draw contact symbol
        self._draw_contact_symbol(
            painter,
            screen_rect,
            contact_block,
            overlay.is_energized,
            label=f"{component.designation}{contact_suffix}"
        )

def _get_contact_block_for_suffix(
    self,
    component: IndustrialComponent,
    suffix: str
) -> ContactBlock:
    """Map contact suffix to ContactBlock.
    
    Industrial relay contact numbering:
    - .0 = Coil (skip, or special case)
    - .1 = First auxiliary contact (13-14 NO or 11-12 NC)
    - .2 = Second contact (23-24 NO or 21-22 NC)
    - .3 = Third contact (33-34 NO or 31-32 NC)
    
    Args:
        component: Component with contact blocks
        suffix: Contact suffix (e.g., '.1', '.2')
        
    Returns:
        ContactBlock for this contact
    """
    from electrical_schematics.models import ContactBlock, ContactType
    
    # Skip .0 (coil reference)
    if suffix == '.0':
        return ContactBlock("A1", "A2", ContactType.NO, label="Coil")
    
    # Map suffix to contact block index
    suffix_map = {
        '.1': 0,
        '.2': 1,
        '.3': 2,
        '.4': 3,
    }
    
    idx = suffix_map.get(suffix, 0)
    
    # Return existing contact block if available
    if idx < len(component.contact_blocks):
        return component.contact_blocks[idx]
    
    # Generate default NO contact using IEC numbering
    terminal_from = f"{(idx + 1) * 10 + 3}"  # 13, 23, 33, 43...
    terminal_to = f"{(idx + 1) * 10 + 4}"    # 14, 24, 34, 44...
    
    return ContactBlock(
        terminal_from,
        terminal_to,
        ContactType.NO,
        label=f"{component.designation}:{terminal_from}-{terminal_to}"
    )

def _draw_contact_symbol(
    self,
    painter: QPainter,
    rect: QRectF,
    contact_block: ContactBlock,
    coil_energized: bool,
    label: str
) -> None:
    """Draw a contact symbol (NO or NC) at a specific position.
    
    Args:
        painter: Qt painter
        rect: Rectangle in screen coordinates
        contact_block: Contact configuration
        coil_energized: Whether parent coil is energized
        label: Contact label to display
    """
    from electrical_schematics.models import ContactType
    
    # Contact state depends on coil energization
    is_closed = contact_block.get_state_for_coil(coil_energized)
    
    # Choose color based on state
    if is_closed:
        color = QColor(39, 174, 96, 200)  # Green - conducting
        border = QColor(27, 79, 114, 255)
    else:
        color = QColor(149, 165, 166, 120)  # Gray - open
        border = QColor(93, 109, 126, 255)
    
    # Draw contact rectangle
    painter.setBrush(QBrush(color))
    painter.setPen(QPen(border, 2))
    painter.drawRect(rect)
    
    # Draw contact symbol inside
    cx = rect.center().x()
    cy = rect.center().y()
    
    if contact_block.contact_type == ContactType.NO:
        # NO contact: vertical line with gap
        gap = 8 if not is_closed else 0
        painter.setPen(QPen(QColor(44, 62, 80), 3))
        painter.drawLine(
            QPointF(cx, rect.top() + 5),
            QPointF(cx, cy - gap)
        )
        painter.drawLine(
            QPointF(cx, cy + gap),
            QPointF(cx, rect.bottom() - 5)
        )
    
    elif contact_block.contact_type == ContactType.NC:
        # NC contact: line with slash
        painter.setPen(QPen(QColor(44, 62, 80), 3))
        if is_closed:
            # Open (slash away from line)
            painter.drawLine(
                QPointF(cx, rect.top() + 5),
                QPointF(cx, cy - 8)
            )
            painter.drawLine(
                QPointF(cx, cy + 8),
                QPointF(cx, rect.bottom() - 5)
            )
        else:
            # Closed (straight line with diagonal)
            painter.drawLine(
                QPointF(cx, rect.top() + 5),
                QPointF(cx, rect.bottom() - 5)
            )
            painter.drawLine(
                QPointF(cx - 5, cy - 5),
                QPointF(cx + 5, cy + 5)
            )
    
    # Draw label
    font = QFont("Arial", 8)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QPen(QColor(44, 62, 80)))
    
    label_rect = QRectF(rect.x(), rect.bottom() + 2, rect.width(), 15)
    painter.drawText(label_rect, Qt.AlignCenter, label)
```

## Integration Points

### In auto_loader.py
After line where diagram is created, add:
```python
# Populate contact positions for relays/contactors
if hasattr(diagram, 'components'):
    populate_contact_positions(diagram.components, pdf_path)
```

## Testing Checklist

After implementing all changes:

1. Load DRAWER.pdf
2. Navigate to Page 9 (UI shows "Page 10")
3. Verify rendering:
   - [ ] Coil `-K1` appears at (266.3, 433.0)
   - [ ] Contact `-K1.1` appears at (552.2, 597.0)
   - [ ] Contact `-K1.2` appears at (688.2, 597.0)
   - [ ] Contact `-K1.3` appears at (756.2, 597.0)
4. Check contact symbols are distinct from coil
5. Toggle relay state, verify contacts change appearance
6. Test multi-page (Page 10, 11, etc.)

## Contact Symbol Reference

IEC 60947 Standard:
- **NO (13-14)**: ─ | ─ (gap when open, closed when energized)
- **NC (21-22)**: ─/─ (straight with slash, opens when energized)
- **Terminals**: Yellow circles at connection points
- **Labels**: Device tag with suffix (e.g., "-K1.1")

## Files Modified

1. ✅ `electrical_schematics/pdf/component_position_finder.py` - Added contact finding
2. ⏳ `electrical_schematics/models/industrial_component.py` - Add contact_positions field
3. ⏳ `electrical_schematics/pdf/auto_loader.py` - Populate contact positions
4. ⏳ `electrical_schematics/gui/pdf_viewer.py` - Render contact symbols

## Next Steps

Complete implementation of steps 2-4 above, then run tests to verify contacts align correctly with schematic positions.

