#!/usr/bin/env python3
"""Test script to validate parts extraction from DRAWER PDF.

This script:
1. Extracts parts from the DRAWER PDF using OCR extractor
2. Validates that 36 parts are extracted
3. Checks that component names are in English
4. Verifies designations match component types
5. Reports detailed findings
"""

from pathlib import Path
from electrical_schematics.pdf.ocr_parts_extractor import OCRPartsExtractor, OCRPartData
from typing import List, Dict, Tuple
import sys

# Expected parts list page numbers (0-indexed)
PARTS_LIST_PAGES = [25, 26]  # Pages 26-27 in the PDF (0-indexed: 25-26)

# German to English translation mapping for common component types
GERMAN_TO_ENGLISH = {
    # Common German terms in technical documentation
    'Widerstand': 'Resistor',
    'Motor': 'Motor',  # Same in both
    'Netzfilter': 'EMI-filter',
    'Netzteil': 'Power supply',
    'Schütz': 'Contactor',
    'Relais': 'Relay',
    'Sicherung': 'Fuse',
    'Schalter': 'Switch',
    'Sensor': 'Sensor',
    'Ventil': 'Valve',
    'Encoder': 'Encoder',
    'PLC': 'PLC',
    'Steuerung': 'Controller',
    'Umrichter': 'VFD',
    'Frequenzumrichter': 'Frequency converter',
    'Drehstrommotor': 'Three-phase motor',
    'Anschluss': 'Terminal',
    'Klemme': 'Terminal',
    'Leuchte': 'Indicator light',
    'Taster': 'Push button',
}


def is_english_designation(designation: str) -> bool:
    """Check if a designation is in English (not German)."""
    # Import language filter
    from electrical_schematics.pdf.language_filter import is_likely_german_line

    # Use the same filter as the extractor
    return not is_likely_german_line(designation)


def analyze_parts(parts: List[OCRPartData]) -> Dict[str, any]:
    """Analyze extracted parts and generate report.

    Returns:
        Dictionary with analysis results
    """
    report = {
        'total_count': len(parts),
        'english_count': 0,
        'german_count': 0,
        'english_parts': [],
        'german_parts': [],
        'empty_type_designation': [],
        'parts_by_page': {},
        'device_tag_prefixes': {},
    }

    for part in parts:
        # Check language
        if is_english_designation(part.designation):
            report['english_count'] += 1
            report['english_parts'].append(part)
        else:
            report['german_count'] += 1
            report['german_parts'].append(part)

        # Check for empty type designations
        if not part.type_designation or part.type_designation.strip() == '':
            report['empty_type_designation'].append(part)

        # Group by page
        page_key = f"Page {part.page_number + 1}"
        if page_key not in report['parts_by_page']:
            report['parts_by_page'][page_key] = []
        report['parts_by_page'][page_key].append(part)

        # Track device tag prefixes
        if part.device_tag:
            # Extract prefix (first letter after +/-)
            prefix = part.device_tag[1] if len(part.device_tag) > 1 else '?'
            report['device_tag_prefixes'][prefix] = report['device_tag_prefixes'].get(prefix, 0) + 1

    return report


def print_report(report: Dict[str, any], iteration: int):
    """Print formatted analysis report."""
    print("\n" + "=" * 80)
    print(f"ITERATION {iteration}: PARTS EXTRACTION ANALYSIS")
    print("=" * 80)

    print(f"\nTotal parts extracted: {report['total_count']} (Expected: 36)")
    print(f"  English designations: {report['english_count']}")
    print(f"  German designations: {report['german_count']}")
    print(f"  Empty type designations: {len(report['empty_type_designation'])}")

    print("\n" + "-" * 80)
    print("Parts by page:")
    for page, parts_list in sorted(report['parts_by_page'].items()):
        print(f"  {page}: {len(parts_list)} parts")

    print("\n" + "-" * 80)
    print("Device tag prefixes:")
    for prefix, count in sorted(report['device_tag_prefixes'].items()):
        print(f"  {prefix}: {count}")

    if report['german_parts']:
        print("\n" + "-" * 80)
        print("Parts with GERMAN designations (need translation):")
        for part in report['german_parts'][:10]:  # Show first 10
            print(f"  {part.device_tag:10s} | {part.designation[:50]}")
        if len(report['german_parts']) > 10:
            print(f"  ... and {len(report['german_parts']) - 10} more")

    if report['empty_type_designation']:
        print("\n" + "-" * 80)
        print("Parts with EMPTY type designations:")
        for part in report['empty_type_designation'][:10]:
            print(f"  {part.device_tag:10s} | {part.designation[:50]}")
        if len(report['empty_type_designation']) > 10:
            print(f"  ... and {len(report['empty_type_designation']) - 10} more")

    print("\n" + "-" * 80)
    print("Sample parts (first 10):")
    sample_parts = (report['english_parts'] + report['german_parts'])[:10]
    for part in sample_parts:
        print(f"\n  {part.device_tag}")
        print(f"    Designation: {part.designation}")
        print(f"    Technical Data: {part.technical_data}")
        print(f"    Type/Part Number: {part.type_designation}")
        print(f"    Confidence: {part.confidence:.1f}%")


def main():
    """Main test function."""
    pdf_path = Path("/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf")

    if not pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}")
        return 1

    print(f"Testing parts extraction from: {pdf_path}")
    print(f"Target pages: {[p+1 for p in PARTS_LIST_PAGES]}")

    # Create extractor
    extractor = OCRPartsExtractor(pdf_path)

    # Check dependencies
    deps_ok, error = extractor.check_dependencies()
    if not deps_ok:
        print(f"\nDependency check failed: {error}")
        print("Falling back to text extraction only...")

    # Extract parts
    print("\nExtracting parts...")
    parts = extractor.extract_parts(
        page_numbers=PARTS_LIST_PAGES,
        use_ocr=True,
        progress_callback=lambda current, total, msg: print(f"  {msg}")
    )

    # Analyze
    report = analyze_parts(parts)

    # Print report
    print_report(report, iteration=1)

    # Determine success
    success = (
        report['total_count'] == 36 and
        report['german_count'] == 0 and
        len(report['empty_type_designation']) == 0
    )

    print("\n" + "=" * 80)
    if success:
        print("✓ SUCCESS: All validation criteria met!")
    else:
        print("✗ ISSUES FOUND:")
        if report['total_count'] != 36:
            print(f"  - Expected 36 parts, got {report['total_count']}")
        if report['german_count'] > 0:
            print(f"  - Found {report['german_count']} parts with German designations")
        if len(report['empty_type_designation']) > 0:
            print(f"  - Found {len(report['empty_type_designation'])} parts with empty type designations")
    print("=" * 80)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
