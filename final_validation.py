#!/usr/bin/env python3
"""Final validation - comprehensive check of all 36 extracted parts."""

from pathlib import Path
from electrical_schematics.pdf.ocr_parts_extractor import OCRPartsExtractor

pdf_path = Path("DRAWER.pdf")
extractor = OCRPartsExtractor(pdf_path)

print("=" * 80)
print("FINAL VALIDATION - ALL 36 PARTS")
print("=" * 80)

# Extract all parts
parts = extractor.extract_parts(page_numbers=[25, 26], use_ocr=False)

print(f"\nTotal parts extracted: {len(parts)}")
print("\n" + "-" * 80)
print(f"{'Device Tag':<12} | {'Designation':<30} | {'Part Number':<25}")
print("-" * 80)

for part in sorted(parts, key=lambda p: p.device_tag):
    # Truncate long strings for display
    designation = part.designation[:30] if part.designation else '(EMPTY)'
    part_num = part.type_designation[:25] if part.type_designation else '(EMPTY)'

    print(f"{part.device_tag:<12} | {designation:<30} | {part_num:<25}")

# Validation checks
print("\n" + "=" * 80)
print("VALIDATION CHECKS")
print("=" * 80)

issues = []

# Check 1: Count
if len(parts) != 36:
    issues.append(f"Expected 36 parts, got {len(parts)}")
else:
    print("✓ Part count: 36")

# Check 2: No empty designations
empty_designations = [p for p in parts if not p.designation or p.designation.strip() == '']
if empty_designations:
    issues.append(f"Found {len(empty_designations)} parts with empty designations: {[p.device_tag for p in empty_designations]}")
else:
    print("✓ All parts have designations")

# Check 3: No empty type designations
empty_types = [p for p in parts if not p.type_designation or p.type_designation.strip() == '']
if empty_types:
    issues.append(f"Found {len(empty_types)} parts with empty type designations: {[p.device_tag for p in empty_types]}")
else:
    print("✓ All parts have type designations")

# Check 4: No German text (using language filter)
from electrical_schematics.pdf.language_filter import is_likely_german_line
german_parts = [p for p in parts if is_likely_german_line(p.designation)]
if german_parts:
    issues.append(f"Found {len(german_parts)} parts with German designations: {[(p.device_tag, p.designation) for p in german_parts]}")
else:
    print("✓ All designations are in English")

# Check 5: No internal E-codes in type designations
import re
internal_code_pattern = re.compile(r'\bE\d{4,}\b')
parts_with_ecodes = [p for p in parts if internal_code_pattern.search(p.type_designation)]
if parts_with_ecodes:
    issues.append(f"Found {len(parts_with_ecodes)} parts with E-codes in type designation: {[(p.device_tag, p.type_designation) for p in parts_with_ecodes]}")
else:
    print("✓ No internal E-codes in type designations")

# Check 6: All device tags follow standard format
invalid_tags = [p for p in parts if not (p.device_tag.startswith('-') or p.device_tag.startswith('+'))]
if invalid_tags:
    issues.append(f"Found {len(invalid_tags)} parts with invalid device tags: {[p.device_tag for p in invalid_tags]}")
else:
    print("✓ All device tags follow standard format")

# Summary
print("\n" + "=" * 80)
if not issues:
    print("✓✓✓ ALL VALIDATION CHECKS PASSED ✓✓✓")
    print("\nExtraction is COMPLETE and CORRECT!")
    print("  - 36 parts extracted")
    print("  - All in English")
    print("  - All with valid type designations")
    print("  - No internal codes leaked through")
else:
    print("✗✗✗ VALIDATION FAILED ✗✗✗")
    print("\nIssues found:")
    for issue in issues:
        print(f"  - {issue}")

print("=" * 80)
