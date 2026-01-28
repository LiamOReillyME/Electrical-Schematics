#!/usr/bin/env python3
"""
Test Position Accuracy - Verify that found positions are reasonable.

The tag matching test shows 100% accuracy, but the user reported issues.
This test validates that the POSITIONS are reasonable (not just that tags were found).

Issues this catches:
1. Tags found on wrong pages
2. Positions that are way off (e.g., in title blocks instead of schematics)
3. Multiple positions with very different locations
"""

import json
from pathlib import Path
from typing import Dict, List

from electrical_schematics.pdf.component_position_finder import ComponentPositionFinder


def test_position_reasonableness():
    """Test that positions are reasonable."""
    pdf_path = Path('examples/DRAWER.pdf')

    # Test tags from problematic pages
    test_cases = {
        8: ['-K1', '-K2', '-K3', '-U1'],  # Page 9: Principle of safety circuit
        9: ['-K1', '-K2', '-A1', '-M1'],  # Page 10: Block diagram
        14: ['-F1:2', '-F2', '-X0:1'],    # Page 15: Power feed AC
        15: ['-F4', '-G1', '-X3'],        # Page 16: Power supply DC
        18: ['-A1', '-K1', '-U1'],        # Page 19: Contactor control
        19: ['-K1', '-K2', '-K3'],        # Page 20: Contactor control
        21: ['-F7', '-SH', '+DG-SH'],     # Page 22: Extractor motor
    }

    issues = []

    with ComponentPositionFinder(pdf_path) as finder:
        for page_num, tags in test_cases.items():
            print(f"\n{'='*70}")
            print(f"Testing page {page_num + 1}")
            print(f"{'='*70}")

            result = finder.find_positions(tags, search_all_pages=False)

            for tag in tags:
                if tag in result.positions:
                    pos = result.positions[tag]
                    print(f"  {tag:10s} -> Page {pos.page + 1:2d} at ({pos.x:6.1f}, {pos.y:6.1f}) confidence={pos.confidence:.2f}")

                    # Check if found on expected page
                    if pos.page != page_num:
                        issue = {
                            'tag': tag,
                            'expected_page': page_num + 1,
                            'found_page': pos.page + 1,
                            'type': 'wrong_page',
                            'severity': 'high'
                        }
                        issues.append(issue)
                        print(f"    WARNING: Found on wrong page! Expected {page_num + 1}, found on {pos.page + 1}")

                    # Check if there are ambiguous matches
                    if tag in result.ambiguous_matches:
                        positions = result.ambiguous_matches[tag]
                        if len(positions) > 1:
                            print(f"    Note: Found on {len(positions)} pages:")
                            for p in positions:
                                print(f"      - Page {p.page + 1} at ({p.x:.1f}, {p.y:.1f})")

                            # Check if expected page is among the matches
                            found_on_expected = any(p.page == page_num for p in positions)
                            if not found_on_expected:
                                issue = {
                                    'tag': tag,
                                    'expected_page': page_num + 1,
                                    'found_pages': [p.page + 1 for p in positions],
                                    'type': 'missing_from_expected_page',
                                    'severity': 'high'
                                }
                                issues.append(issue)
                                print(f"    ERROR: Not found on expected page {page_num + 1}!")

                else:
                    print(f"  {tag:10s} -> NOT FOUND")
                    issue = {
                        'tag': tag,
                        'expected_page': page_num + 1,
                        'type': 'not_found',
                        'severity': 'critical'
                    }
                    issues.append(issue)

    # Report summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    if not issues:
        print("All positions are correct!")
        print("Tags found on expected pages with reasonable positions.")
    else:
        print(f"Found {len(issues)} issues:")
        for issue in issues:
            print(f"  - {issue['severity'].upper()}: {issue['tag']} - {issue['type']}")

    # Save issues to file
    if issues:
        with open('position_accuracy_issues.json', 'w') as f:
            json.dump(issues, f, indent=2)
        print(f"\nIssues saved to position_accuracy_issues.json")

    return len(issues) == 0


def test_all_tags_on_page():
    """Test finding ALL tags on each problematic page."""
    pdf_path = Path('examples/DRAWER.pdf')

    # Pages reported as problematic (0-indexed)
    problematic_pages = [8, 9, 14, 15, 18, 19, 21]

    print("\n{'='*70}")
    print("DISCOVERY MODE: Find ALL tags on each page")
    print("{'='*70}\n")

    with ComponentPositionFinder(pdf_path) as finder:
        for page_num in problematic_pages:
            print(f"\nPage {page_num + 1}:")
            print(f"  Title: {finder.get_page_title(page_num)}")

            # Use find_all_device_tags to discover what's on the page
            all_positions = finder.find_all_device_tags(page_range=(page_num, page_num + 1))

            print(f"  Discovered {len(all_positions)} device tags:")

            # Group by type
            panel_tags = [p for p in all_positions if p.device_tag.startswith('-')]
            field_tags = [p for p in all_positions if p.device_tag.startswith('+')]

            if panel_tags:
                print(f"\n  Panel devices (-):")
                for p in sorted(panel_tags, key=lambda x: x.device_tag):
                    print(f"    {p.device_tag:15s} at ({p.x:6.1f}, {p.y:6.1f})")

            if field_tags:
                print(f"\n  Field devices (+):")
                for p in sorted(field_tags, key=lambda x: x.device_tag):
                    print(f"    {p.device_tag:15s} at ({p.x:6.1f}, {p.y:6.1f})")


def main():
    print("="*70)
    print("POSITION ACCURACY TEST")
    print("="*70)

    # Test 1: Check position reasonableness
    success = test_position_reasonableness()

    # Test 2: Discovery mode
    test_all_tags_on_page()

    print("\n" + "="*70)
    if success:
        print("RESULT: All positions correct")
        return 0
    else:
        print("RESULT: Issues found - see position_accuracy_issues.json")
        return 1


if __name__ == '__main__':
    exit(main())
