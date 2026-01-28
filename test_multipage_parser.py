"""Test multi-page parts list parsing."""

from pathlib import Path
from electrical_schematics.pdf.exact_parts_parser import (
    find_parts_list_pages,
    parse_parts_list,
    PartData
)

def test_multipage_parsing():
    """Test parsing multiple parts list pages from DRAWER.pdf."""
    pdf_path = Path('/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf')

    if not pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}")
        return

    print("=" * 70)
    print("TESTING MULTI-PAGE PARTS LIST PARSING")
    print("=" * 70)

    # Step 1: Find all parts list pages
    print("\n1. Finding parts list pages...")
    pages = find_parts_list_pages(pdf_path)
    print(f"   Found {len(pages)} parts list page(s): {pages}")

    # Step 2: Parse all parts
    print("\n2. Parsing all parts lists...")
    parts = parse_parts_list(pdf_path)
    print(f"   Total parts extracted: {len(parts)}")

    # Step 3: Show summary by page
    if pages:
        print(f"\n3. Expected: 36 components on 2 pages (per user)")
        print(f"   Actual: {len(parts)} components on {len(pages)} page(s)")

    # Step 4: Show all parts
    print("\n4. All extracted parts:")
    print("-" * 70)

    for i, part in enumerate(parts, 1):
        desc = part.designation[:40] + "..." if len(part.designation) > 40 else part.designation
        type_d = part.type_designation[:30] if part.type_designation else "N/A"
        print(f"{i:3d}. {part.device_tag:10s} | {desc:43s} | {type_d}")

    # Step 5: Summary statistics
    print("\n" + "-" * 70)
    print("\n5. Summary Statistics:")
    with_designation = sum(1 for p in parts if p.designation)
    with_tech_data = sum(1 for p in parts if p.technical_data)
    with_type_desig = sum(1 for p in parts if p.type_designation)

    print(f"   Total parts:           {len(parts)}")
    print(f"   With description:      {with_designation} ({100*with_designation/max(len(parts),1):.1f}%)")
    print(f"   With technical data:   {with_tech_data} ({100*with_tech_data/max(len(parts),1):.1f}%)")
    print(f"   With part number:      {with_type_desig} ({100*with_type_desig/max(len(parts),1):.1f}%)")

    # Verify against expected
    print("\n6. Verification:")
    if len(parts) >= 36:
        print(f"   ✓ Found at least 36 components (actual: {len(parts)})")
    else:
        print(f"   ⚠ Expected 36 components, found {len(parts)}")

    if len(pages) >= 2:
        print(f"   ✓ Found 2+ parts list pages (actual: {len(pages)})")
    else:
        print(f"   ⚠ Expected 2 pages, found {len(pages)}")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    test_multipage_parsing()
