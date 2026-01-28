#!/usr/bin/env python3
"""Compare before/after wire discrimination on selected pages."""

import fitz
from pathlib import Path
from electrical_schematics.pdf.visual_wire_detector import (
    VisualWireDetector,
    LineType
)


def compare_page(detector: VisualWireDetector, page_num: int):
    """Compare before/after discrimination for a single page."""
    all_lines = detector.detect_wires(page_num)
    wires_only = detector.detect_wires_only(page_num)
    classified = detector.classify_all_lines(page_num)

    print(f"\n{'='*70}")
    print(f"PAGE {page_num} - Before/After Comparison")
    print(f"{'='*70}")

    print(f"\nBEFORE DISCRIMINATION:")
    print(f"  Total line segments: {len(all_lines)}")

    print(f"\nAFTER DISCRIMINATION:")
    print(f"  Wires only: {len(wires_only)}")
    print(f"  Reduction: {len(all_lines) - len(wires_only)} lines filtered ({((len(all_lines) - len(wires_only)) / len(all_lines) * 100):.1f}%)")

    print(f"\nCLASSIFICATION BREAKDOWN:")
    for line_type in LineType:
        count = len(classified.get(line_type, []))
        if count > 0:
            percentage = (count / len(all_lines)) * 100
            print(f"  {line_type.value:20s}: {count:5d} ({percentage:5.1f}%)")

    # Show wire color breakdown
    from collections import defaultdict
    wire_colors = defaultdict(int)
    for wire in wires_only:
        wire_colors[wire.color.value] += 1

    print(f"\nWIRE COLORS:")
    for color, count in sorted(wire_colors.items(), key=lambda x: -x[1]):
        print(f"  {color:15s}: {count:4d}")

    # Show examples of each type
    print(f"\nSAMPLE LINES BY TYPE:")
    for line_type in [LineType.WIRE, LineType.BORDER, LineType.TABLE_GRID, LineType.COMPONENT_OUTLINE]:
        lines = classified.get(line_type, [])
        if lines:
            sample = lines[0]
            print(f"  {line_type.value:20s}: Length={sample.length:6.1f}pt, "
                  f"Color={sample.color.value:10s}, "
                  f"H={sample.is_horizontal}, V={sample.is_vertical}")


def main():
    """Run comparison on selected pages."""
    pdf_path = Path('/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf')

    print("="*70)
    print("WIRE DISCRIMINATION - BEFORE/AFTER COMPARISON")
    print("="*70)
    print(f"PDF: {pdf_path.name}")

    doc = fitz.open(pdf_path)
    detector = VisualWireDetector(doc, enable_classification=True)

    # Compare a diverse set of pages
    pages_to_analyze = [
        (5, "High grid density page"),
        (7, "High wire density schematic"),
        (20, "Complex schematic"),
        (27, "Device tag list page"),
        (32, "Cable routing table")
    ]

    for page_num, description in pages_to_analyze:
        print(f"\n{'='*70}")
        print(f"Page {page_num}: {description}")
        compare_page(detector, page_num)

    print(f"\n{'='*70}")
    print("Comparison complete!")
    print("="*70)


if __name__ == '__main__':
    main()
