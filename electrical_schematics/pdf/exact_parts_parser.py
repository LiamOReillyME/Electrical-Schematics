"""Parts list parser using exact column coordinates."""

import fitz
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from .language_filter import filter_german_from_text


@dataclass
class PartData:
    """Part information extracted from parts list."""
    device_tag: str  # e.g., -A1, -A2
    designation: str  # Description
    technical_data: str  # Technical specifications
    type_designation: str  # Part number


def find_parts_list_pages(pdf_path: Path) -> List[int]:
    """Find all pages containing parts lists.

    Looks for "Parts list" marker anywhere on the page.
    Parts list pages typically have the marker and contain device tags
    starting with - or +.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of page numbers (0-indexed) containing parts lists, sorted by page number
    """
    doc = fitz.open(pdf_path)

    markers = [
        "Parts list",
        "parts list",
        "Artikelstückliste",
        "Artikelstuckliste",
    ]

    # Track pages with markers and count of device tags
    candidate_pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        # Check for parts list marker
        has_marker = any(marker in text for marker in markers)

        if not has_marker:
            continue

        # Count device tags (designations like -A1, -B2, +X1)
        # Parts list pages have many such designations
        text_dict = page.get_text("dict")
        device_tag_count = 0

        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text_item = span.get("text", "").strip()
                        # Check if it looks like a device tag
                        if text_item.startswith('-') or text_item.startswith('+'):
                            if len(text_item) >= 2 and text_item[1:2].isalpha():
                                device_tag_count += 1

        if device_tag_count >= 3:  # Lower threshold to catch pages with fewer components
            candidate_pages.append((page_num, device_tag_count))

    doc.close()

    if not candidate_pages:
        return []

    # Return all pages sorted by page number (not by count)
    candidate_pages.sort(key=lambda x: x[0])
    return [page_num for page_num, _ in candidate_pages]


def find_parts_list_page(pdf_path: Path) -> Optional[int]:
    """Find the first page containing a parts list.

    Backward compatibility wrapper for find_parts_list_pages().

    Args:
        pdf_path: Path to PDF file

    Returns:
        Page number (0-indexed) or None
    """
    pages = find_parts_list_pages(pdf_path)
    return pages[0] if pages else None


def parse_parts_list(pdf_path: Path) -> List[PartData]:
    """Parse parts list from all parts list pages.

    Scans for all parts list pages and combines results.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of part data from all parts list pages
    """
    # Find ALL parts list pages
    page_nums = find_parts_list_pages(pdf_path)
    if not page_nums:
        return []

    doc = fitz.open(pdf_path)
    all_parts = []

    for page_num in page_nums:
        page_parts = _parse_single_parts_page(doc, page_num)
        all_parts.extend(page_parts)

    doc.close()
    return all_parts


def _parse_single_parts_page(doc: fitz.Document, page_num: int) -> List[PartData]:
    """Parse a single parts list page.

    Column definitions:
    - Device tag: X35 to X190
    - Designation: X190 to X375
    - Technical Data: X375 to X615
    - Type designation: X615 to X840

    Args:
        doc: Open PDF document
        page_num: Page number to parse

    Returns:
        List of part data from this page
    """
    page = doc[page_num]

    # Column boundaries (adjusted based on actual header positions)
    COL_DEVICE_TAG = (35, 190)      # Device tag column
    COL_DESIGNATION = (190, 375)    # Designation/description column
    COL_TECH_DATA = (375, 615)      # Technical data column
    COL_TYPE_DESIGNATION = (615, 840)  # Type designation/part number column
    ROW_START = 80  # Start after header rows
    ROW_END = 750   # End of data region

    # Collect all text items with positions
    text_items = []
    text_dict = page.get_text("dict")

    for block in text_dict.get("blocks", []):
        if block.get("type") == 0:  # Text block
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue

                    bbox = span.get("bbox", [0, 0, 0, 0])
                    x = bbox[0]
                    y = bbox[1]

                    # Only consider items in the data region
                    if y >= ROW_START and y <= ROW_END:
                        text_items.append({
                            'text': text,
                            'x': x,
                            'y': y
                        })

    # Group items by row (y-position)
    # Use 5px grouping tolerance for tighter row detection
    rows = {}
    for item in text_items:
        y_key = round(item['y'] / 5) * 5  # Group by ~5px rows
        if y_key not in rows:
            rows[y_key] = []
        rows[y_key].append(item)

    # Extract parts from each row
    # New approach: collect all data first, then look backwards when we find device tags
    parts = []
    sorted_y_keys = sorted(rows.keys())

    # Build index of row data
    row_data = {}
    for y in sorted_y_keys:
        row_items = rows[y]

        device_tags = []
        designations = []
        tech_data = []
        type_desigs = []

        for item in row_items:
            x = item['x']
            text = item['text']

            if COL_DEVICE_TAG[0] <= x < COL_DEVICE_TAG[1]:
                if text.startswith('-') or text.startswith('+'):
                    device_tags.append(text)
            elif COL_DESIGNATION[0] <= x < COL_DESIGNATION[1]:
                designations.append(text)
            elif COL_TECH_DATA[0] <= x < COL_TECH_DATA[1]:
                tech_data.append(text)
            elif COL_TYPE_DESIGNATION[0] <= x < COL_TYPE_DESIGNATION[1]:
                type_desigs.append(text)

        row_data[y] = {
            'device_tags': device_tags,
            'designations': designations,
            'tech_data': tech_data,
            'type_desigs': type_desigs
        }

    # Process rows: when we find a device tag, look backwards for English designation
    for i, y in enumerate(sorted_y_keys):
        data = row_data[y]

        if not data['device_tags']:
            continue

        device_tag = data['device_tags'][0]

        # Collect designation from previous row (English) and current row (German)
        designation_parts = []

        # Previous row (typically contains English)
        # Only look at previous row if it's very close (within 15px, about 1 text line)
        if i > 0:
            prev_y = sorted_y_keys[i - 1]
            prev_data = row_data[prev_y]
            # Only add if:
            # 1. Previous row doesn't have its own device tag
            # 2. Previous row is within 15px (about 1 line height)
            if not prev_data['device_tags'] and (y - prev_y) <= 15:
                designation_parts.extend(prev_data['designations'])

        # Current row (typically contains German)
        designation_parts.extend(data['designations'])

        # Next row (sometimes continuation)
        # Only look at next row if it's very close (within 15px)
        if i + 1 < len(sorted_y_keys):
            next_y = sorted_y_keys[i + 1]
            next_data = row_data[next_y]
            # Only add if:
            # 1. Next row doesn't have its own device tag
            # 2. Next row is within 15px
            if not next_data['device_tags'] and (next_y - y) <= 15:
                designation_parts.extend(next_data['designations'])

        # Tech data and type designation from current row
        tech_parts = data['tech_data']
        type_parts = data['type_desigs']

        # Create part (filter out German text from designation)
        part = PartData(
            device_tag=device_tag,
            designation=filter_german_from_text(" ".join(designation_parts)),
            technical_data=" ".join(tech_parts),
            type_designation=" ".join(type_parts)
        )
        parts.append(part)

    return parts
