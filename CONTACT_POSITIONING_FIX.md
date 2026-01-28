# Contact Positioning Fix

## Issue Description
User reports: "contacts do not line up with devices"

Contacts for relays/contactors (e.g., -K1.1, -K1.2) are not being positioned correctly on schematics.

## Root Cause Analysis

### What We Found
1. **Relays appear on multiple pages** - e.g., -K1 appears on 10 different pages
2. **Contact notation uses instance numbers** - Contacts are labeled as:
   - `-K1` = Coil (with terminals A1-A2)
   - `-K1.1` = First contact (terminals 13-14)
   - `-K1.2` = Second contact (terminals 23-24 or 21-22)
   - `-K1.3` = Third contact (terminals 33-34 or 31-32)

3. **Current behavior**:
   - `component_position_finder.py` finds ALL occurrences of `-K1` (both coil and contacts)
   - Stores them as `page_positions` on the single `-K1` component
   - `pdf_viewer.py` renders the same coil symbol at every position
   - Contact symbols (`.1`, `.2`, `.3`) are never detected or rendered

4. **Example from DRAWER.pdf**:
   ```
   Page 9:
     -K1      at (266.3, 433.0)  <- Coil position
     -K1.1    at (552.2, 597.0)  <- Contact 1 position  
     -K1.2    at (688.2, 597.0)  <- Contact 2 position
     -K1.3    at (756.2, 597.0)  <- Contact 3 position
   
   Page 10:
     -K1      at (130.3, 495.0)  <- Coil position
     -K1.1    at (127.0, 585.7)  <- Contact 1 position
     -K1.2    at (455.8, 585.7)  <- Contact 2 position
     -K1.3    at (648.5, 585.7)  <- Contact 3 position
   ```

## The Problem

The system currently:
1. Finds `-K1` text at 10 locations across pages
2. Stores all 10 as positions of the `-K1` component
3. Renders the coil symbol at all 10 locations

But it **doesn't**:
1. Find `-K1.1`, `-K1.2`, `-K1.3` as separate contact positions
2. Distinguish coil positions from contact positions
3. Render contact symbols at the `.1`, `.2`, `.3` locations

## Solution

We need to:

### 1. Update ComponentPositionFinder
Detect contact instance references (`.1`, `.2`, `.3` suffixes):

```python
def find_contact_positions(
    self,
    device_tag: str,
    page_range: Optional[Tuple[int, int]] = None
) -> Dict[str, List[ComponentPosition]]:
    """Find positions of device contacts.
    
    For device -K1, finds:
    - -K1.1, -K1.2, -K1.3 (contact instances)
    
    Returns dict mapping contact suffix to positions:
    {'.1': [pos1, pos2, ...], '.2': [...], '.3': [...]}
    """
```

### 2. Update IndustrialComponent Model
Add contact position tracking:

```python
@dataclass
class IndustrialComponent:
    # Existing fields...
    
    # Contact instance positions
    # Key: contact suffix (e.g., '.1', '.2')
    # Value: Dict[page, PagePosition]
    contact_positions: Dict[str, Dict[int, PagePosition]] = field(default_factory=dict)
    
    def add_contact_position(
        self,
        contact_suffix: str,  # e.g., '.1'
        page: int,
        x: float,
        y: float,
        width: float,
        height: float,
        confidence: float = 1.0
    ) -> None:
        """Add position for a contact instance."""
```

### 3. Update Auto Loader
Parse contact instances when loading DRAWER diagrams:

```python
# In drawer_to_model.py or auto_loader.py

for component in components:
    if component.type in [RELAY, CONTACTOR]:
        # Find contact positions
        contact_positions = position_finder.find_contact_positions(
            component.designation
        )
        
        for suffix, positions in contact_positions.items():
            for pos in positions:
                component.add_contact_position(
                    suffix, pos.page, pos.x, pos.y,
                    pos.width, pos.height, pos.confidence
                )
```

### 4. Update PDF Viewer Rendering
Render contacts at their specific positions:

```python
# In pdf_viewer.py

def _draw_component_overlay(self, painter: QPainter, overlay: ComponentOverlay):
    """Draw component overlay including contacts."""
    
    # Draw coil/device at primary position
    # ... existing code ...
    
    # Draw contacts at their instance positions
    if overlay.component.contact_positions:
        self._draw_contact_instances(painter, overlay)

def _draw_contact_instances(
    self,
    painter: QPainter,
    overlay: ComponentOverlay
) -> None:
    """Draw contact symbols at their actual positions."""
    
    component = overlay.component
    
    # Only draw contacts on current page
    for contact_suffix, page_positions in component.contact_positions.items():
        if self.current_page in page_positions:
            pos = page_positions[self.current_page]
            
            # Convert to screen coordinates
            screen_rect = QRectF(
                pos.x * self.zoom_level * 2,
                pos.y * self.zoom_level * 2,
                pos.width * self.zoom_level * 2,
                pos.height * self.zoom_level * 2
            )
            
            # Determine contact type from suffix
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
    """Map contact suffix (.1, .2, .3) to ContactBlock."""
    # .1 = first contact (13-14 NO)
    # .2 = second contact (23-24 NO or 21-22 NC)
    # .3 = third contact (33-34 NO or 31-32 NC)
    
    suffix_map = {
        '.1': 0,
        '.2': 1,
        '.3': 2,
        '.4': 3,
    }
    
    idx = suffix_map.get(suffix, 0)
    if idx < len(component.contact_blocks):
        return component.contact_blocks[idx]
    
    # Default NO contact
    return ContactBlock(
        f"{idx}3",
        f"{idx}4",
        ContactType.NO,
        label=f"{component.designation}:{idx}3-{idx}4"
    )
```

## IEC Contact Numbering
Standard IEC 60947 numbering for contacts:
- **NO contacts**: X3-X4 format
  - 13-14 (first NO)
  - 23-24 (second NO)
  - 33-34 (third NO)
  - 43-44 (fourth NO)

- **NC contacts**: X1-X2 format
  - 11-12 (first NC)
  - 21-22 (second NC)
  - 31-32 (third NC)
  - 41-42 (fourth NC)

- **Coil**: A1-A2

## Implementation Steps

1. ✅ Diagnose issue (COMPLETE)
2. Update `component_position_finder.py`:
   - Add `find_contact_positions()` method
   - Search for `.1`, `.2`, `.3` suffixes
3. Update `industrial_component.py`:
   - Add `contact_positions` field
   - Add `add_contact_position()` method
4. Update `auto_loader.py` or `drawer_to_model.py`:
   - Call `find_contact_positions()` for relays/contactors
   - Populate component contact positions
5. Update `pdf_viewer.py`:
   - Add `_draw_contact_instances()` method
   - Add `_get_contact_block_for_suffix()` helper
   - Render contact symbols at `.1`, `.2`, `.3` positions

## Testing Plan

1. Load DRAWER.pdf
2. Navigate to page 9 (page 10 in UI)
3. Verify `-K1` coil appears at (266.3, 433.0)
4. Verify `-K1.1` contact appears at (552.2, 597.0)
5. Verify `-K1.2` contact appears at (688.2, 597.0)
6. Verify `-K1.3` contact appears at (756.2, 597.0)
7. Check contact symbols are different from coil symbol
8. Test on multiple pages (pages 10, 11, etc.)
9. Test toggling relay state affects contact rendering

## Expected Result

After fix:
- Coils render at `-K1` text positions (rectangle with designation)
- Contacts render at `-K1.1`, `-K1.2`, `-K1.3` positions
- Contact symbols show NO/NC configuration
- Contact labels show full designation (e.g., "K1:13-14")
- Contacts align with their actual schematic positions
- Multi-page relays show correct symbols on each page

