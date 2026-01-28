#!/usr/bin/env python3
"""Debug script to investigate auto-placement accuracy issues.

Tests component position finding on problematic pages to identify:
- Text extraction failures
- Coordinate calculation errors
- Cross-reference filtering issues
- Missing device tags
"""

import sys
from pathlib import Path
from collections import defaultdict
import re

import fitz  # PyMuPDF

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from electrical_schematics.pdf.component_position_finder import (
    ComponentPositionFinder,
    classify_page,
    should_skip_page_by_title,
)


def extract_all_text_with_metadata(page: fitz.Page) -> list:
    """Extract all text from a page with detailed metadata.

    Returns list of dicts with:
    - text: The text content
    - bbox: Bounding box (x0, y0, x1, y1)
    - color: RGB color tuple (if available)
    - font_size: Font size
    - font_name: Font name
    """
    text_dict = page.get_text("dict")
    results = []

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:  # Only text blocks
            continue

        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if not text:
                    continue

                bbox = span.get("bbox", (0, 0, 0, 0))
                color = span.get("color", None)
                font_size = span.get("size", 0)
                font_name = span.get("font", "")

                results.append({
                    "text": text,
                    "bbox": bbox,
                    "color": color,
                    "font_size": font_size,
                    "font_name": font_name,
                })

    return results


def is_cross_reference(text: str, metadata: dict) -> bool:
    """Check if text is a cross-reference (should be filtered out).

    Cross-references appear in blue text and have format: TAG:PAGE/COORDINATE
    Example: "K2:61/19.9" means K2 is on page 61 at y-coordinate 19.9
    """
    # Pattern: TAG:PAGE/COORDINATE
    cross_ref_pattern = r'^[A-Z0-9+-]+:\d+/[\d.]+$'
    if re.match(cross_ref_pattern, text):
        return True

    # Check for blue text (RGB: 0, 0, 255 or similar)
    # PyMuPDF color is an integer, convert to RGB
    color = metadata.get("color")
    if color is not None:
        # Extract RGB components from integer
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF

        # Check if blue-dominant (b > r and b > g)
        if b > 200 and r < 100 and g < 100:
            return True

    return False


def looks_like_device_tag(text: str) -> bool:
    """Check if text looks like a device tag."""
    # Standard device tag pattern
    device_tag_pattern = r'^[+-]?[A-Z0-9]+(?:-[A-Z0-9]+)?(?::\S+)?$'
    return bool(re.match(device_tag_pattern, text))


def analyze_page(pdf_path: Path, page_num: int, expected_tags: list = None) -> dict:
    """Analyze a single page for device tags.

    Args:
        pdf_path: Path to PDF
        page_num: Page number (0-indexed)
        expected_tags: Optional list of tags we expect to find

    Returns:
        Dict with analysis results
    """
    doc = fitz.open(pdf_path)
    page = doc[page_num]

    # Get page classification
    title = classify_page(page)
    should_skip = should_skip_page_by_title(title)

    # Extract all text
    all_text = extract_all_text_with_metadata(page)

    # Filter to device-tag-like text
    device_tags = []
    cross_refs = []

    for item in all_text:
        text = item["text"]

        # Check if cross-reference
        if is_cross_reference(text, item):
            cross_refs.append(item)
            continue

        # Check if looks like device tag
        if looks_like_device_tag(text):
            device_tags.append(item)

    # Extract unique tag names (ignoring terminal references)
    found_tags = set()
    for item in device_tags:
        text = item["text"]
        # Strip terminal references like ":13" or "-X5:3"
        base_tag = re.sub(r'[-:].*$', '', text)
        if not base_tag:
            base_tag = text
        found_tags.add(base_tag)

    result = {
        "page_num": page_num,
        "title": title,
        "should_skip": should_skip,
        "total_text_blocks": len(all_text),
        "device_tag_candidates": len(device_tags),
        "cross_references": len(cross_refs),
        "unique_tags": sorted(found_tags),
        "all_device_tags": device_tags,
        "all_cross_refs": cross_refs,
    }

    # Compare to expected if provided
    if expected_tags:
        expected_set = set(expected_tags)
        found_set = found_tags
        missing = expected_set - found_set
        unexpected = found_set - expected_set

        result["expected_tags"] = sorted(expected_tags)
        result["missing_tags"] = sorted(missing)
        result["unexpected_tags"] = sorted(unexpected)
        result["accuracy"] = len(found_set & expected_set) / len(expected_set) if expected_set else 0.0

    doc.close()
    return result


def test_position_finder(pdf_path: Path, tags_to_find: list, page_range: tuple = None) -> dict:
    """Test the ComponentPositionFinder on specific tags.

    Args:
        pdf_path: Path to PDF
        tags_to_find: List of device tags to search for
        page_range: Optional (start, end) page range

    Returns:
        Dict with test results
    """
    with ComponentPositionFinder(pdf_path, page_range) as finder:
        result = finder.find_positions(tags_to_find)

        return {
            "total_tags": len(tags_to_find),
            "found_tags": len(result.positions),
            "unmatched_tags": sorted(result.unmatched_tags),
            "ambiguous_matches": {k: len(v) for k, v in result.ambiguous_matches.items()},
            "skipped_pages": sorted(result.skipped_pages),
            "page_classifications": result.page_classifications,
            "positions": {
                tag: {
                    "page": pos.page,
                    "x": pos.x,
                    "y": pos.y,
                    "confidence": pos.confidence,
                    "match_type": pos.match_type,
                }
                for tag, pos in result.positions.items()
            }
        }


def main():
    """Run comprehensive debug analysis."""
    pdf_path = Path("/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf")

    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        return

    print("=" * 80)
    print("AUTO-PLACEMENT ACCURACY DEBUG")
    print("=" * 80)
    print()

    # Problem pages from bug report
    problem_pages = [9, 10, 15, 16, 19, 20, 22]

    # Test each problem page
    for page_num in problem_pages:
        print(f"\n{'='*80}")
        print(f"PAGE {page_num + 1} (0-indexed: {page_num})")
        print(f"{'='*80}")

        analysis = analyze_page(pdf_path, page_num)

        print(f"Title: {analysis['title']}")
        print(f"Should Skip: {analysis['should_skip']}")
        print(f"Total Text Blocks: {analysis['total_text_blocks']}")
        print(f"Device Tag Candidates: {analysis['device_tag_candidates']}")
        print(f"Cross-References: {analysis['cross_references']}")
        print(f"Unique Tags Found: {len(analysis['unique_tags'])}")
        print()

        # Show unique tags
        if analysis['unique_tags']:
            print("Tags found on page:")
            for tag in analysis['unique_tags']:
                print(f"  - {tag}")
        else:
            print("No tags found!")
        print()

        # Show cross-references
        if analysis['all_cross_refs']:
            print(f"Cross-references (should be filtered): {len(analysis['all_cross_refs'])}")
            for item in analysis['all_cross_refs'][:10]:  # Show first 10
                print(f"  - {item['text']} @ ({item['bbox'][0]:.1f}, {item['bbox'][1]:.1f})")
            if len(analysis['all_cross_refs']) > 10:
                print(f"  ... and {len(analysis['all_cross_refs']) - 10} more")
        print()

    # Now test with ComponentPositionFinder
    print(f"\n{'='*80}")
    print("TESTING ComponentPositionFinder")
    print(f"{'='*80}")
    print()

    # Get all unique tags from problem pages
    all_tags = set()
    for page_num in problem_pages:
        analysis = analyze_page(pdf_path, page_num)
        all_tags.update(analysis['unique_tags'])

    print(f"Total unique tags across problem pages: {len(all_tags)}")
    print(f"Tags: {sorted(all_tags)}")
    print()

    # Test position finder
    test_result = test_position_finder(
        pdf_path,
        list(all_tags),
        page_range=(0, 30)  # Search first 30 pages
    )

    print(f"Tags searched: {test_result['total_tags']}")
    print(f"Tags found: {test_result['found_tags']}")
    print(f"Accuracy: {test_result['found_tags'] / test_result['total_tags'] * 100:.1f}%")
    print()

    if test_result['unmatched_tags']:
        print(f"UNMATCHED TAGS ({len(test_result['unmatched_tags'])}):")
        for tag in test_result['unmatched_tags']:
            print(f"  - {tag}")
        print()

    print(f"Skipped Pages: {test_result['skipped_pages']}")
    print()

    # Show where tags were found
    print("Tag Positions:")
    for tag, pos in sorted(test_result['positions'].items()):
        print(f"  {tag:20s} -> Page {pos['page'] + 1:2d} @ ({pos['x']:6.1f}, {pos['y']:6.1f}) "
              f"[{pos['match_type']}, conf={pos['confidence']:.2f}]")


if __name__ == "__main__":
    main()
