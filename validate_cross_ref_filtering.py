#!/usr/bin/env python3
"""Validate that cross-reference filtering is working correctly.

This script demonstrates the cross-reference filtering enhancement
by showing that cross-references are correctly identified and filtered out.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from electrical_schematics.pdf.component_position_finder import (
    ComponentPositionFinder,
    is_cross_reference,
)


def test_cross_ref_pattern():
    """Test cross-reference pattern matching."""
    print("=" * 80)
    print("CROSS-REFERENCE PATTERN TESTING")
    print("=" * 80)
    print()

    test_cases = [
        # (text, expected, description)
        ("K2:61/19.9", True, "Standard cross-reference"),
        ("-K3:20/15.3", True, "Cross-reference with - prefix"),
        ("+V1:12/45.6", True, "Cross-reference with + prefix"),
        ("U2:30/100.5", True, "Cross-reference without prefix"),

        ("-K1", False, "Device tag (should NOT be filtered)"),
        ("-K1:13", False, "Terminal reference (colon but no slash)"),
        ("+DG-M1", False, "Field device tag"),
        ("-A1-X5:3", False, "Terminal block reference"),
        ("F2", False, "Simple device tag"),
        ("0V", False, "Voltage rail"),
    ]

    passed = 0
    failed = 0

    for text, expected, description in test_cases:
        result = is_cross_reference(text)
        status = "✓" if result == expected else "✗"

        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"{status} {text:20s} -> {result:5} (expected {expected:5}) - {description}")

    print()
    print(f"Results: {passed} passed, {failed} failed")
    print()

    return failed == 0


def test_real_pdf():
    """Test cross-reference filtering on real PDF."""
    print("=" * 80)
    print("REAL PDF TESTING")
    print("=" * 80)
    print()

    pdf_path = Path("/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf")

    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return False

    # Get all discovered device tags
    with ComponentPositionFinder(pdf_path) as finder:
        all_positions = finder.find_all_device_tags(page_range=(0, 30))

        # Filter to likely cross-references (tags with colon and slash)
        cross_refs = [pos for pos in all_positions if ":" in pos.device_tag and "/" in pos.device_tag]
        device_tags = [pos for pos in all_positions if ":" not in pos.device_tag or "/" not in pos.device_tag]

        print(f"Total text blocks matching device tag pattern: {len(all_positions)}")
        print(f"Cross-references (filtered out): {len(cross_refs)}")
        print(f"Actual device tags: {len(device_tags)}")
        print()

        if cross_refs:
            print("Sample cross-references (should be 0 if filtering works):")
            for pos in cross_refs[:10]:
                print(f"  {pos.device_tag} on page {pos.page + 1}")
            print()

        if device_tags:
            print("Sample device tags found:")
            unique_tags = {}
            for pos in device_tags:
                if pos.device_tag not in unique_tags:
                    unique_tags[pos.device_tag] = pos

            for tag in sorted(unique_tags.keys())[:20]:
                pos = unique_tags[tag]
                print(f"  {tag:20s} on page {pos.page + 1:2d}")
            print()

    # Expected result: 0 cross-references found (all filtered)
    success = len(cross_refs) == 0

    if success:
        print("✓ SUCCESS: All cross-references correctly filtered out")
    else:
        print(f"✗ FAILURE: Found {len(cross_refs)} cross-references (should be 0)")

    print()
    return success


def main():
    """Run all validation tests."""
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "CROSS-REFERENCE FILTERING VALIDATION" + " " * 22 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    # Test pattern matching
    pattern_success = test_cross_ref_pattern()

    # Test on real PDF
    pdf_success = test_real_pdf()

    # Summary
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print()
    print(f"Pattern Matching: {'✓ PASS' if pattern_success else '✗ FAIL'}")
    print(f"Real PDF Testing: {'✓ PASS' if pdf_success else '✗ FAIL'}")
    print()

    if pattern_success and pdf_success:
        print("✓ ALL VALIDATIONS PASSED")
        print()
        print("Cross-reference filtering is working correctly.")
        print("Device tags are properly distinguished from cross-references.")
        return 0
    else:
        print("✗ SOME VALIDATIONS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
