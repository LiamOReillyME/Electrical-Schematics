#!/usr/bin/env python3
"""Test script for wire discrimination algorithm.

Analyzes DRAWER.pdf and shows:
- Total line segments detected
- Classification breakdown (wires, borders, grids, etc.)
- Per-page statistics
- Accuracy metrics
"""

import fitz
from pathlib import Path
from collections import defaultdict
from electrical_schematics.pdf.visual_wire_detector import (
    VisualWireDetector,
    LineType,
    WireColor
)


def analyze_page(detector: VisualWireDetector, page_num: int) -> dict:
    """Analyze a single page and return statistics."""
    # Get all lines
    all_lines = detector.detect_wires(page_num)

    # Classify lines
    classified = detector.classify_all_lines(page_num)

    # Count by type
    type_counts = {line_type: len(lines) for line_type, lines in classified.items()}

    # Count wires by color
    wires = classified.get(LineType.WIRE, [])
    wire_colors = defaultdict(int)
    for wire in wires:
        wire_colors[wire.color.value] += 1

    return {
        'total_lines': len(all_lines),
        'type_counts': type_counts,
        'wire_count': len(wires),
        'wire_colors': dict(wire_colors),
        'classified': classified
    }


def print_page_summary(page_num: int, stats: dict):
    """Print summary for a single page."""
    print(f"\n{'='*60}")
    print(f"Page {page_num}")
    print(f"{'='*60}")
    print(f"Total line segments: {stats['total_lines']}")
    print(f"\nClassification breakdown:")

    type_counts = stats['type_counts']
    for line_type in LineType:
        count = type_counts.get(line_type, 0)
        if count > 0:
            percentage = (count / stats['total_lines']) * 100
            print(f"  {line_type.value:20s}: {count:4d} ({percentage:5.1f}%)")

    # Wire color breakdown
    if stats['wire_count'] > 0:
        print(f"\nWire colors:")
        for color, count in sorted(stats['wire_colors'].items(), key=lambda x: -x[1]):
            print(f"  {color:15s}: {count:4d}")


def main():
    """Run wire discrimination analysis."""
    pdf_path = Path('/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf')

    print("="*60)
    print("WIRE DISCRIMINATION ANALYSIS")
    print("="*60)
    print(f"PDF: {pdf_path}")

    # Open document
    doc = fitz.open(pdf_path)
    detector = VisualWireDetector(doc, enable_classification=True)

    print(f"Total pages: {len(doc)}")

    # Analyze all pages
    all_stats = []
    total_lines = 0
    total_wires = 0
    overall_type_counts = defaultdict(int)
    overall_wire_colors = defaultdict(int)

    for page_num in range(len(doc)):
        stats = analyze_page(detector, page_num)
        all_stats.append(stats)

        total_lines += stats['total_lines']
        total_wires += stats['wire_count']

        # Aggregate counts
        for line_type, count in stats['type_counts'].items():
            overall_type_counts[line_type] += count

        for color, count in stats['wire_colors'].items():
            overall_wire_colors[color] += count

    # Print overall summary
    print("\n" + "="*60)
    print("OVERALL SUMMARY")
    print("="*60)
    print(f"Total line segments detected: {total_lines:,}")
    print(f"Total wires (after filtering): {total_wires:,}")
    print(f"Reduction: {total_lines - total_wires:,} lines filtered out ({((total_lines - total_wires) / total_lines * 100):.1f}%)")

    print(f"\nOverall classification breakdown:")
    for line_type in LineType:
        count = overall_type_counts.get(line_type, 0)
        if count > 0:
            percentage = (count / total_lines) * 100
            print(f"  {line_type.value:20s}: {count:5d} ({percentage:5.1f}%)")

    print(f"\nOverall wire color distribution:")
    for color, count in sorted(overall_wire_colors.items(), key=lambda x: -x[1]):
        print(f"  {color:15s}: {count:4d}")

    # Show pages with most wires
    print(f"\nPages with most wires (top 10):")
    sorted_pages = sorted(enumerate(all_stats), key=lambda x: -x[1]['wire_count'])
    for i, (page_num, stats) in enumerate(sorted_pages[:10]):
        print(f"  Page {page_num:2d}: {stats['wire_count']:4d} wires")

    # Show pages with most non-wire lines
    print(f"\nPages with most non-wire lines (top 10):")
    sorted_pages = sorted(
        enumerate(all_stats),
        key=lambda x: -(x[1]['total_lines'] - x[1]['wire_count'])
    )
    for i, (page_num, stats) in enumerate(sorted_pages[:10]):
        non_wires = stats['total_lines'] - stats['wire_count']
        print(f"  Page {page_num:2d}: {non_wires:4d} non-wire lines")

    # Detailed analysis for selected pages
    print("\n" + "="*60)
    print("DETAILED ANALYSIS - SELECTED PAGES")
    print("="*60)

    # Analyze pages with lots of lines (likely schematic pages)
    high_line_pages = [5, 27, 32, 33]  # From earlier output
    for page_num in high_line_pages:
        if page_num < len(all_stats):
            print_page_summary(page_num, all_stats[page_num])

    print("\n" + "="*60)
    print("Analysis complete!")
    print("="*60)


if __name__ == '__main__':
    main()
