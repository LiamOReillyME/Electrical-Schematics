#!/usr/bin/env python3
"""Diagnostic test for component auto-placement accuracy.

This script analyzes why auto-placement is only ~40% accurate by:
1. Extracting the complete parts list (expected components)
2. Running auto-placement algorithm
3. Comparing expected vs actual placements
4. Identifying root causes of failures
"""

from pathlib import Path
from collections import defaultdict

from electrical_schematics.pdf.exact_parts_parser import parse_parts_list
from electrical_schematics.pdf.component_position_finder import ComponentPositionFinder


def main():
    # Path to test PDF
    pdf_path = Path("/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf")

    if not pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}")
        return

    print("=" * 80)
    print("COMPONENT AUTO-PLACEMENT DIAGNOSTIC REPORT")
    print("=" * 80)
    print()

    # Step 1: Extract parts list
    print("Step 1: Extracting Parts List")
    print("-" * 80)
    parts = parse_parts_list(pdf_path)
    device_tags = [part.device_tag for part in parts]

    print(f"Total parts found: {len(parts)}")
    print(f"Device tags: {', '.join(sorted(device_tags))}")
    print()

    # Display parts details
    print("Parts Details:")
    for part in sorted(parts, key=lambda p: p.device_tag):
        print(f"  {part.device_tag:12} | {part.designation[:40]:40} | {part.technical_data[:30]:30}")
    print()

    # Step 2: Open position finder and classify pages
    print("Step 2: Page Classification")
    print("-" * 80)

    finder = ComponentPositionFinder(pdf_path)
    page_classifications = finder.classify_all_pages()

    total_pages = len(page_classifications)
    schematic_pages = []
    skipped_pages = []

    for page_num, title in page_classifications.items():
        if finder._should_skip_page(page_num):
            skipped_pages.append((page_num, title))
        else:
            schematic_pages.append((page_num, title))

    print(f"Total pages: {total_pages}")
    print(f"Schematic pages: {len(schematic_pages)}")
    print(f"Skipped pages: {len(skipped_pages)}")
    print()

    print("Schematic pages (will be searched):")
    for page_num, title in sorted(schematic_pages):
        title_str = f'"{title}"' if title else "(no title)"
        print(f"  Page {page_num + 1:2d}: {title_str}")
    print()

    print("Skipped pages (will NOT be searched):")
    for page_num, title in sorted(skipped_pages):
        print(f"  Page {page_num + 1:2d}: \"{title}\"")
    print()

    # Step 3: Run auto-placement
    print("Step 3: Running Auto-Placement")
    print("-" * 80)

    result = finder.find_positions(device_tags, search_all_pages=False)

    placed_count = len(result.positions)
    unmatched_count = len(result.unmatched_tags)
    multi_page_count = len(result.ambiguous_matches)
    success_rate = (placed_count / len(device_tags) * 100) if device_tags else 0

    print(f"Components placed: {placed_count}/{len(device_tags)} ({success_rate:.1f}%)")
    print(f"Unmatched tags: {unmatched_count}")
    print(f"Multi-page components: {multi_page_count}")
    print()

    # Step 4: Detailed placement analysis
    print("Step 4: Placement Details")
    print("-" * 80)

    print("\nSuccessfully Placed Components:")
    for tag in sorted(result.positions.keys()):
        pos = result.positions[tag]
        match_type_str = f"[{pos.match_type}, conf={pos.confidence:.2f}]"
        multi_page_marker = " (multi-page)" if tag in result.ambiguous_matches else ""
        print(f"  {tag:12} | Page {pos.page + 1:2d} | ({pos.x:7.1f}, {pos.y:6.1f}) | {match_type_str:30} {multi_page_marker}")

        # If multi-page, show all pages
        if tag in result.ambiguous_matches:
            for alt_pos in result.ambiguous_matches[tag]:
                if alt_pos.page != pos.page:
                    print(f"               | Page {alt_pos.page + 1:2d} | ({alt_pos.x:7.1f}, {alt_pos.y:6.1f}) | (alternate position)")
    print()

    print("Unmatched Components (NOT FOUND):")
    for tag in sorted(result.unmatched_tags):
        # Find the part info
        part_info = next((p for p in parts if p.device_tag == tag), None)
        if part_info:
            print(f"  {tag:12} | {part_info.designation[:50]:50} | Tech: {part_info.technical_data[:30]:30}")
        else:
            print(f"  {tag:12} | (no part info)")
    print()

    # Step 5: Root cause analysis
    print("Step 5: Root Cause Analysis")
    print("-" * 80)
    print()

    # Analyze unmatched components
    if result.unmatched_tags:
        print("Analyzing why components were not found:")
        print()

        # Try to find tags manually by searching all pages
        print("  Attempting manual search on ALL pages (including skipped)...")
        finder_all_pages = ComponentPositionFinder(pdf_path)
        result_all_pages = finder_all_pages.find_positions(
            list(result.unmatched_tags),
            search_all_pages=True
        )

        found_on_skipped = set()
        still_missing = set()

        for tag in result.unmatched_tags:
            if tag in result_all_pages.positions:
                pos = result_all_pages.positions[tag]
                found_on_skipped.add(tag)
                page_title = finder_all_pages.get_page_title(pos.page)
                print(f"    {tag:12} FOUND on Page {pos.page + 1} (skipped page: \"{page_title}\")")
            else:
                still_missing.add(tag)

        print()
        print(f"  Found on skipped pages: {len(found_on_skipped)}")
        print(f"  Still missing after all-page search: {len(still_missing)}")
        print()

        if still_missing:
            print("  Components still missing after all-page search:")
            for tag in sorted(still_missing):
                part_info = next((p for p in parts if p.device_tag == tag), None)
                if part_info:
                    print(f"    {tag:12} | {part_info.designation[:50]:50}")

                    # Check if tag appears in parts list but nowhere in PDF text
                    # This could indicate:
                    # 1. Tag is on a drawing/image instead of text
                    # 2. Tag has different formatting in schematic vs parts list
                    # 3. Tag doesn't actually appear on schematic pages
            print()

        finder_all_pages.close()

    # Step 6: Summary and recommendations
    print("Step 6: Summary and Recommendations")
    print("-" * 80)
    print()

    # Calculate statistics
    found_correctly = placed_count
    found_on_wrong_pages = len(found_on_skipped) if 'found_on_skipped' in locals() else 0
    truly_missing = len(still_missing) if 'still_missing' in locals() else unmatched_count

    print("ROOT CAUSES IDENTIFIED:")
    print()

    cause_num = 1

    if found_on_wrong_pages > 0:
        print(f"{cause_num}. PAGE CLASSIFICATION ERROR ({found_on_wrong_pages} components, {found_on_wrong_pages/len(device_tags)*100:.1f}%)")
        print(f"   - {found_on_wrong_pages} components exist in PDF but are on pages marked as 'skip'")
        print(f"   - These pages may be incorrectly classified")
        print(f"   - Examples: {', '.join(list(found_on_skipped)[:5])}")
        print()
        cause_num += 1

    if truly_missing > 0:
        print(f"{cause_num}. TEXT EXTRACTION FAILURE ({truly_missing} components, {truly_missing/len(device_tags)*100:.1f}%)")
        print(f"   - {truly_missing} components could not be found even on all pages")
        print(f"   - Possible reasons:")
        print(f"     a) Tags are in images/drawings, not extractable text")
        print(f"     b) Tags have different formatting in schematic vs parts list")
        print(f"     c) Tags genuinely don't appear on schematic pages")
        print(f"     d) OCR needed (PDF is scanned images, not vector text)")
        print(f"   - Examples: {', '.join(list(still_missing)[:5])}")
        print()
        cause_num += 1

    if multi_page_count > 0:
        print(f"{cause_num}. MULTI-PAGE COMPONENTS ({multi_page_count} components)")
        print(f"   - {multi_page_count} components appear on multiple pages")
        print(f"   - Algorithm correctly handles this (picks best position)")
        print(f"   - This is EXPECTED behavior, not a problem")
        print()
        cause_num += 1

    print("RECOMMENDATIONS:")
    print()

    rec_num = 1
    if found_on_wrong_pages > 0:
        print(f"{rec_num}. Review page classification logic")
        print(f"   - Check title block detection accuracy")
        print(f"   - Some 'cable diagram' or 'parts list' pages may contain schematics")
        print(f"   - Consider hybrid approach: search certain skipped pages anyway")
        print()
        rec_num += 1

    if truly_missing > 0:
        print(f"{rec_num}. Investigate text extraction issues")
        print(f"   - Check if PDF uses vector text or scanned images")
        print(f"   - Test with PyMuPDF text extraction on specific pages")
        print(f"   - May need computer vision / OCR for image-based tags")
        print()
        rec_num += 1

    if success_rate < 80:
        print(f"{rec_num}. Consider fuzzy matching")
        print(f"   - Some tags may have slight variations (spacing, case, special chars)")
        print(f"   - Implement Levenshtein distance or similar for partial matches")
        print()

    print("=" * 80)
    print(f"FINAL ACCURACY: {success_rate:.1f}% ({placed_count}/{len(device_tags)} components)")
    print("=" * 80)

    finder.close()


if __name__ == "__main__":
    main()
