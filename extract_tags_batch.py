#!/usr/bin/env python3
"""
Batch extract device tags from problematic pages.

Non-interactive version that extracts all potential tags and
generates ground truth data automatically.
"""

import re
from pathlib import Path
from typing import Set

import fitz  # PyMuPDF


DEVICE_TAG_PATTERN = re.compile(r'[+-][A-Z0-9]+(?:-[A-Z0-9]+)?(?::[^\s/]*)?')
CROSS_REF_PATTERN = re.compile(r'[A-Z0-9]+:\d+/[\d.]+')

# Problematic pages to analyze (0-indexed)
PROBLEMATIC_PAGES = [8, 9, 14, 15, 18, 19, 21]  # Pages 9, 10, 15, 16, 19, 20, 22 (1-indexed)


def get_page_title(page) -> str:
    """Extract page title from title block."""
    page_rect = page.rect
    ph = page_rect.height
    pw = page_rect.width

    title_block_region = fitz.Rect(
        pw * 0.55,
        ph * 0.94,
        pw * 0.72,
        ph * 0.98
    )

    text_dict = page.get_text("dict", clip=title_block_region)

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if text and len(text) > 3:
                    return text

    return "Unknown"


def extract_tags(page) -> Set[str]:
    """Extract all device tags from a page."""
    text_dict = page.get_text("dict")
    tags = set()

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue

        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()

                # Check if it matches device tag pattern
                if DEVICE_TAG_PATTERN.match(text):
                    # Exclude cross-reference tags
                    if not CROSS_REF_PATTERN.match(text):
                        # Exclude overly long tags (likely false positives)
                        if len(text) < 30:
                            tags.add(text)

    return tags


def main():
    pdf_path = Path('examples/DRAWER.pdf')

    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return 1

    with fitz.open(pdf_path) as doc:
        print("# Ground Truth Data Extraction Results\n")
        print("Copy this into test_auto_placement_pages.py:\n")
        print("```python")
        print("GROUND_TRUTH = {")

        for page_num in PROBLEMATIC_PAGES:
            page = doc[page_num]
            title = get_page_title(page)
            tags = extract_tags(page)

            print(f"    {page_num}: {{")
            print(f"        'title': '{title}',")
            print(f"        'tags': [")

            # Sort tags
            panel_tags = sorted([t for t in tags if t.startswith('-')])
            field_tags = sorted([t for t in tags if t.startswith('+')])

            if panel_tags:
                print("            # Panel/Control devices")
                for tag in panel_tags:
                    print(f"            '{tag}',")

            if field_tags:
                if panel_tags:
                    print()
                print("            # Field devices")
                for tag in field_tags:
                    print(f"            '{tag}',")

            print("        ]")
            print("    },")

        print("}")
        print("```")

        print("\n# Per-Page Summary\n")
        for page_num in PROBLEMATIC_PAGES:
            page = doc[page_num]
            title = get_page_title(page)
            tags = extract_tags(page)

            print(f"## Page {page_num + 1}: {title}")
            print(f"- Total tags: {len(tags)}")
            print(f"- Panel devices (-): {len([t for t in tags if t.startswith('-')])}")
            print(f"- Field devices (+): {len([t for t in tags if t.startswith('+')])}")
            print()

    return 0


if __name__ == '__main__':
    exit(main())
