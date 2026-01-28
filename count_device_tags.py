#!/usr/bin/env python3
"""Count all device tags visible on schematic pages in DRAWER.pdf.

This script:
1. Extracts the parts list from DRAWER.pdf (pages 26-27)
2. Identifies schematic pages (skips cover, TOC, cable diagrams, parts lists)
3. Counts occurrences of each device tag on each schematic page
4. Generates a comprehensive JSON report with tag counts and positions
5. Creates visual verification images for first 3 schematic pages

Output:
- TAG_COUNT_REPORT.json: Complete analysis of all tag occurrences
- tag_debug/tag_count_page_*.png: Visual verification images (first 3 pages)
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

import fitz  # PyMuPDF

# Import existing modules
import sys
sys.path.insert(0, str(Path(__file__).parent / "electrical_schematics"))

from electrical_schematics.pdf.drawer_parser import DrawerParser
from electrical_schematics.pdf.component_position_finder import (
    ComponentPositionFinder,
    classify_page,
    should_skip_page_by_title,
)


class DeviceTagCounter:
    """Count device tag occurrences across schematic pages."""

    # Regex pattern for device tags: +/- followed by alphanumeric, possibly with suffix
    DEVICE_TAG_PATTERN = re.compile(r'([+-][A-Z0-9]+(?:-[A-Z0-9]+)?)')

    def __init__(self, pdf_path: Path):
        """Initialize the counter.

        Args:
            pdf_path: Path to the DRAWER PDF file
        """
        self.pdf_path = Path(pdf_path)
        self.doc = fitz.open(self.pdf_path)
        self.parser = DrawerParser(self.pdf_path)
        self.finder = ComponentPositionFinder(self.pdf_path)

    def close(self):
        """Clean up resources."""
        if self.doc:
            self.doc.close()
        self.finder.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def extract_parts_list(self) -> List[str]:
        """Extract device tags from parts list (pages 26-27).

        Returns:
            List of device tags from the parts list
        """
        print("Extracting parts list from DRAWER.pdf...")
        diagram = self.parser.parse()
        device_tags = sorted(diagram.devices.keys())
        print(f"  Found {len(device_tags)} devices in parts list")
        return device_tags

    def identify_schematic_pages(self) -> List[int]:
        """Identify which pages are schematics (not cover, TOC, cable, etc.).

        Returns:
            List of page numbers (0-indexed) that contain schematics
        """
        print("\nClassifying pages...")
        schematic_pages = []

        for page_num in range(len(self.doc)):
            title = classify_page(self.doc[page_num])
            should_skip = should_skip_page_by_title(title)

            if not should_skip:
                schematic_pages.append(page_num)
                status = "SCHEMATIC"
            else:
                status = "SKIP"

            # Print first few and summary
            if page_num < 5 or page_num > len(self.doc) - 3:
                print(f"  Page {page_num:2d}: {status:10s} - {title}")
            elif page_num == 5:
                print(f"  ... (pages 5-{len(self.doc)-3} not shown)")

        print(f"\n  Total schematic pages: {len(schematic_pages)}")
        return schematic_pages

    def count_tags_on_page(
        self,
        page_num: int,
        device_tags: List[str]
    ) -> Dict[str, List[Tuple[float, float, float, float]]]:
        """Count occurrences of device tags on a specific page.

        Args:
            page_num: Page number (0-indexed)
            device_tags: List of device tags to search for

        Returns:
            Dictionary mapping device tags to list of bounding boxes
            Each bbox is (x0, y0, x1, y1) in PDF coordinates
        """
        page = self.doc[page_num]
        text_dict = page.get_text("dict")

        tag_matches = defaultdict(list)

        # Create set and variants for fast lookup
        tag_set = set(device_tags)
        tag_variants = {}
        for tag in device_tags:
            tag_variants[tag] = tag
            # Add version without prefix
            stripped = tag.lstrip("+-")
            if stripped != tag:
                tag_variants[stripped] = tag

        # Search all text on the page
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:  # Only text blocks
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    bbox = span.get("bbox", (0, 0, 0, 0))

                    # Check if this text matches any device tag
                    matched_tag = None

                    # Exact match
                    if text in tag_set:
                        matched_tag = text
                    # Check variants
                    elif text in tag_variants:
                        matched_tag = tag_variants[text]
                    # Check if text starts with a tag (e.g., "-K1:13" contains "-K1")
                    else:
                        for tag in tag_set:
                            if text.startswith(tag):
                                matched_tag = tag
                                break

                    if matched_tag:
                        tag_matches[matched_tag].append(bbox)

        return tag_matches

    def generate_report(self) -> Dict:
        """Generate comprehensive tag count report.

        Returns:
            Dictionary with complete analysis
        """
        print("\n" + "="*70)
        print("DEVICE TAG COUNTING REPORT")
        print("="*70)

        # Step 1: Extract parts list
        device_tags = self.extract_parts_list()

        # Step 2: Identify schematic pages
        schematic_pages = self.identify_schematic_pages()

        # Step 3: Count tags on each schematic page
        print("\nCounting tags on schematic pages...")
        tags_by_page = {}
        tags_with_counts = defaultdict(lambda: {"count": 0, "pages": [], "positions": []})
        total_occurrences = 0

        for page_num in schematic_pages:
            tag_matches = self.count_tags_on_page(page_num, device_tags)

            # Record tags found on this page
            page_tags = list(tag_matches.keys())
            tags_by_page[page_num] = page_tags

            # Update global counts
            for tag, bboxes in tag_matches.items():
                count = len(bboxes)
                tags_with_counts[tag]["count"] += count
                tags_with_counts[tag]["pages"].append(page_num)

                # Store positions for first few occurrences
                for bbox in bboxes[:5]:  # Limit to 5 per page
                    tags_with_counts[tag]["positions"].append({
                        "page": page_num,
                        "x0": bbox[0],
                        "y0": bbox[1],
                        "x1": bbox[2],
                        "y1": bbox[3],
                        "center_x": (bbox[0] + bbox[2]) / 2,
                        "center_y": (bbox[1] + bbox[3]) / 2,
                    })

                total_occurrences += count

            if len(tags_by_page) <= 5 or page_num == schematic_pages[-1]:
                print(f"  Page {page_num:2d}: {len(page_tags):2d} unique tags, "
                      f"{sum(len(tags_with_counts[t]['positions']) for t in page_tags):3d} total occurrences")

        # Step 4: Calculate statistics
        print(f"\n{'='*70}")
        print("SUMMARY STATISTICS")
        print(f"{'='*70}")
        print(f"Parts list count:           {len(device_tags)}")
        print(f"Schematic pages:            {len(schematic_pages)}")
        print(f"Total tag occurrences:      {total_occurrences}")
        print(f"Tags found at least once:   {len(tags_with_counts)}")
        print(f"Tags never found:           {len(device_tags) - len(tags_with_counts)}")

        # Find tags that appear on multiple pages
        multi_page_tags = {
            tag: data for tag, data in tags_with_counts.items()
            if len(set(data["pages"])) > 1
        }
        print(f"Tags on multiple pages:     {len(multi_page_tags)}")

        # Step 5: Build report structure
        report = {
            "pdf_file": str(self.pdf_path),
            "parts_list_count": len(device_tags),
            "parts_list": device_tags,
            "schematic_pages": schematic_pages,
            "total_tag_occurrences": total_occurrences,
            "unique_tags_found": len(tags_with_counts),
            "tags_never_found": sorted(set(device_tags) - set(tags_with_counts.keys())),
            "tags_by_page": {
                str(page): sorted(tags) for page, tags in tags_by_page.items()
            },
            "tags_with_counts": {
                tag: {
                    "count": data["count"],
                    "pages": sorted(set(data["pages"])),
                    "page_count": len(set(data["pages"])),
                    "positions": data["positions"][:10]  # Limit positions to first 10
                }
                for tag, data in sorted(tags_with_counts.items())
            },
            "expected_placements": total_occurrences,
            "multi_page_tags": {
                tag: {
                    "pages": sorted(set(data["pages"])),
                    "total_count": data["count"]
                }
                for tag, data in sorted(multi_page_tags.items())
            }
        }

        # Print sample of multi-page tags
        if multi_page_tags:
            print(f"\nSample multi-page tags:")
            for tag, data in sorted(multi_page_tags.items())[:5]:
                pages = sorted(set(data["pages"]))
                print(f"  {tag:10s}: appears on {len(pages)} pages {pages}")

        return report

    def create_visual_verification(
        self,
        report: Dict,
        output_dir: Path,
        max_pages: int = 3
    ):
        """Create visual verification images for first few schematic pages.

        Args:
            report: Report dictionary from generate_report()
            output_dir: Directory to save debug images
            max_pages: Maximum number of pages to visualize
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*70}")
        print(f"CREATING VISUAL VERIFICATION")
        print(f"{'='*70}")

        schematic_pages = report["schematic_pages"][:max_pages]
        tags_with_counts = report["tags_with_counts"]

        for page_num in schematic_pages:
            print(f"\nGenerating debug image for page {page_num}...")

            page = self.doc[page_num]

            # Render page at 2x resolution for clarity
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Convert to PIL Image for drawing
            from PIL import Image, ImageDraw, ImageFont
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            draw = ImageDraw.Draw(img)

            # Try to load a font, fall back to default if not available
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            except:
                font = ImageFont.load_default()

            # Draw bounding boxes for all tags on this page
            tags_on_page = 0
            for tag, data in tags_with_counts.items():
                for pos in data["positions"]:
                    if pos["page"] == page_num:
                        # Scale coordinates by zoom factor
                        x0 = pos["x0"] * zoom
                        y0 = pos["y0"] * zoom
                        x1 = pos["x1"] * zoom
                        y1 = pos["y1"] * zoom

                        # Draw green bounding box
                        draw.rectangle([x0, y0, x1, y1], outline="green", width=2)

                        # Draw tag label slightly above box
                        label_y = max(0, y0 - 15)
                        draw.text((x0, label_y), tag, fill="red", font=font)

                        tags_on_page += 1

            # Save image
            output_file = output_dir / f"tag_count_page_{page_num}.png"
            img.save(output_file)
            print(f"  Saved: {output_file}")
            print(f"  Tags highlighted: {tags_on_page}")

        print(f"\nVisual verification complete. Images saved to: {output_dir}")


def main():
    """Main entry point."""
    # Paths
    pdf_path = Path("/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf")
    report_path = Path("/home/liam-oreilly/claude.projects/electricalSchematics/TAG_COUNT_REPORT.json")
    debug_dir = Path("/home/liam-oreilly/claude.projects/electricalSchematics/tag_debug")

    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        return 1

    # Run analysis
    with DeviceTagCounter(pdf_path) as counter:
        # Generate report
        report = counter.generate_report()

        # Save report
        print(f"\n{'='*70}")
        print(f"SAVING REPORT")
        print(f"{'='*70}")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to: {report_path}")

        # Create visual verification
        counter.create_visual_verification(report, debug_dir, max_pages=3)

    print(f"\n{'='*70}")
    print("COMPLETE")
    print(f"{'='*70}")
    print(f"Report:  {report_path}")
    print(f"Images:  {debug_dir}/")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
