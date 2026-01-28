# Device Tag Counting & Validation Tools

This directory contains tools for establishing ground truth device tag counts and validating auto-placement results for DRAWER.pdf electrical schematics.

## Overview

Three scripts work together to count, validate, and verify device tag placements:

1. **count_device_tags.py** - Establishes ground truth by counting all device tags
2. **validate_auto_placement.py** - Validates auto-placement results against ground truth
3. Visual verification images in `tag_debug/` directory

## Ground Truth Report

### Files Generated

- **TAG_COUNT_REPORT.json** - Complete analysis data (1208 lines)
  - Parts list (24 devices)
  - Tag counts by page
  - Position coordinates for all 154 occurrences
  - Multi-page tag mapping

- **TAG_COUNT_SUMMARY.md** - Human-readable summary
  - Statistics and metrics
  - Tag distribution
  - Multi-page components
  - Implementation notes

- **tag_debug/*.png** - Visual verification images
  - First 3 schematic pages with highlighted tags
  - Green bounding boxes around detected text
  - Red labels showing device tags

## Key Findings

```
Parts List:              24 devices
Schematic Pages:         16 pages (out of 40 total)
Total Tag Occurrences:   154 instances
Discovery Rate:          100% (all tags found)
Multi-Page Tags:         13 components (appear on 2+ pages)
```

### Top Multi-Page Components

| Tag | Pages | Count | Type |
|-----|-------|-------|------|
| -K1 | 10 | 70 | Main contactor |
| -A1 | 6 | 26 | PLC |
| -K2 | 5 | 10 | Contactor |
| -KR1 | 3 | 9 | Safety relay |

## Usage

### 1. Generate Ground Truth

Run the counting script to analyze DRAWER.pdf:

```bash
python count_device_tags.py
```

**Output:**
- TAG_COUNT_REPORT.json
- TAG_COUNT_SUMMARY.md
- tag_debug/tag_count_page_*.png

**What it does:**
1. Parses device tags from parts list (pages 26-27)
2. Classifies pages (skips cover, TOC, cable diagrams)
3. Counts all tag occurrences on schematic pages
4. Records precise bounding box coordinates
5. Generates visual verification images

### 2. Validate Auto-Placement

Compare auto-placement results against ground truth:

```bash
python validate_auto_placement.py <placement_results.json>
```

**Input format** (placement_results.json):
```json
{
  "-K1": {"page": 7, "x": 215.3, "y": 603.0, "confidence": 1.0},
  "-A1": {"page": 7, "x": 39.3, "y": 55.1, "confidence": 1.0},
  ...
}
```

**Output:**
- Console report with validation metrics
- JSON validation report saved to disk

**What it validates:**
- All 24 tags from parts list are placed
- No extra/unknown tags
- Position accuracy (distance from ground truth)
- Multi-page components appear on correct pages

### 3. Example Validation

Test the validation script:

```bash
python validate_auto_placement.py test_placement_results.json
```

Sample output:
```
SUMMARY
----------------------------------------------------------------------
Ground Truth Tags:        24
Placed Tags:              24
Match Percentage:         100.0%

POSITION ACCURACY
----------------------------------------------------------------------
Tags Validated:           24
Average Distance:         0.0 pt
Within 50pt:              24 (100.0%)
Within 100pt:             24 (100.0%)

RESULT: PASS - All tags correctly placed
```

## Ground Truth Data Structure

### TAG_COUNT_REPORT.json Format

```json
{
  "parts_list_count": 24,
  "parts_list": ["+DG-B1", "+DG-M1", "-A1", ...],
  "schematic_pages": [7, 8, 9, 10, ...],
  "total_tag_occurrences": 154,
  "tags_by_page": {
    "7": ["-A1", "-F4", "-G1", "-K1"],
    "8": ["-K1", "-K2", "-K3", "-KR1", "-U1"],
    ...
  },
  "tags_with_counts": {
    "-K1": {
      "count": 70,
      "pages": [7, 8, 9, 10, 13, 15, 18, 19, 20, 21],
      "page_count": 10,
      "positions": [
        {
          "page": 7,
          "x0": 209.5, "y0": 598.7,
          "x1": 221.1, "y1": 607.4,
          "center_x": 215.3, "center_y": 603.0
        },
        ...
      ]
    },
    ...
  },
  "multi_page_tags": {
    "-K1": {
      "pages": [7, 8, 9, 10, 13, 15, 18, 19, 20, 21],
      "total_count": 70
    },
    ...
  }
}
```

### Position Coordinate Format

All positions are in PDF points (1/72 inch):
- `x0, y0` - Bottom-left corner of bounding box
- `x1, y1` - Top-right corner of bounding box
- `center_x, center_y` - Center point (for overlay placement)
- `page` - Page number (0-indexed)

## Validation Metrics

### Match Percentage
- **100%** = All tags from parts list are placed
- **90-99%** = Most tags placed with minor gaps
- **<90%** = Significant placement issues

### Position Accuracy
- **Within 50pt** = Excellent accuracy (±0.7 inches)
- **Within 100pt** = Good accuracy (±1.4 inches)
- **>100pt** = Potential placement error

### Multi-Page Validation
- Checks each multi-page component appears on all expected pages
- Reports missing pages for incomplete placements
- Essential for components like -K1 (10 pages) and -A1 (6 pages)

## Expected Auto-Placement Results

Based on ground truth analysis, auto-placement should achieve:

### Target Metrics
- **Total placements:** 154 component overlays
- **Unique components:** 24 devices
- **Page coverage:** 12 of 16 schematic pages
- **Multi-page support:** 13 components on multiple pages

### Success Criteria
1. ✓ All 24 devices from parts list placed
2. ✓ All 154 occurrences have overlay positions
3. ✓ Multi-page components on correct pages
4. ✓ Position accuracy within 50pt of ground truth
5. ✓ No overlays on non-schematic pages

## Implementation Notes

### Page Classification

Pages are classified by reading the title block at the bottom center:

**Schematic Pages** (included):
- "Electrical schematic" or unnamed pages
- Block diagrams
- Pages 7-24 in DRAWER.pdf

**Non-Schematic Pages** (skipped):
- Cover sheet (page 0)
- Table of contents (pages 1-2)
- Global information (page 3)
- Device allocation (page 4)
- Cable diagrams (pages 25-39)
- Parts lists (pages 26-27)

### Tag Detection Pattern

Regex: `[+-][A-Z0-9]+(?:-[A-Z0-9]+)?`

**Matches:**
- `-A1`, `-K1`, `-F2` (control panel devices)
- `+DG-M1`, `+DG-B1` (field devices)
- `-A1-X5:3` (with terminal references)

**Does not match:**
- Partial tags without prefix
- Wire numbers (W1, W2)
- Page numbers

### Coordinate System

PyMuPDF uses bottom-left origin:
- Origin (0, 0) at bottom-left of page
- X increases right
- Y increases up
- Units in points (1pt = 1/72 inch)

For Qt/GUI display, may need to flip Y axis:
```python
screen_y = page_height - pdf_y
```

## Troubleshooting

### Missing Tags

If validation shows missing tags:
1. Check page classification (might be skipping schematic pages)
2. Verify tag format matches regex pattern
3. Check for OCR issues in PDF text extraction
4. Review visual debug images to confirm tag visibility

### Position Errors

If positions are off by >50pt:
1. Verify coordinate system matches PDF coordinates
2. Check for zoom/scale factors in rendering
3. Ensure using center coordinates (not corner)
4. Compare against visual debug images

### Multi-Page Issues

If multi-page validation fails:
1. Confirm tag appears on all ground truth pages
2. Check if secondary positions are being placed
3. Verify page filtering isn't skipping valid pages
4. Review ambiguous_matches in ground truth data

## Files Reference

### Generated by count_device_tags.py
- `/TAG_COUNT_REPORT.json` - Full ground truth data
- `/TAG_COUNT_SUMMARY.md` - Human-readable summary
- `/tag_debug/tag_count_page_*.png` - Visual verification (3 pages)

### Tool Scripts
- `/count_device_tags.py` - Ground truth generator
- `/validate_auto_placement.py` - Validation tool
- `/test_placement_results.json` - Sample placement data

### Documentation
- `/TAG_COUNTING_README.md` - This file
- `/CLAUDE.md` - Project overview
- `/electrical_schematics/pdf/README_DRAWER.md` - DRAWER format spec

## Integration with Auto-Placement

The ground truth data can be integrated into your auto-placement feature:

```python
from pathlib import Path
import json

# Load ground truth
with open("TAG_COUNT_REPORT.json") as f:
    ground_truth = json.load(f)

# Get expected tags
expected_tags = ground_truth["parts_list"]

# Get expected positions for a tag
tag_positions = ground_truth["tags_with_counts"]["-K1"]["positions"]

# Check if tag should appear on multiple pages
multi_page = "-K1" in ground_truth["multi_page_tags"]
if multi_page:
    pages = ground_truth["multi_page_tags"]["-K1"]["pages"]
    print(f"-K1 should appear on pages: {pages}")
```

## Testing Strategy

1. **Unit Tests**: Test tag detection pattern, page classification
2. **Integration Tests**: Test full counting pipeline on DRAWER.pdf
3. **Validation Tests**: Run validate_auto_placement.py in CI/CD
4. **Visual Tests**: Review debug images for accuracy
5. **Regression Tests**: Compare against TAG_COUNT_REPORT.json baseline

## Performance

Counting DRAWER.pdf (40 pages):
- **Parts list extraction:** <1 second
- **Page classification:** ~2 seconds
- **Tag counting:** ~3 seconds
- **Visual generation:** ~2 seconds
- **Total runtime:** ~8 seconds

## License

Part of the Industrial Wiring Diagram Analyzer project.

## Contact

For questions or issues with the tag counting tools, see the main project README.

---

**Last Updated:** 2026-01-28
**Ground Truth Version:** 1.0
**DRAWER.pdf Version:** Original provided PDF
