"""OCR-based parts list extractor using Tesseract.

This module provides OCR extraction for parts lists in PDFs,
particularly useful for scanned or image-based documents where
standard text extraction fails.
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple, Callable
from dataclasses import dataclass

from .language_filter import is_likely_german_line, select_english_from_alternates

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

import fitz  # PyMuPDF


# Pattern to match internal E-codes (inventory codes, not manufacturer part numbers)
# Examples: E160970, E65138, E89520
INTERNAL_CODE_PATTERN = re.compile(r'^E\d{4,}$', re.IGNORECASE)

# Known manufacturer part number patterns
# These help identify valid part numbers among multiple items in a cell
MANUFACTURER_PATTERNS = [
    # Allen-Bradley / Rockwell: 1492-SP1B060, 1492-SPM1C100
    re.compile(r'\d{3,4}-[A-Z]{2,}[A-Z0-9]+'),
    # Siemens: 3RT2026-1DB40-1AAO, 6ES7-511-1AK02, 5SY6210-7
    re.compile(r'\d[A-Z]{1,2}\d+[-/][A-Z0-9\-]+'),
    # Omron: G2R-1-SN, G7SA-3A1B
    re.compile(r'G\d[A-Z]{1,2}-[A-Z0-9\-]+'),
    # Phoenix Contact: TRIO-PS/1AC/24DC/5
    re.compile(r'[A-Z]{3,}-[A-Z]+/[A-Z0-9/]+'),
    # Generic: alphanumeric with hyphens/slashes (common format)
    re.compile(r'[A-Z]{2,}[0-9]+[-/][A-Z0-9\-/]+'),
    # Schneider Electric: LC1D09, LC1D25
    re.compile(r'LC\d[A-Z]\d+'),
]


@dataclass
class OCRPartData:
    """Part information extracted via OCR from parts list."""
    device_tag: str  # e.g., -A1, -K1, +DG-M1
    designation: str  # Description text
    technical_data: str  # Technical specifications
    type_designation: str  # Part number (for DigiKey lookup)
    page_number: int  # Source page
    confidence: float = 0.0  # OCR confidence score (0-100)

    def __repr__(self) -> str:
        return f"OCRPartData({self.device_tag}, type={self.type_designation})"


def is_internal_code(text: str) -> bool:
    """Check if a string is an internal inventory code (E-code).

    Internal codes follow the pattern E followed by 4+ digits.
    Examples: E160970, E65138, E89520

    Args:
        text: String to check

    Returns:
        True if it matches the internal code pattern
    """
    return bool(INTERNAL_CODE_PATTERN.match(text.strip()))


def extract_manufacturer_part_number(raw_text: str) -> str:
    """Extract manufacturer part number from raw text, filtering out internal codes.

    When a cell contains multiple items (e.g., "E65138 1492-SPM1C100"),
    this function extracts only the manufacturer part number.

    Args:
        raw_text: Raw text from type designation column

    Returns:
        Cleaned manufacturer part number, or empty string if none found
    """
    if not raw_text:
        return ""

    # Split by whitespace to handle multiple items in one cell
    tokens = raw_text.split()

    # Filter out internal codes
    valid_tokens = [t for t in tokens if not is_internal_code(t)]

    if not valid_tokens:
        return ""

    # If only one token remains after filtering, use it
    if len(valid_tokens) == 1:
        return valid_tokens[0]

    # Multiple tokens remain - try to find the best manufacturer part number
    for pattern in MANUFACTURER_PATTERNS:
        for token in valid_tokens:
            if pattern.match(token):
                return token

    # No pattern matched - return the longest non-E-code token
    # (manufacturer part numbers tend to be longer than generic codes)
    return max(valid_tokens, key=len)


class OCRPartsExtractor:
    """Extract parts data from PDF using Tesseract OCR.

    This extractor handles both vector PDFs (using PyMuPDF text extraction)
    and scanned/image PDFs (using Tesseract OCR). It automatically detects
    which method to use based on text extraction success.
    """

    # Column boundaries for parts list table (in points, ~72 DPI)
    # These match the existing exact_parts_parser.py boundaries
    COL_DEVICE_TAG = (35, 190)
    COL_DESIGNATION = (190, 375)
    COL_TECH_DATA = (375, 615)
    COL_TYPE_DESIGNATION = (615, 840)
    ROW_START = 80
    ROW_END = 750

    # Parts list page markers
    PAGE_MARKERS = [
        "Parts list",
        "parts list",
        "Artikelstückliste",
        "Artikelstuckliste",
        "PARTS LIST",
        "Bill of Materials",
        "BOM",
    ]

    def __init__(self, pdf_path: Path, tesseract_cmd: Optional[str] = None):
        """Initialize OCR parts extractor.

        Args:
            pdf_path: Path to PDF file
            tesseract_cmd: Optional path to tesseract executable
        """
        self.pdf_path = Path(pdf_path)
        self.doc: Optional[fitz.Document] = None

        if tesseract_cmd and TESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def check_dependencies(self) -> Tuple[bool, str]:
        """Check if required dependencies are available.

        Returns:
            Tuple of (success, error_message)
        """
        if not TESSERACT_AVAILABLE:
            return False, "pytesseract not installed. Run: pip install pytesseract"

        if not PDF2IMAGE_AVAILABLE:
            return False, "pdf2image not installed. Run: pip install pdf2image"

        # Check if tesseract binary is available
        try:
            pytesseract.get_tesseract_version()
        except pytesseract.TesseractNotFoundError:
            return False, (
                "Tesseract OCR not found. Install it:\n"
                "  Ubuntu/Debian: sudo apt install tesseract-ocr\n"
                "  macOS: brew install tesseract\n"
                "  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki"
            )

        return True, ""

    def find_parts_list_pages(self) -> List[int]:
        """Find pages containing parts lists.

        Returns:
            List of page numbers (0-indexed) containing parts lists
        """
        self.doc = fitz.open(self.pdf_path)
        parts_pages = []

        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()

            # Check for parts list marker
            has_marker = any(marker in text for marker in self.PAGE_MARKERS)
            if not has_marker:
                continue

            # Count device tags to confirm it's a parts list page
            device_tag_count = self._count_device_tags(page)
            if device_tag_count >= 3:
                parts_pages.append(page_num)

        return sorted(parts_pages)

    def _count_device_tags(self, page: fitz.Page) -> int:
        """Count device tags on a page to verify it's a parts list."""
        text_dict = page.get_text("dict")
        count = 0

        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text.startswith('-') or text.startswith('+'):
                            if len(text) >= 2 and text[1:2].isalpha():
                                count += 1
        return count

    def extract_parts(
        self,
        page_numbers: Optional[List[int]] = None,
        use_ocr: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[OCRPartData]:
        """Extract parts from PDF pages.

        Args:
            page_numbers: Specific pages to process (None = auto-detect)
            use_ocr: Whether to use OCR for image-based extraction
            progress_callback: Optional callback(current, total, message)

        Returns:
            List of extracted part data
        """
        if page_numbers is None:
            page_numbers = self.find_parts_list_pages()

        if not page_numbers:
            return []

        all_parts = []
        total_pages = len(page_numbers)

        for idx, page_num in enumerate(page_numbers):
            if progress_callback:
                progress_callback(idx + 1, total_pages, f"Processing page {page_num + 1}")

            # First try PyMuPDF text extraction (faster, for vector PDFs)
            parts = self._extract_from_text(page_num)

            # If text extraction yields few results and OCR is enabled, try OCR
            if len(parts) < 3 and use_ocr:
                deps_ok, error = self.check_dependencies()
                if deps_ok:
                    if progress_callback:
                        progress_callback(idx + 1, total_pages, f"OCR processing page {page_num + 1}")
                    ocr_parts = self._extract_from_ocr(page_num)
                    if len(ocr_parts) > len(parts):
                        parts = ocr_parts

            all_parts.extend(parts)

        self._close()
        return all_parts

    def _extract_from_text(self, page_num: int) -> List[OCRPartData]:
        """Extract parts using PyMuPDF text extraction."""
        if self.doc is None:
            self.doc = fitz.open(self.pdf_path)

        page = self.doc[page_num]
        text_dict = page.get_text("dict")

        # Collect text items with positions
        text_items = []
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        bbox = span.get("bbox", [0, 0, 0, 0])
                        x, y = bbox[0], bbox[1]
                        if self.ROW_START <= y <= self.ROW_END:
                            text_items.append({'text': text, 'x': x, 'y': y})

        return self._parse_text_items(text_items, page_num)

    def _extract_from_ocr(self, page_num: int) -> List[OCRPartData]:
        """Extract parts using Tesseract OCR."""
        if not TESSERACT_AVAILABLE or not PDF2IMAGE_AVAILABLE:
            return []

        # Convert page to image
        images = convert_from_path(
            str(self.pdf_path),
            first_page=page_num + 1,
            last_page=page_num + 1,
            dpi=300
        )

        if not images:
            return []

        image = images[0]

        # Run OCR with detailed output
        ocr_data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            config='--psm 6'  # Assume uniform block of text
        )

        # Convert OCR output to text items with positions
        # Scale coordinates from 300 DPI image to PDF points (72 DPI)
        scale = 72.0 / 300.0
        text_items = []

        for i in range(len(ocr_data['text'])):
            text = ocr_data['text'][i].strip()
            if not text:
                continue

            x = ocr_data['left'][i] * scale
            y = ocr_data['top'][i] * scale
            conf = float(ocr_data['conf'][i])

            if self.ROW_START <= y <= self.ROW_END and conf > 30:
                text_items.append({
                    'text': text,
                    'x': x,
                    'y': y,
                    'confidence': conf
                })

        return self._parse_text_items(text_items, page_num)

    def _parse_text_items(
        self,
        text_items: List[dict],
        page_num: int
    ) -> List[OCRPartData]:
        """Parse text items into structured part data.

        Groups items by row and extracts data from each column.

        IMPORTANT: In DRAWER PDFs, the designation/tech/type appear on the line
        BEFORE the device tag, not after. So we look backwards.
        """
        # Group items by row (y-position)
        rows = {}
        for item in text_items:
            y_key = round(item['y'] / 10) * 10
            if y_key not in rows:
                rows[y_key] = []
            rows[y_key].append(item)

        # Extract parts from rows
        parts = []
        sorted_y_keys = sorted(rows.keys())

        for i, y in enumerate(sorted_y_keys):
            row_items = rows[y]

            # Categorize items by column
            device_tags = []
            for item in row_items:
                x = item['x']
                text = item['text']

                if self.COL_DEVICE_TAG[0] <= x < self.COL_DEVICE_TAG[1]:
                    if text.startswith('-') or text.startswith('+'):
                        device_tags.append(text)

            # New device tag starts a new part
            if device_tags:
                # Look backward (previous row, y - ~10) for designation/tech/type
                # But ONLY if previous row doesn't have its own device tag
                prev_y = sorted_y_keys[i - 1] if i > 0 else None
                prev_row = rows[prev_y] if prev_y else []

                # Check if previous row has its own device tag
                prev_has_device_tag = False
                if prev_row:
                    for item in prev_row:
                        x = item['x']
                        text = item['text']
                        if (self.COL_DEVICE_TAG[0] <= x < self.COL_DEVICE_TAG[1] and
                            (text.startswith('-') or text.startswith('+'))):
                            prev_has_device_tag = True
                            break

                # Also check current row for any data
                curr_designations = []
                curr_tech_data = []
                curr_type_desigs = []
                prev_designations = []
                prev_tech_data = []
                prev_type_desigs = []
                confidences = []

                # Extract from current row
                for item in row_items:
                    x = item['x']
                    text = item['text']
                    conf = item.get('confidence', 100.0)
                    confidences.append(conf)

                    if self.COL_DESIGNATION[0] <= x < self.COL_DESIGNATION[1]:
                        if not is_likely_german_line(text):
                            curr_designations.append(text)
                    elif self.COL_TECH_DATA[0] <= x < self.COL_TECH_DATA[1]:
                        curr_tech_data.append(text)
                    elif self.COL_TYPE_DESIGNATION[0] <= x < self.COL_TYPE_DESIGNATION[1]:
                        curr_type_desigs.append(text)

                # Extract from previous row (typical pattern) - but only if prev row
                # doesn't have its own device tag
                if not prev_has_device_tag:
                    for item in prev_row:
                        x = item['x']
                        text = item['text']
                        conf = item.get('confidence', 100.0)
                        confidences.append(conf)

                        if self.COL_DESIGNATION[0] <= x < self.COL_DESIGNATION[1]:
                            if not is_likely_german_line(text):
                                prev_designations.append(text)
                        elif self.COL_TECH_DATA[0] <= x < self.COL_TECH_DATA[1]:
                            prev_tech_data.append(text)
                        elif self.COL_TYPE_DESIGNATION[0] <= x < self.COL_TYPE_DESIGNATION[1]:
                            prev_type_desigs.append(text)

                # Also check next row for continuation
                next_y = sorted_y_keys[i + 1] if i + 1 < len(sorted_y_keys) else None
                next_row = rows[next_y] if next_y else []
                next_designations = []
                next_tech_data = []
                next_type_desigs = []

                for item in next_row:
                    x = item['x']
                    text = item['text']
                    conf = item.get('confidence', 100.0)
                    confidences.append(conf)

                    if self.COL_DESIGNATION[0] <= x < self.COL_DESIGNATION[1]:
                        if not is_likely_german_line(text):
                            next_designations.append(text)
                    elif self.COL_TECH_DATA[0] <= x < self.COL_TECH_DATA[1]:
                        next_tech_data.append(text)
                    elif self.COL_TYPE_DESIGNATION[0] <= x < self.COL_TYPE_DESIGNATION[1]:
                        next_type_desigs.append(text)

                # Combine data - use smart fallback logic
                # Typical pattern: designation/tech/type are in previous row
                # But sometimes they span current or next row
                # Priority: previous > current > next, but collect all non-empty data
                all_designations = prev_designations or curr_designations or next_designations
                all_tech_data = prev_tech_data or curr_tech_data or next_tech_data
                all_type_desigs = prev_type_desigs or curr_type_desigs or next_type_desigs

                avg_conf = sum(confidences) / len(confidences) if confidences else 0
                part = OCRPartData(
                    device_tag=device_tags[0],
                    designation=" ".join(all_designations),
                    technical_data=" ".join(all_tech_data),
                    type_designation=" ".join(all_type_desigs),
                    page_number=page_num,
                    confidence=avg_conf
                )
                parts.append(part)

        # Clean up extracted data
        for part in parts:
            part.designation = self._clean_text(part.designation)
            part.technical_data = self._clean_text(part.technical_data)
            part.type_designation = self._clean_part_number(part.type_designation)

        return parts

    def _clean_text(self, text: str) -> str:
        """Clean up extracted text."""
        # Remove extra whitespace
        text = " ".join(text.split())
        # Remove common OCR artifacts
        text = text.replace("|", "").replace("\\", "")

        # Remove duplicate words (e.g., "Circuit breaker Circuit breaker" -> "Circuit breaker")
        words = text.split()
        cleaned_words = []
        prev_word = None
        for word in words:
            # Skip if same as previous word (case-insensitive)
            if word.lower() != (prev_word.lower() if prev_word else None):
                cleaned_words.append(word)
            prev_word = word

        return " ".join(cleaned_words).strip()

    def _clean_part_number(self, part_number: str) -> str:
        """Clean up and validate part number, filtering out internal codes.

        This method:
        1. Removes OCR artifacts and whitespace
        2. Filters out internal E-codes (e.g., E160970, E65138)
        3. Extracts manufacturer part numbers when multiple items are present

        Args:
            part_number: Raw part number text from OCR

        Returns:
            Cleaned manufacturer part number, or empty string if none found
        """
        part_number = self._clean_text(part_number)

        # Remove common non-part-number prefixes/suffixes
        part_number = re.sub(r'^[^A-Za-z0-9]+', '', part_number)
        part_number = re.sub(r'[^A-Za-z0-9\-/]+$', '', part_number)

        # Extract manufacturer part number, filtering out internal codes
        part_number = extract_manufacturer_part_number(part_number)

        return part_number

    def _close(self) -> None:
        """Close the PDF document."""
        if self.doc:
            self.doc.close()
            self.doc = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close()
        return False


def extract_parts_with_ocr(
    pdf_path: Path,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> List[OCRPartData]:
    """Convenience function to extract parts from a PDF.

    Args:
        pdf_path: Path to PDF file
        progress_callback: Optional progress callback

    Returns:
        List of extracted part data
    """
    with OCRPartsExtractor(pdf_path) as extractor:
        return extractor.extract_parts(progress_callback=progress_callback)
