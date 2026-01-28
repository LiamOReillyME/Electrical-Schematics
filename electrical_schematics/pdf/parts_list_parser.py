"""Generic parts list parser for industrial electrical diagrams.

This parser can extract component information from parts lists in PDFs,
regardless of the specific format (DRAWER, EPLAN, AutoCAD Electrical, etc.).
"""

import fitz
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PartsListComponent:
    """Component information extracted from parts list."""

    designation: str  # e.g., K1, S1, M1
    quantity: int = 1
    description: str = ""
    manufacturer: str = ""
    part_number: str = ""
    voltage_rating: str = ""
    additional_info: Dict[str, str] = None

    def __post_init__(self):
        if self.additional_info is None:
            self.additional_info = {}


class PartsListParser:
    """Parser for extracting component information from PDF parts lists."""

    def __init__(self, pdf_path: Path):
        """Initialize parser.

        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = pdf_path
        self.doc = None

    def find_parts_list_pages(self) -> List[int]:
        """Find pages containing parts lists.

        Looks for pages with "Parts List" or "artikelstuckliste" markers
        in the upper left corner or bottom right of center.

        Returns:
            List of page numbers containing parts lists
        """
        self.doc = fitz.open(self.pdf_path)
        parts_pages = []

        markers = [
            "Parts List",
            "parts list",
            "PARTS LIST",
            "Parts list",  # Mixed case
            "artikelstuckliste",
            "Artikelstuckliste",
            "ARTIKELSTUCKLISTE",
            "artikelstückliste",  # With umlaut (lowercase)
            "Artikelstückliste",  # With umlaut (title case)
            "ARTIKELSTÜCKLISTE",  # With umlaut (uppercase)
            "Parts table",
            "Component list",
            "list of components",
            "Bill of materials",
            "BOM"
        ]

        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()

            # Check if any marker is present
            for marker in markers:
                if marker in text:
                    # Verify position - should be in upper left or bottom center
                    if self._is_marker_in_correct_position(page, marker):
                        parts_pages.append(page_num)
                        break

        return parts_pages

    def _is_marker_in_correct_position(self, page: fitz.Page, marker: str) -> bool:
        """Check if marker text is in expected position.

        Args:
            page: PDF page
            marker: Text marker to check

        Returns:
            True if marker is in upper left or bottom center area
        """
        # Get all text blocks with positions
        blocks = page.get_text("blocks")
        page_rect = page.rect

        for block in blocks:
            x0, y0, x1, y1, text, block_no, block_type = block

            if marker in text:
                # Upper left corner (top 20%, left 30%)
                if y0 < page_rect.height * 0.2 and x0 < page_rect.width * 0.3:
                    return True

                # Bottom center (bottom 20%, middle 60%)
                if (y0 > page_rect.height * 0.8 and
                    x0 > page_rect.width * 0.2 and
                    x1 < page_rect.width * 0.8):
                    return True

        return False

    def parse_parts_list(self) -> List[PartsListComponent]:
        """Parse all parts lists in the PDF.

        Returns:
            List of PartsListComponent objects
        """
        parts_pages = self.find_parts_list_pages()

        if not parts_pages:
            return []

        all_components = []

        for page_num in parts_pages:
            components = self._parse_parts_page(page_num)
            all_components.extend(components)

        if self.doc:
            self.doc.close()
            self.doc = None

        return all_components

    def _parse_parts_page(self, page_num: int) -> List[PartsListComponent]:
        """Parse a single parts list page.

        Args:
            page_num: Page number to parse

        Returns:
            List of components found on this page
        """
        page = self.doc[page_num]
        text = page.get_text()

        # Try different parsing strategies
        components = []

        # Strategy 1: Table-based extraction (most common)
        components = self._parse_table_format(page)

        if not components:
            # Strategy 2: Line-by-line text extraction
            components = self._parse_text_format(text)

        return components

    def _parse_table_format(self, page: fitz.Page) -> List[PartsListComponent]:
        """Parse parts list in table format.

        Args:
            page: PDF page

        Returns:
            List of components
        """
        components = []

        # Get text with bounding boxes
        blocks = page.get_text("dict")

        # Look for table structures
        # This is a simplified parser - real implementation would need
        # more sophisticated table detection

        text_lines = []
        for block in blocks.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    line_text = ""
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                    if line_text.strip():
                        text_lines.append(line_text.strip())

        # Parse lines looking for component patterns
        components = self._extract_components_from_lines(text_lines)

        return components

    def _parse_text_format(self, text: str) -> List[PartsListComponent]:
        """Parse parts list from plain text.

        Args:
            text: Page text

        Returns:
            List of components
        """
        lines = text.split('\n')
        return self._extract_components_from_lines(lines)

    def _extract_components_from_lines(self, lines: List[str]) -> List[PartsListComponent]:
        """Extract components from text lines.

        Args:
            lines: List of text lines

        Returns:
            List of components
        """
        components = []

        # Common designation patterns
        designation_patterns = [
            r'^([A-Z]+\d+)',  # K1, S1, M1, etc.
            r'^\s*([A-Z]+\d+)',  # With leading whitespace
            r'^([-+][A-Z]+\d+)',  # -K1, +S1 (DRAWER format)
            r'^([A-Z]+\d+[A-Z]?)',  # K1A, S1B, etc.
        ]

        # Voltage patterns
        voltage_patterns = [
            r'(\d+V(?:AC|DC)?)',
            r'(\d+\s*V\s*(?:AC|DC)?)',
        ]

        for line in lines:
            line = line.strip()

            if not line or len(line) < 2:
                continue

            # Try to match designation
            designation = None
            for pattern in designation_patterns:
                match = re.match(pattern, line)
                if match:
                    designation = match.group(1)
                    break

            if not designation:
                continue

            # Extract other information from the line
            description = ""
            manufacturer = ""
            part_number = ""
            voltage = ""
            quantity = 1

            # Remove designation from line to extract other info
            remainder = re.sub(r'^[-+]?[A-Z]+\d+[A-Z]?\s*', '', line)

            # Look for voltage
            for pattern in voltage_patterns:
                match = re.search(pattern, remainder)
                if match:
                    voltage = match.group(1).replace(' ', '')
                    break

            # Look for quantity (typically a number at start or in parens)
            qty_match = re.search(r'\((\d+)\)|^(\d+)\s+', remainder)
            if qty_match:
                quantity = int(qty_match.group(1) or qty_match.group(2))

            # Rest is description (simplified - real parser would be more sophisticated)
            # Remove voltage and quantity from description
            description = remainder
            for pattern in voltage_patterns:
                description = re.sub(pattern, '', description)
            description = re.sub(r'\(\d+\)', '', description)
            description = description.strip()

            # Create component
            component = PartsListComponent(
                designation=designation,
                quantity=quantity,
                description=description[:100] if description else "",  # Limit length
                voltage_rating=voltage,
                manufacturer=manufacturer,
                part_number=part_number
            )

            components.append(component)

        return components

    def close(self):
        """Close the PDF document."""
        if self.doc:
            self.doc.close()
            self.doc = None
