#!/usr/bin/env python3
"""Analyze unknown lines to improve classification."""

import fitz
from pathlib import Path
from electrical_schematics.pdf.visual_wire_detector import (
    VisualWireDetector,
    LineType,
    WireColor
)


def main():
    pdf_path = Path('/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf')
    doc = fitz.open(pdf_path)
    detector = VisualWireDetector(doc, enable_classification=True)

    # Analyze unknown lines on a few pages
    test_pages = [5, 10, 20, 27]

    for page_num in test_pages:
        print(f"\n{'='*60}")
        print(f"Page {page_num} - Unknown Lines Analysis")
        print(f"{'='*60}")

        classified = detector.classify_all_lines(page_num)
        unknown_lines = classified.get(LineType.UNKNOWN, [])

        if not unknown_lines:
            print("No unknown lines on this page")
            continue

        print(f"Total unknown lines: {len(unknown_lines)}")

        # Analyze characteristics
        print("\nLength distribution:")
        short = sum(1 for l in unknown_lines if l.length < 15)
        medium = sum(1 for l in unknown_lines if 15 <= l.length < 30)
        long = sum(1 for l in unknown_lines if l.length >= 30)
        print(f"  Short (< 15 pts): {short}")
        print(f"  Medium (15-30 pts): {medium}")
        print(f"  Long (>= 30 pts): {long}")

        print("\nOrientation:")
        horizontal = sum(1 for l in unknown_lines if l.is_horizontal)
        vertical = sum(1 for l in unknown_lines if l.is_vertical)
        diagonal = len(unknown_lines) - horizontal - vertical
        print(f"  Horizontal: {horizontal}")
        print(f"  Vertical: {vertical}")
        print(f"  Diagonal: {diagonal}")

        print("\nColor distribution:")
        from collections import defaultdict
        colors = defaultdict(int)
        for line in unknown_lines:
            colors[line.color.value] += 1
        for color, count in sorted(colors.items(), key=lambda x: -x[1]):
            print(f"  {color:15s}: {count}")

        # Sample a few unknown lines
        print("\nSample unknown lines (first 5):")
        for i, line in enumerate(unknown_lines[:5]):
            print(f"  {i+1}. Length={line.length:.1f}, Color={line.color.value}, "
                  f"H={line.is_horizontal}, V={line.is_vertical}, "
                  f"Start=({line.start_x:.1f}, {line.start_y:.1f}), "
                  f"End=({line.end_x:.1f}, {line.end_y:.1f})")


if __name__ == '__main__':
    main()
