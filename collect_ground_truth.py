#!/usr/bin/env python3
"""
Ground Truth Data Collection Helper

Interactive tool to help manually collect device tags from problematic pages.
Displays each page and extracts all text, helping identify which tags should
be found by the auto-placement algorithm.

Usage:
    python collect_ground_truth.py
    python collect_ground_truth.py --page 9
"""

import argparse
import re
from pathlib import Path
from typing import List, Set

import fitz  # PyMuPDF


class GroundTruthCollector:
    """Helper to collect ground truth data from PDF pages."""

    # Pattern for device tags
    DEVICE_TAG_PATTERN = re.compile(r'[+-][A-Z0-9]+(?:-[A-Z0-9]+)?(?::[^\s/]*)?')

    # Pattern for cross-reference tags (blue navigation references to skip)
    CROSS_REF_PATTERN = re.compile(r'[A-Z0-9]+:\d+/[\d.]+')

    def __init__(self, pdf_path: Path):
        self.pdf_path = Path(pdf_path)
        self.doc = None

    def __enter__(self):
        self.doc = fitz.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.doc:
            self.doc.close()

    def extract_potential_tags(self, page_num: int) -> Set[str]:
        """Extract all text that looks like device tags from a page.

        Args:
            page_num: 0-indexed page number

        Returns:
            Set of potential device tags found on the page
        """
        if not self.doc or page_num < 0 or page_num >= len(self.doc):
            return set()

        page = self.doc[page_num]

        # Get all text with position info
        text_dict = page.get_text("dict")

        potential_tags = set()

        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:  # Only text blocks
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()

                    # Check if it matches device tag pattern
                    if self.DEVICE_TAG_PATTERN.match(text):
                        # Exclude cross-reference tags (navigation references)
                        if not self.CROSS_REF_PATTERN.match(text):
                            potential_tags.add(text)

        return potential_tags

    def get_page_info(self, page_num: int) -> dict:
        """Get information about a page.

        Args:
            page_num: 0-indexed page number

        Returns:
            Dictionary with page information
        """
        if not self.doc or page_num < 0 or page_num >= len(self.doc):
            return {}

        page = self.doc[page_num]

        # Get page title (from title block at bottom)
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
        title = ""

        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if text and len(text) > 3:
                        title = text
                        break
                if title:
                    break
            if title:
                break

        return {
            'page_num': page_num,
            'page_num_1indexed': page_num + 1,
            'title': title,
            'width': page_rect.width,
            'height': page_rect.height
        }

    def display_page_analysis(self, page_num: int):
        """Display analysis of a page with potential device tags.

        Args:
            page_num: 0-indexed page number
        """
        info = self.get_page_info(page_num)
        tags = self.extract_potential_tags(page_num)

        print(f"\n{'='*70}")
        print(f"PAGE {info['page_num_1indexed']} ANALYSIS")
        print(f"{'='*70}")
        print(f"Title: {info['title']}")
        print(f"Dimensions: {info['width']:.0f} x {info['height']:.0f} points")
        print(f"\nPotential Device Tags Found: {len(tags)}")
        print(f"{'='*70}")

        if tags:
            # Group by prefix for easier review
            panel_tags = sorted([t for t in tags if t.startswith('-')])
            field_tags = sorted([t for t in tags if t.startswith('+')])

            if panel_tags:
                print(f"\nPanel/Control Devices (- prefix): {len(panel_tags)}")
                for i, tag in enumerate(panel_tags, 1):
                    print(f"  {i:2d}. {tag}")

            if field_tags:
                print(f"\nField Devices (+ prefix): {len(field_tags)}")
                for i, tag in enumerate(field_tags, 1):
                    print(f"  {i:2d}. {tag}")
        else:
            print("\nNo device tags found!")

        print(f"\n{'='*70}")

        return info, tags

    def generate_ground_truth_entry(self, page_num: int, tags: Set[str]) -> str:
        """Generate Python code for GROUND_TRUTH entry.

        Args:
            page_num: 0-indexed page number
            tags: Set of verified device tags

        Returns:
            Python code string for GROUND_TRUTH entry
        """
        info = self.get_page_info(page_num)

        code = f"    {page_num}: {{\n"
        code += f"        'title': '{info['title']}',\n"
        code += f"        'tags': [\n"

        # Sort tags by type and name
        panel_tags = sorted([t for t in tags if t.startswith('-')])
        field_tags = sorted([t for t in tags if t.startswith('+')])

        if panel_tags:
            code += "            # Panel/Control devices\n"
            for tag in panel_tags:
                code += f"            '{tag}',\n"

        if field_tags:
            if panel_tags:
                code += "\n"
            code += "            # Field devices\n"
            for tag in field_tags:
                code += f"            '{tag}',\n"

        code += "        ]\n"
        code += "    },"

        return code

    def interactive_collection(self, page_numbers: List[int]):
        """Interactive collection mode for multiple pages.

        Args:
            page_numbers: List of 0-indexed page numbers to process
        """
        print("\n" + "="*70)
        print("GROUND TRUTH DATA COLLECTION")
        print("="*70)
        print("\nThis tool will help you collect device tags from each page.")
        print("Review the automatically extracted tags and verify they are correct.")
        print("\nExclude cross-reference tags (blue text like K2:61/19.9)")
        print("="*70)

        ground_truth_entries = []

        for page_num in page_numbers:
            info, tags = self.display_page_analysis(page_num)

            print("\nActions:")
            print("  [a] Accept all tags")
            print("  [e] Edit tag list manually")
            print("  [s] Skip this page")
            print("  [q] Quit")

            choice = input("\nChoice: ").strip().lower()

            if choice == 'q':
                break
            elif choice == 's':
                continue
            elif choice == 'e':
                print("\nEnter tags (comma-separated, or blank to skip):")
                tag_input = input("> ").strip()
                if tag_input:
                    tags = set(t.strip() for t in tag_input.split(','))
                else:
                    continue
            elif choice != 'a':
                print("Invalid choice, skipping page.")
                continue

            # Generate entry
            entry = self.generate_ground_truth_entry(page_num, tags)
            ground_truth_entries.append(entry)

        # Output final GROUND_TRUTH dictionary
        if ground_truth_entries:
            print("\n" + "="*70)
            print("COPY THIS INTO test_auto_placement_pages.py")
            print("="*70)
            print("\nGROUND_TRUTH = {")
            for entry in ground_truth_entries:
                print(entry)
            print("}")
            print("\n" + "="*70)


def main():
    parser = argparse.ArgumentParser(
        description='Collect ground truth data for auto-placement testing'
    )
    parser.add_argument(
        '--pdf',
        default='examples/DRAWER.pdf',
        help='Path to DRAWER.pdf (default: examples/DRAWER.pdf)'
    )
    parser.add_argument(
        '--page',
        type=int,
        help='Analyze only this specific page (1-indexed)'
    )

    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        return 1

    # Problematic pages (0-indexed)
    problematic_pages = [8, 9, 14, 15, 18, 19, 21]  # 9, 10, 15, 16, 19, 20, 22 in 1-indexed

    if args.page:
        problematic_pages = [args.page - 1]

    with GroundTruthCollector(pdf_path) as collector:
        collector.interactive_collection(problematic_pages)

    return 0


if __name__ == '__main__':
    exit(main())
