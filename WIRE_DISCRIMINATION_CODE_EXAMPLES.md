# Wire Discrimination - Code Examples

## Quick Start

### Basic Wire Detection (Filtered)

```python
import fitz
from electrical_schematics.pdf.visual_wire_detector import VisualWireDetector

# Open PDF
doc = fitz.open("wiring_diagram.pdf")

# Create detector with classification enabled
detector = VisualWireDetector(doc, enable_classification=True)

# Get only actual wires (borders/grids filtered out)
wires = detector.detect_wires_only(page_num=0)

print(f"Found {len(wires)} wires on page 0")
for wire in wires:
    print(f"  Color: {wire.color.value:10s}, "
          f"Length: {wire.length:6.1f}pt, "
          f"Voltage: {wire.voltage_type}")
```

### Get Classification Breakdown

```python
from electrical_schematics.pdf.visual_wire_detector import LineType

# Get all lines classified by type
classified = detector.classify_all_lines(page_num=0)

print("Classification breakdown:")
for line_type, lines in classified.items():
    print(f"  {line_type.value:20s}: {len(lines):4d} lines")

# Access specific types
wires = classified.get(LineType.WIRE, [])
borders = classified.get(LineType.BORDER, [])
grids = classified.get(LineType.TABLE_GRID, [])
```

### Compare All Lines vs Wires Only

```python
# Get all detected line segments
all_lines = detector.detect_wires(page_num=0)

# Get filtered wires only
wires_only = detector.detect_wires_only(page_num=0)

reduction = len(all_lines) - len(wires_only)
print(f"All segments: {len(all_lines)}")
print(f"Wires only:   {len(wires_only)}")
print(f"Filtered out: {reduction} ({reduction/len(all_lines)*100:.1f}%)")
```

## Analysis Examples

### Find High-Density Schematic Pages

```python
# Analyze all pages to find schematics
schematic_pages = []

for page_num in range(len(doc)):
    wires = detector.detect_wires_only(page_num)
    all_lines = detector.detect_wires(page_num)

    # Pages with >30% wires are likely schematics
    if len(all_lines) > 0:
        wire_ratio = len(wires) / len(all_lines)
        if wire_ratio > 0.30:
            schematic_pages.append((page_num, len(wires)))

print("Schematic pages found:")
for page_num, wire_count in sorted(schematic_pages, key=lambda x: -x[1]):
    print(f"  Page {page_num}: {wire_count} wires")
```

### Analyze Wire Color Distribution

```python
from collections import defaultdict

# Count wires by color across all pages
color_counts = defaultdict(int)
voltage_counts = defaultdict(int)

for page_num in range(len(doc)):
    wires = detector.detect_wires_only(page_num)
    for wire in wires:
        color_counts[wire.color.value] += 1
        voltage_counts[wire.voltage_type] += 1

print("Wire colors:")
for color, count in sorted(color_counts.items(), key=lambda x: -x[1]):
    print(f"  {color:15s}: {count:4d}")

print("\nVoltage types:")
for voltage, count in sorted(voltage_counts.items(), key=lambda x: -x[1]):
    print(f"  {voltage:10s}: {count:4d}")
```

### Find Longest Wires

```python
# Find longest wires on each page
for page_num in range(len(doc)):
    wires = detector.detect_wires_only(page_num)
    if not wires:
        continue

    longest = max(wires, key=lambda w: w.length)
    print(f"Page {page_num}: Longest wire = {longest.length:.1f}pt "
          f"({longest.color.value}, {longest.voltage_type})")
```

## Configuration Examples

### Adjust Classification Thresholds

```python
from electrical_schematics.pdf.visual_wire_detector import (
    VisualWireDetector,
    LineClassifier
)

# Create detector with custom parameters
detector = VisualWireDetector(
    doc,
    min_wire_length=10.0,        # Minimum wire length (default: 8.0)
    max_wire_thickness=5.0,       # Maximum wire thickness (default: 5.0)
    enable_classification=True
)

# Get page dimensions
page = doc[0]
page_rect = page.rect

# Create classifier with custom thresholds
classifier = LineClassifier(
    page_width=page_rect.width,
    page_height=page_rect.height,
    border_margin=25.0,           # Border margin (default: 20.0)
    title_block_ratio=0.80,       # Title block Y ratio (default: 0.85)
    grid_tolerance=4.0,           # Grid alignment tolerance (default: 3.0)
    shape_tolerance=10.0          # Shape proximity tolerance (default: 8.0)
)
```

### Disable Classification (Get All Lines)

```python
# Create detector without classification
detector = VisualWireDetector(doc, enable_classification=False)

# This returns all detected line segments (no filtering)
all_lines = detector.detect_wires(page_num=0)
```

## Advanced Usage

### Manual Classification

```python
from electrical_schematics.pdf.visual_wire_detector import LineClassifier

# Get all lines
all_lines = detector.detect_wires(page_num=0)

# Create classifier
page = doc[0]
page_rect = page.rect
classifier = LineClassifier(page_rect.width, page_rect.height)

# Classify each line manually
for line in all_lines:
    line_type = classifier.classify_line(line, all_lines)
    print(f"Line at ({line.start_x:.1f}, {line.start_y:.1f}): {line_type.value}")
```

### Filter Specific Line Types

```python
# Get classification
classified = detector.classify_all_lines(page_num=0)

# Get only wires and component outlines
wires = classified.get(LineType.WIRE, [])
outlines = classified.get(LineType.COMPONENT_OUTLINE, [])

print(f"Wires: {len(wires)}")
print(f"Component outlines: {len(outlines)}")

# Combine them
wire_and_outlines = wires + outlines
```

### Export Wire Data

```python
import json

# Export wire data to JSON
def export_wires(detector, page_num, output_file):
    wires = detector.detect_wires_only(page_num)

    wire_data = []
    for wire in wires:
        wire_data.append({
            'start_x': wire.start_x,
            'start_y': wire.start_y,
            'end_x': wire.end_x,
            'end_y': wire.end_y,
            'color': wire.color.value,
            'voltage_type': wire.voltage_type,
            'length': wire.length,
            'is_horizontal': wire.is_horizontal,
            'is_vertical': wire.is_vertical
        })

    with open(output_file, 'w') as f:
        json.dump(wire_data, f, indent=2)

# Export wires from page 0
export_wires(detector, 0, 'wires_page_0.json')
```

## Testing Examples

### Test Border Detection

```python
from electrical_schematics.pdf.visual_wire_detector import (
    LineClassifier,
    VisualWire,
    WireColor
)

# Create classifier
classifier = LineClassifier(page_width=600, page_height=800)

# Test top border
top_border = VisualWire(
    page_number=0,
    start_x=0, start_y=5,
    end_x=500, end_y=5,
    color=WireColor.BLACK,
    rgb=(0.0, 0.0, 0.0),
    thickness=1.0
)

assert classifier._is_border(top_border), "Should detect top border"
```

### Test Wire Characteristics

```python
# Test colored wire detection
red_wire = VisualWire(
    page_number=0,
    start_x=100, start_y=200,
    end_x=400, end_y=200,
    color=WireColor.RED,
    rgb=(1.0, 0.0, 0.0),
    thickness=1.5
)

assert classifier._has_wire_characteristics(red_wire), "Should detect red wire"
```

## Integration Examples

### Use in GUI Application

```python
class PDFViewer:
    def __init__(self, pdf_path):
        self.doc = fitz.open(pdf_path)
        self.detector = VisualWireDetector(self.doc, enable_classification=True)

    def render_page_with_wires(self, page_num):
        # Get only actual wires
        wires = self.detector.detect_wires_only(page_num)

        # Render page
        page = self.doc[page_num]
        pix = page.get_pixmap()

        # Overlay wires (simplified)
        for wire in wires:
            # Draw wire overlay based on color
            color = self._get_overlay_color(wire.color)
            # ... draw line on pixmap ...

        return pix

    def _get_overlay_color(self, wire_color):
        # Map wire color to overlay color
        color_map = {
            WireColor.RED: (255, 0, 0),
            WireColor.BLUE: (0, 0, 255),
            WireColor.GREEN: (0, 255, 0)
        }
        return color_map.get(wire_color, (128, 128, 128))
```

### Statistics Widget

```python
def get_page_statistics(detector, page_num):
    """Get detailed statistics for a page."""
    classified = detector.classify_all_lines(page_num)

    stats = {
        'total_lines': sum(len(lines) for lines in classified.values()),
        'wire_count': len(classified.get(LineType.WIRE, [])),
        'border_count': len(classified.get(LineType.BORDER, [])),
        'grid_count': len(classified.get(LineType.TABLE_GRID, [])),
        'outline_count': len(classified.get(LineType.COMPONENT_OUTLINE, [])),
        'unknown_count': len(classified.get(LineType.UNKNOWN, []))
    }

    # Wire color breakdown
    wires = classified.get(LineType.WIRE, [])
    stats['wire_colors'] = {}
    for wire in wires:
        color = wire.color.value
        stats['wire_colors'][color] = stats['wire_colors'].get(color, 0) + 1

    return stats
```

## Performance Examples

### Batch Processing

```python
import time

def analyze_all_pages(pdf_path):
    """Analyze all pages and show performance."""
    doc = fitz.open(pdf_path)
    detector = VisualWireDetector(doc, enable_classification=True)

    start_time = time.time()
    total_lines = 0
    total_wires = 0

    for page_num in range(len(doc)):
        all_lines = detector.detect_wires(page_num)
        wires = detector.detect_wires_only(page_num)

        total_lines += len(all_lines)
        total_wires += len(wires)

    elapsed = time.time() - start_time

    print(f"Processed {len(doc)} pages in {elapsed:.2f}s")
    print(f"Total lines: {total_lines}")
    print(f"Total wires: {total_wires}")
    print(f"Reduction: {total_lines - total_wires} ({(total_lines - total_wires)/total_lines*100:.1f}%)")
    print(f"Speed: {len(doc)/elapsed:.1f} pages/second")
```

### Parallel Processing (Optional)

```python
from concurrent.futures import ThreadPoolExecutor

def process_page(detector, page_num):
    """Process a single page."""
    wires = detector.detect_wires_only(page_num)
    return page_num, len(wires)

def parallel_analysis(pdf_path, max_workers=4):
    """Analyze pages in parallel."""
    doc = fitz.open(pdf_path)
    detector = VisualWireDetector(doc, enable_classification=True)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_page, detector, page_num)
            for page_num in range(len(doc))
        ]

        results = [f.result() for f in futures]

    return sorted(results, key=lambda x: -x[1])  # Sort by wire count
```

## Debugging Examples

### Visualize Classification

```python
def print_classification_details(detector, page_num):
    """Print detailed classification information."""
    classified = detector.classify_all_lines(page_num)

    print(f"\nPage {page_num} - Classification Details")
    print("=" * 60)

    for line_type in LineType:
        lines = classified.get(line_type, [])
        if not lines:
            continue

        print(f"\n{line_type.value.upper()} ({len(lines)} lines):")

        # Show first 3 examples
        for i, line in enumerate(lines[:3]):
            print(f"  {i+1}. Length={line.length:6.1f}pt, "
                  f"Color={line.color.value:10s}, "
                  f"Start=({line.start_x:6.1f}, {line.start_y:6.1f}), "
                  f"End=({line.end_x:6.1f}, {line.end_y:6.1f})")
```

### Compare Detection Methods

```python
def compare_detection_methods(pdf_path, page_num):
    """Compare detection with and without classification."""
    doc = fitz.open(pdf_path)

    # Without classification
    detector_no_class = VisualWireDetector(doc, enable_classification=False)
    all_lines = detector_no_class.detect_wires(page_num)

    # With classification
    detector_with_class = VisualWireDetector(doc, enable_classification=True)
    wires_only = detector_with_class.detect_wires_only(page_num)

    print(f"Without classification: {len(all_lines)} line segments")
    print(f"With classification:    {len(wires_only)} wires")
    print(f"Reduction:             {len(all_lines) - len(wires_only)} lines ({(len(all_lines) - len(wires_only))/len(all_lines)*100:.1f}%)")
```

---

**File**: `/home/liam-oreilly/claude.projects/electricalSchematics/WIRE_DISCRIMINATION_CODE_EXAMPLES.md`
**Created**: 2026-01-28
**Project**: Industrial Wiring Diagram Analyzer
