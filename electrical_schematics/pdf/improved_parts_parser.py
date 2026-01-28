"""Improved parts list parser with column-based extraction."""

import fitz
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class ParsedComponent:
    """Component parsed from parts list."""
    designation: str
    description: str = ""
    technical_data: str = ""
    part_number: str = ""
    manufacturer: str = ""
    page_ref: str = ""


def parse_parts_list_columns(pdf_path: Path) -> List[ParsedComponent]:
    """Parse parts list using column-based extraction.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of parsed components
    """
    doc = fitz.open(pdf_path)
    components = []

    # Find parts list page
    parts_page_num = None
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        if 'Parts list' in text or 'Artikelstückliste' in text:
            parts_page_num = page_num
            break

    if parts_page_num is None:
        doc.close()
        return []

    page = doc[parts_page_num]
    text_dict = page.get_text("dict")

    # Collect all text with positions
    text_items = []
    for block in text_dict.get("blocks", []):
        if block.get("type") == 0:  # Text block
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    bbox = span.get("bbox", [0, 0, 0, 0])
                    text_items.append({
                        'text': text,
                        'x': bbox[0],
                        'y': bbox[1]
                    })

    # Define column boundaries based on typical DRAWER format
    # These are approximate x-positions
    COL_DEVICE_TAG = (30, 170)      # Device tag (e.g., -A1, -A2)
    COL_PAGE_REF = (110, 170)       # Page reference
    COL_DESIGNATION = (180, 400)    # Description/designation
    COL_TECH_DATA = (370, 650)      # Technical data (voltage, size, etc.)
    COL_PART_NUM = (600, 900)       # Part number
    COL_MANUFACTURER = (830, 1100)  # Manufacturer

    # Group text by rows (y-position)
    rows = {}
    for item in text_items:
        y = round(item['y'] / 5) * 5  # Group by ~5px rows
        if y not in rows:
            rows[y] = []
        rows[y].append(item)

    # Skip header rows (first ~280 pixels typically headers)
    data_rows = {y: items for y, items in rows.items() if y > 280}

    # Process each row
    for y in sorted(data_rows.keys()):
        row_items = data_rows[y]

        # Extract data from columns
        designation = ""
        page_ref = ""
        description = ""
        tech_data = ""
        part_number = ""
        manufacturer = ""

        for item in row_items:
            x = item['x']
            text = item['text']

            # Device tag (designation like -A1, -A2)
            if COL_DEVICE_TAG[0] <= x < COL_DEVICE_TAG[1]:
                if text.startswith('-') or text.startswith('+'):
                    designation = text
                elif len(text) <= 5 and not designation:  # Page ref like "12 0"
                    page_ref = text

            # Designation/Description
            elif COL_DESIGNATION[0] <= x < COL_DESIGNATION[1]:
                description += " " + text

            # Technical data
            elif COL_TECH_DATA[0] <= x < COL_TECH_DATA[1]:
                tech_data += " " + text

            # Part number
            elif COL_PART_NUM[0] <= x < COL_PART_NUM[1]:
                # Part numbers are usually numeric
                if text.replace('-', '').replace('.', '').isdigit():
                    part_number = text
                elif not part_number:
                    part_number = text

            # Manufacturer
            elif COL_MANUFACTURER[0] <= x < COL_MANUFACTURER[1]:
                manufacturer += " " + text

        # Only add if we have a valid designation
        if designation:
            component = ParsedComponent(
                designation=designation.strip(),
                description=description.strip(),
                technical_data=tech_data.strip(),
                part_number=part_number.strip(),
                manufacturer=manufacturer.strip(),
                page_ref=page_ref.strip()
            )
            components.append(component)

    doc.close()

    # Remove duplicates (same designation)
    seen = set()
    unique_components = []
    for comp in components:
        if comp.designation not in seen:
            seen.add(comp.designation)
            unique_components.append(comp)

    return unique_components
