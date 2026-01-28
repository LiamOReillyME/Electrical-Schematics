#!/usr/bin/env python3
"""Test auto-placement on actual schematic pages with real device tags."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from electrical_schematics.pdf.drawer_parser import DrawerParser
from electrical_schematics.pdf.component_position_finder import ComponentPositionFinder


def main():
    pdf_path = Path("/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf")

    # Parse to get expected devices
    parser = DrawerParser(pdf_path)
    diagram = parser.parse()

    # Group by page
    from collections import defaultdict
    by_page = defaultdict(list)
    for tag, dev in diagram.devices.items():
        # page_ref format is like "15 2" or "21 6"
        # Extract the page number (first part)
        page_str = dev.page_ref.split()[0]
        page_num = int(page_str) - 1  # Convert to 0-indexed
        by_page[page_num].append(tag)

    print("="*80)
    print("TESTING AUTO-PLACEMENT ON ACTUAL SCHEMATIC PAGES")
    print("="*80)
    print()

    # Test each page that has devices
    total_expected = 0
    total_found = 0
    total_missing = 0

    with ComponentPositionFinder(pdf_path) as finder:
        for page_num in sorted(by_page.keys()):
            expected_tags = sorted(by_page[page_num])
            total_expected += len(expected_tags)

            print(f"\nPage {page_num + 1} (0-indexed: {page_num})")
            print(f"Expected tags: {expected_tags}")

            # Find positions
            result = finder.find_positions(expected_tags, search_all_pages=False)

            found = len(result.positions)
            missing = len(result.unmatched_tags)

            total_found += found
            total_missing += missing

            print(f"Found: {found}/{len(expected_tags)}")

            if result.unmatched_tags:
                print(f"MISSING: {sorted(result.unmatched_tags)}")

            # Show what was found
            for tag in expected_tags:
                if tag in result.positions:
                    pos = result.positions[tag]
                    print(f"  ✓ {tag:20s} @ page {pos.page + 1:2d}, ({pos.x:6.1f}, {pos.y:6.1f}) "
                          f"[{pos.match_type}, conf={pos.confidence:.2f}]")
                else:
                    print(f"  ✗ {tag:20s} NOT FOUND")

            print()

    print("="*80)
    print(f"OVERALL RESULTS")
    print("="*80)
    print(f"Total expected: {total_expected}")
    print(f"Total found: {total_found}")
    print(f"Total missing: {total_missing}")
    print(f"Accuracy: {total_found / total_expected * 100:.1f}%")


if __name__ == "__main__":
    main()
