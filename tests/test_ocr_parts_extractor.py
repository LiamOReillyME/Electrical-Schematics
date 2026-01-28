"""Tests for OCR parts extractor."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from electrical_schematics.pdf.ocr_parts_extractor import (
    OCRPartsExtractor,
    OCRPartData,
    extract_parts_with_ocr,
    is_internal_code,
    extract_manufacturer_part_number,
    TESSERACT_AVAILABLE,
    PDF2IMAGE_AVAILABLE
)


class TestOCRPartData:
    """Tests for OCRPartData dataclass."""

    def test_creation(self) -> None:
        """Test creating OCRPartData."""
        part = OCRPartData(
            device_tag="-K1",
            designation="Relay",
            technical_data="24VDC coil",
            type_designation="G2R-1-SN",
            page_number=5,
            confidence=95.5
        )
        assert part.device_tag == "-K1"
        assert part.designation == "Relay"
        assert part.type_designation == "G2R-1-SN"
        assert part.page_number == 5
        assert part.confidence == 95.5

    def test_repr(self) -> None:
        """Test string representation."""
        part = OCRPartData(
            device_tag="-K1",
            designation="Relay",
            technical_data="",
            type_designation="G2R-1-SN",
            page_number=0
        )
        assert "OCRPartData(-K1" in repr(part)
        assert "G2R-1-SN" in repr(part)

    def test_default_confidence(self) -> None:
        """Test default confidence value."""
        part = OCRPartData(
            device_tag="-A1",
            designation="PLC",
            technical_data="",
            type_designation="6ES7-511",
            page_number=0
        )
        assert part.confidence == 0.0


class TestInternalCodeDetection:
    """Tests for internal E-code detection."""

    def test_detects_internal_codes(self) -> None:
        """Test that internal E-codes are correctly identified."""
        # These are internal inventory codes that should be filtered
        assert is_internal_code("E160970") is True
        assert is_internal_code("E65138") is True
        assert is_internal_code("E89520") is True
        assert is_internal_code("E12345") is True
        assert is_internal_code("E1234567890") is True

    def test_case_insensitive(self) -> None:
        """Test that E-code detection is case insensitive."""
        assert is_internal_code("e160970") is True
        assert is_internal_code("E160970") is True

    def test_allows_manufacturer_part_numbers(self) -> None:
        """Test that valid manufacturer part numbers are not filtered."""
        # Allen-Bradley
        assert is_internal_code("1492-SP1B060") is False
        assert is_internal_code("1492-SPM1C100") is False
        # Siemens
        assert is_internal_code("3RT2026-1DB40-1AAO") is False
        assert is_internal_code("6ES7-511-1AK02") is False
        assert is_internal_code("5SY6210-7") is False
        # Omron
        assert is_internal_code("G2R-1-SN") is False
        assert is_internal_code("G7SA-3A1B") is False
        # Phoenix Contact
        assert is_internal_code("TRIO-PS/1AC/24DC/5") is False
        # Schneider
        assert is_internal_code("LC1D09") is False

    def test_short_e_codes_not_filtered(self) -> None:
        """Test that short E-codes (less than 4 digits) are not filtered.

        These might be legitimate part numbers starting with E.
        """
        assert is_internal_code("E123") is False
        assert is_internal_code("E12") is False
        assert is_internal_code("E1") is False

    def test_e_codes_with_letters_not_filtered(self) -> None:
        """Test that codes with letters after E are not filtered."""
        assert is_internal_code("EA1234") is False
        assert is_internal_code("E1234A") is False
        assert is_internal_code("E-1234") is False

    def test_whitespace_handling(self) -> None:
        """Test that whitespace is handled correctly."""
        assert is_internal_code("  E160970  ") is True
        assert is_internal_code("E160970 ") is True


class TestManufacturerPartExtraction:
    """Tests for extracting manufacturer part numbers from mixed text."""

    def test_extracts_from_mixed_text(self) -> None:
        """Test extracting manufacturer PN when mixed with internal code."""
        # Internal code first
        assert extract_manufacturer_part_number("E65138 1492-SPM1C100") == "1492-SPM1C100"
        # Internal code last
        assert extract_manufacturer_part_number("1492-SP1B060 E160970") == "1492-SP1B060"
        # Multiple internal codes
        assert extract_manufacturer_part_number("E65138 3RT2026-1DB40-1AAO E89520") == "3RT2026-1DB40-1AAO"

    def test_single_manufacturer_part(self) -> None:
        """Test with single manufacturer part number (no internal code)."""
        assert extract_manufacturer_part_number("G2R-1-SN") == "G2R-1-SN"
        assert extract_manufacturer_part_number("TRIO-PS/1AC/24DC/5") == "TRIO-PS/1AC/24DC/5"
        assert extract_manufacturer_part_number("LC1D09") == "LC1D09"

    def test_only_internal_code_returns_empty(self) -> None:
        """Test that only internal codes returns empty string."""
        assert extract_manufacturer_part_number("E160970") == ""
        assert extract_manufacturer_part_number("E65138 E89520") == ""

    def test_empty_input(self) -> None:
        """Test with empty input."""
        assert extract_manufacturer_part_number("") == ""
        assert extract_manufacturer_part_number("   ") == ""

    def test_known_manufacturer_patterns(self) -> None:
        """Test extraction of known manufacturer patterns."""
        # Allen-Bradley
        assert extract_manufacturer_part_number("E12345 1492-SP1B060") == "1492-SP1B060"
        # Siemens
        assert extract_manufacturer_part_number("E12345 6ES7-511-1AK02") == "6ES7-511-1AK02"
        # Omron
        assert extract_manufacturer_part_number("E12345 G7SA-3A1B") == "G7SA-3A1B"
        # Phoenix Contact
        assert extract_manufacturer_part_number("E12345 TRIO-PS/1AC/24DC/5") == "TRIO-PS/1AC/24DC/5"

    def test_multiple_valid_parts_returns_first_match(self) -> None:
        """Test with multiple valid parts - should return pattern-matched one."""
        # When multiple valid tokens exist, pattern matching takes priority
        result = extract_manufacturer_part_number("ABC123 1492-SPM1C100")
        # Should prefer the Allen-Bradley pattern match
        assert result == "1492-SPM1C100"

    def test_fallback_to_longest_token(self) -> None:
        """Test fallback to longest token when no patterns match."""
        # Two tokens, neither matches manufacturer patterns
        result = extract_manufacturer_part_number("SHORT VERYLONGPART")
        assert result == "VERYLONGPART"


class TestOCRPartsExtractor:
    """Tests for OCRPartsExtractor class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test extractor initialization."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()

        extractor = OCRPartsExtractor(pdf_path)
        assert extractor.pdf_path == pdf_path
        assert extractor.doc is None

    def test_check_dependencies_missing_tesseract(self) -> None:
        """Test dependency check when pytesseract is missing."""
        with patch('electrical_schematics.pdf.ocr_parts_extractor.TESSERACT_AVAILABLE', False):
            extractor = OCRPartsExtractor(Path("test.pdf"))
            ok, error = extractor.check_dependencies()
            assert not ok
            assert "pytesseract" in error

    def test_check_dependencies_missing_pdf2image(self) -> None:
        """Test dependency check when pdf2image is missing."""
        with patch('electrical_schematics.pdf.ocr_parts_extractor.TESSERACT_AVAILABLE', True):
            with patch('electrical_schematics.pdf.ocr_parts_extractor.PDF2IMAGE_AVAILABLE', False):
                extractor = OCRPartsExtractor(Path("test.pdf"))
                ok, error = extractor.check_dependencies()
                assert not ok
                assert "pdf2image" in error

    def test_clean_text(self) -> None:
        """Test text cleaning."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        assert extractor._clean_text("  hello  world  ") == "hello world"
        assert extractor._clean_text("test|text") == "testtext"
        assert extractor._clean_text("back\\slash") == "backslash"

    def test_clean_part_number(self) -> None:
        """Test part number cleaning."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        assert extractor._clean_part_number("  G2R-1-SN  ") == "G2R-1-SN"
        assert extractor._clean_part_number("...ABC123...") == "ABC123"
        assert extractor._clean_part_number("XYZ-100/200") == "XYZ-100/200"

    def test_clean_part_number_filters_internal_codes(self) -> None:
        """Test that _clean_part_number filters out internal E-codes."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        # Internal code only -> empty string
        assert extractor._clean_part_number("E160970") == ""
        assert extractor._clean_part_number("E65138") == ""

        # Mixed internal code and manufacturer PN -> manufacturer PN only
        assert extractor._clean_part_number("E65138 1492-SPM1C100") == "1492-SPM1C100"
        assert extractor._clean_part_number("1492-SP1B060 E160970") == "1492-SP1B060"

    def test_clean_part_number_preserves_valid_parts(self) -> None:
        """Test that valid manufacturer part numbers are preserved."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        # Various manufacturer part number formats
        assert extractor._clean_part_number("1492-SP1B060") == "1492-SP1B060"
        assert extractor._clean_part_number("3RT2026-1DB40-1AAO") == "3RT2026-1DB40-1AAO"
        assert extractor._clean_part_number("G2R-1-SN") == "G2R-1-SN"
        assert extractor._clean_part_number("TRIO-PS/1AC/24DC/5") == "TRIO-PS/1AC/24DC/5"

    def test_parse_text_items_single_part(self) -> None:
        """Test parsing text items for a single part."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        # Simulate text items from a parts list row
        text_items = [
            {'text': '-K1', 'x': 50, 'y': 100},
            {'text': 'Safety Relay', 'x': 200, 'y': 100},
            {'text': '24VDC', 'x': 400, 'y': 100},
            {'text': 'G7SA-3A1B', 'x': 650, 'y': 100},
        ]

        parts = extractor._parse_text_items(text_items, page_num=5)

        assert len(parts) == 1
        assert parts[0].device_tag == '-K1'
        assert parts[0].designation == 'Safety Relay'
        assert parts[0].technical_data == '24VDC'
        assert parts[0].type_designation == 'G7SA-3A1B'
        assert parts[0].page_number == 5

    def test_parse_text_items_filters_internal_codes(self) -> None:
        """Test that parsing filters out internal codes from type designation."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        # Simulate text items with internal code mixed with manufacturer PN
        text_items = [
            {'text': '-F1', 'x': 50, 'y': 100},
            {'text': 'Fuse', 'x': 200, 'y': 100},
            {'text': '10A', 'x': 400, 'y': 100},
            {'text': 'E65138', 'x': 650, 'y': 100},  # Internal code
            {'text': '1492-SPM1C100', 'x': 720, 'y': 100},  # Manufacturer PN
        ]

        parts = extractor._parse_text_items(text_items, page_num=0)

        assert len(parts) == 1
        assert parts[0].device_tag == '-F1'
        # Should only have manufacturer PN, not internal code
        assert parts[0].type_designation == '1492-SPM1C100'
        assert 'E65138' not in parts[0].type_designation

    def test_parse_text_items_multiple_parts(self) -> None:
        """Test parsing text items for multiple parts."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        text_items = [
            # First part
            {'text': '-K1', 'x': 50, 'y': 100},
            {'text': 'Relay', 'x': 200, 'y': 100},
            {'text': 'G2R-1', 'x': 650, 'y': 100},
            # Second part
            {'text': '-K2', 'x': 50, 'y': 150},
            {'text': 'Contactor', 'x': 200, 'y': 150},
            {'text': 'LC1D09', 'x': 650, 'y': 150},
        ]

        parts = extractor._parse_text_items(text_items, page_num=0)

        assert len(parts) == 2
        assert parts[0].device_tag == '-K1'
        assert parts[0].type_designation == 'G2R-1'
        assert parts[1].device_tag == '-K2'
        assert parts[1].type_designation == 'LC1D09'

    def test_parse_text_items_multiline_entry(self) -> None:
        """Test parsing multi-line part entries.

        In DRAWER PDFs, designation/tech/type typically appear on the line
        BEFORE the device tag, not after. This test reflects that pattern.
        """
        extractor = OCRPartsExtractor(Path("test.pdf"))

        text_items = [
            # First line has designation and tech data
            {'text': 'Programmable Logic Controller', 'x': 200, 'y': 90},
            {'text': '24VDC', 'x': 400, 'y': 90},
            {'text': '6ES7-511-1AK02', 'x': 650, 'y': 90},
            # Second line has the device tag (y=100, ~10 points later)
            {'text': '-A1', 'x': 50, 'y': 100},
        ]

        parts = extractor._parse_text_items(text_items, page_num=0)

        assert len(parts) == 1
        assert parts[0].device_tag == '-A1'
        assert 'Programmable Logic Controller' in parts[0].designation
        assert '24VDC' in parts[0].technical_data
        assert parts[0].type_designation == '6ES7-511-1AK02'

    def test_parse_text_items_plus_prefix(self) -> None:
        """Test parsing device tags with + prefix."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        text_items = [
            {'text': '+DG-M1', 'x': 50, 'y': 100},
            {'text': 'Motor', 'x': 200, 'y': 100},
            {'text': '400VAC', 'x': 400, 'y': 100},
        ]

        parts = extractor._parse_text_items(text_items, page_num=0)

        assert len(parts) == 1
        assert parts[0].device_tag == '+DG-M1'

    def test_parse_text_items_empty(self) -> None:
        """Test parsing empty text items."""
        extractor = OCRPartsExtractor(Path("test.pdf"))
        parts = extractor._parse_text_items([], page_num=0)
        assert len(parts) == 0

    def test_parse_text_items_no_device_tags(self) -> None:
        """Test parsing text items without device tags."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        text_items = [
            {'text': 'Some text', 'x': 200, 'y': 100},
            {'text': 'More text', 'x': 400, 'y': 100},
        ]

        parts = extractor._parse_text_items(text_items, page_num=0)
        assert len(parts) == 0

    def test_parse_text_items_only_internal_code(self) -> None:
        """Test that parts with only internal codes have empty type_designation."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        text_items = [
            {'text': '-X1', 'x': 50, 'y': 100},
            {'text': 'Terminal Block', 'x': 200, 'y': 100},
            {'text': 'E89520', 'x': 650, 'y': 100},  # Only internal code
        ]

        parts = extractor._parse_text_items(text_items, page_num=0)

        assert len(parts) == 1
        assert parts[0].device_tag == '-X1'
        assert parts[0].type_designation == ''  # Should be empty after filtering

    def test_context_manager(self, tmp_path: Path) -> None:
        """Test using extractor as context manager."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()

        with OCRPartsExtractor(pdf_path) as extractor:
            assert extractor.doc is None  # Not opened yet

        # After exit, should be cleaned up
        assert extractor.doc is None


class TestColumnBoundaries:
    """Tests for column boundary detection."""

    def test_device_tag_column_left_boundary(self) -> None:
        """Test device tag column left boundary."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        # Item at left edge of device tag column
        text_items = [{'text': '-K1', 'x': 35, 'y': 100}]
        parts = extractor._parse_text_items(text_items, page_num=0)
        assert len(parts) == 1
        assert parts[0].device_tag == '-K1'

    def test_device_tag_column_right_boundary(self) -> None:
        """Test device tag column right boundary."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        # Item at right edge of device tag column (should still be captured)
        text_items = [{'text': '-K1', 'x': 189, 'y': 100}]
        parts = extractor._parse_text_items(text_items, page_num=0)
        assert len(parts) == 1

    def test_type_designation_column(self) -> None:
        """Test type designation (part number) column."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        text_items = [
            {'text': '-F1', 'x': 50, 'y': 100},
            {'text': '5SY6210-7', 'x': 650, 'y': 100},  # In type designation column
        ]
        parts = extractor._parse_text_items(text_items, page_num=0)

        assert len(parts) == 1
        assert parts[0].type_designation == '5SY6210-7'


class TestExtractVoltage:
    """Tests for voltage extraction from technical data."""

    def test_extract_vdc(self) -> None:
        """Test extracting VDC voltage."""
        from electrical_schematics.api.parts_import_service import PartsImportService

        service = PartsImportService(Mock())
        assert service._extract_voltage("24VDC coil") == "24VDC"
        assert service._extract_voltage("Rated 48 VDC") == "48VDC"

    def test_extract_vac(self) -> None:
        """Test extracting VAC voltage."""
        from electrical_schematics.api.parts_import_service import PartsImportService

        service = PartsImportService(Mock())
        assert service._extract_voltage("400VAC motor") == "400VAC"
        assert service._extract_voltage("230 V AC supply") == "230VAC"

    def test_extract_voltage_no_match(self) -> None:
        """Test voltage extraction when no voltage present."""
        from electrical_schematics.api.parts_import_service import PartsImportService

        service = PartsImportService(Mock())
        assert service._extract_voltage("No voltage here") is None
        assert service._extract_voltage("") is None


class TestCategoryMapping:
    """Tests for category mapping from device tags."""

    def test_category_from_device_tag_relay(self) -> None:
        """Test category mapping for relay."""
        from electrical_schematics.api.parts_import_service import PartsImportService

        service = PartsImportService(Mock())
        category, prefix = service._category_from_device_tag("-K1")
        assert category == "Relays"
        assert prefix == "K"

    def test_category_from_device_tag_motor(self) -> None:
        """Test category mapping for motor."""
        from electrical_schematics.api.parts_import_service import PartsImportService

        service = PartsImportService(Mock())
        category, prefix = service._category_from_device_tag("+DG-M1")
        assert category == "Motors"
        assert prefix == "M"

    def test_category_from_device_tag_sensor(self) -> None:
        """Test category mapping for sensor."""
        from electrical_schematics.api.parts_import_service import PartsImportService

        service = PartsImportService(Mock())
        category, prefix = service._category_from_device_tag("-B1")
        assert category == "Sensors"
        assert prefix == "B"

    def test_category_from_device_tag_fuse(self) -> None:
        """Test category mapping for fuse."""
        from electrical_schematics.api.parts_import_service import PartsImportService

        service = PartsImportService(Mock())
        category, prefix = service._category_from_device_tag("-F2")
        assert category == "Protection"
        assert prefix == "F"

    def test_category_from_device_tag_plc(self) -> None:
        """Test category mapping for PLC."""
        from electrical_schematics.api.parts_import_service import PartsImportService

        service = PartsImportService(Mock())
        category, prefix = service._category_from_device_tag("-A1")
        assert category == "PLCs"
        assert prefix == "A"

    def test_category_from_device_tag_unknown(self) -> None:
        """Test category mapping for unknown prefix."""
        from electrical_schematics.api.parts_import_service import PartsImportService

        service = PartsImportService(Mock())
        category, prefix = service._category_from_device_tag("-Z99")
        assert category == "Other"
        assert prefix == "X"


class TestPageMarkerDetection:
    """Tests for parts list page marker detection."""

    def test_page_markers_defined(self) -> None:
        """Test that page markers are defined."""
        assert len(OCRPartsExtractor.PAGE_MARKERS) > 0
        assert "Parts list" in OCRPartsExtractor.PAGE_MARKERS
        assert "Artikelstückliste" in OCRPartsExtractor.PAGE_MARKERS


class TestRealWorldScenarios:
    """Integration tests for real-world part number extraction scenarios."""

    def test_allen_bradley_fuse_with_internal_code(self) -> None:
        """Test Allen-Bradley fuse extraction with internal code."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        text_items = [
            {'text': '-F1', 'x': 50, 'y': 100},
            {'text': 'Circuit Breaker', 'x': 200, 'y': 100},
            {'text': '6A', 'x': 400, 'y': 100},
            {'text': 'E65138', 'x': 650, 'y': 100},
            {'text': '1492-SPM1C100', 'x': 720, 'y': 100},
        ]

        parts = extractor._parse_text_items(text_items, page_num=0)
        assert parts[0].type_designation == '1492-SPM1C100'

    def test_siemens_contactor_with_internal_code(self) -> None:
        """Test Siemens contactor extraction with internal code."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        text_items = [
            {'text': '-K1', 'x': 50, 'y': 100},
            {'text': 'Main Contactor', 'x': 200, 'y': 100},
            {'text': '24VDC', 'x': 400, 'y': 100},
            {'text': 'E160970', 'x': 650, 'y': 100},
            {'text': '3RT2026-1DB40-1AAO', 'x': 750, 'y': 100},
        ]

        parts = extractor._parse_text_items(text_items, page_num=0)
        assert parts[0].type_designation == '3RT2026-1DB40-1AAO'

    def test_omron_relay_standalone(self) -> None:
        """Test Omron relay extraction (no internal code)."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        text_items = [
            {'text': '-K5', 'x': 50, 'y': 100},
            {'text': 'Relay', 'x': 200, 'y': 100},
            {'text': '24VDC', 'x': 400, 'y': 100},
            {'text': 'G2R-1-SN', 'x': 650, 'y': 100},
        ]

        parts = extractor._parse_text_items(text_items, page_num=0)
        assert parts[0].type_designation == 'G2R-1-SN'

    def test_phoenix_contact_power_supply(self) -> None:
        """Test Phoenix Contact power supply extraction."""
        extractor = OCRPartsExtractor(Path("test.pdf"))

        text_items = [
            {'text': '-G1', 'x': 50, 'y': 100},
            {'text': 'Power Supply', 'x': 200, 'y': 100},
            {'text': '24VDC 5A', 'x': 400, 'y': 100},
            {'text': 'E89520', 'x': 650, 'y': 100},
            {'text': 'TRIO-PS/1AC/24DC/5', 'x': 750, 'y': 100},
        ]

        parts = extractor._parse_text_items(text_items, page_num=0)
        assert parts[0].type_designation == 'TRIO-PS/1AC/24DC/5'
