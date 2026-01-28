"""Tests for parts import service."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from typing import Dict

from electrical_schematics.api.parts_import_service import (
    PartsImportService,
    ImportResult,
    ImportStatus,
    PartImportDetail,
    DIGIKEY_CATEGORY_MAP
)
from electrical_schematics.pdf.ocr_parts_extractor import OCRPartData
from electrical_schematics.api.digikey_models import DigiKeyProductDetails
from electrical_schematics.database.manager import DatabaseManager, ComponentTemplate


@pytest.fixture
def mock_db_manager() -> Mock:
    """Create a mock database manager."""
    db = Mock(spec=DatabaseManager)
    db.search_templates.return_value = []
    db.add_component_template.return_value = 1
    db.add_from_digikey.return_value = 1
    db.update_template.return_value = None
    db.add_component_spec.return_value = 1
    return db


@pytest.fixture
def mock_digikey_config() -> Mock:
    """Create a mock DigiKey config."""
    config = Mock()
    config.client_id = "test_client_id"
    config.client_secret = "test_secret"
    return config


@pytest.fixture
def sample_digikey_product() -> DigiKeyProductDetails:
    """Create a sample DigiKey product."""
    return DigiKeyProductDetails(
        part_number="DK-G2R-1-SN-DC24",
        manufacturer="Omron",
        manufacturer_part_number="G2R-1-SN DC24",
        description="RELAY GEN PURPOSE SPDT 10A 24VDC",
        detailed_description="General purpose relay with SPDT contacts",
        primary_photo="https://example.com/photo.jpg",
        primary_datasheet="https://example.com/datasheet.pdf",
        datasheets=["https://example.com/datasheet.pdf"],
        product_url="https://www.digikey.com/product/G2R-1-SN",
        parameters={
            "Coil Voltage": "24VDC",
            "Contact Rating": "10A",
            "Contact Configuration": "SPDT"
        },
        category="Relays",
        family="Power Relays",
        limited_taxonomy={"CategoryName": "Relays"},
        packaging="Tube",
        quantity_available=1500,
        minimum_order_quantity=1,
        standard_pricing=[{"break_quantity": 1, "unit_price": 5.50}]
    )


class TestImportResult:
    """Tests for ImportResult dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        result = ImportResult()
        assert result.total_parts == 0
        assert result.parts_extracted == 0
        assert result.parts_added == 0
        assert result.parts_updated == 0
        assert result.parts_not_found == 0
        assert result.parts_skipped == 0
        assert result.errors == []
        assert result.details == []

    def test_success_rate_zero_parts(self) -> None:
        """Test success rate with zero parts."""
        result = ImportResult()
        assert result.success_rate == 0.0

    def test_success_rate_all_successful(self) -> None:
        """Test success rate with all parts successful."""
        result = ImportResult(
            parts_extracted=10,
            parts_added=7,
            parts_updated=3
        )
        assert result.success_rate == 100.0

    def test_success_rate_partial(self) -> None:
        """Test success rate with partial success."""
        result = ImportResult(
            parts_extracted=10,
            parts_added=3,
            parts_updated=2,
            parts_not_found=5
        )
        assert result.success_rate == 50.0


class TestPartImportDetail:
    """Tests for PartImportDetail dataclass."""

    def test_creation(self) -> None:
        """Test creating PartImportDetail."""
        detail = PartImportDetail(
            part_number="G2R-1-SN",
            device_tag="-K1",
            status=ImportStatus.ADDED,
            message="Added with DigiKey data",
            digikey_url="https://digikey.com/product/123",
            library_id=42
        )
        assert detail.part_number == "G2R-1-SN"
        assert detail.device_tag == "-K1"
        assert detail.status == ImportStatus.ADDED
        assert detail.library_id == 42

    def test_optional_fields(self) -> None:
        """Test optional fields default to None."""
        detail = PartImportDetail(
            part_number="ABC123",
            device_tag="-X1",
            status=ImportStatus.NOT_FOUND,
            message="Not found in DigiKey"
        )
        assert detail.digikey_url is None
        assert detail.library_id is None


class TestPartsImportService:
    """Tests for PartsImportService class."""

    def test_init(self, mock_db_manager: Mock) -> None:
        """Test service initialization."""
        service = PartsImportService(mock_db_manager)
        assert service.db == mock_db_manager
        assert service.digikey_config is None
        assert service._digikey_client is None

    def test_init_with_config(self, mock_db_manager: Mock, mock_digikey_config: Mock) -> None:
        """Test service initialization with DigiKey config."""
        service = PartsImportService(mock_db_manager, mock_digikey_config)
        assert service.digikey_config == mock_digikey_config

    def test_set_digikey_config(self, mock_db_manager: Mock, mock_digikey_config: Mock) -> None:
        """Test setting DigiKey config after initialization."""
        service = PartsImportService(mock_db_manager)
        service.set_digikey_config(mock_digikey_config)
        assert service.digikey_config == mock_digikey_config

    def test_deduplicate_parts(self, mock_db_manager: Mock) -> None:
        """Test part deduplication."""
        service = PartsImportService(mock_db_manager)

        parts = [
            OCRPartData("-K1", "Relay 1", "", "G2R-1", 0, 90.0),
            OCRPartData("-K2", "Relay 2", "", "G2R-1", 1, 95.0),  # Same part, higher confidence
            OCRPartData("-K3", "Relay 3", "", "G2R-2", 0, 80.0),
        ]

        unique = service._deduplicate_parts(parts)

        assert len(unique) == 2
        # Should keep higher confidence version of G2R-1
        g2r1 = [p for p in unique if p.type_designation == "G2R-1"][0]
        assert g2r1.confidence == 95.0

    def test_process_part_skip_no_part_number(self, mock_db_manager: Mock) -> None:
        """Test processing part with no part number."""
        service = PartsImportService(mock_db_manager)

        part = OCRPartData("-K1", "Relay", "", "", 0)
        result = service._process_part(part, update_existing=True)

        assert result.status == ImportStatus.SKIPPED
        assert "No valid part number" in result.message

    def test_process_part_skip_short_part_number(self, mock_db_manager: Mock) -> None:
        """Test processing part with too short part number."""
        service = PartsImportService(mock_db_manager)

        part = OCRPartData("-K1", "Relay", "", "AB", 0)  # Only 2 chars
        result = service._process_part(part, update_existing=True)

        assert result.status == ImportStatus.SKIPPED

    def test_process_part_skip_existing_no_update(self, mock_db_manager: Mock) -> None:
        """Test skipping existing part when update_existing is False."""
        # Setup mock to find existing
        existing = ComponentTemplate(
            id=1, category="Relays", subcategory=None, name="Test Relay",
            designation_prefix="K", component_type="RELAY", default_voltage="24VDC",
            description="", manufacturer="", part_number="G2R-1-SN",
            datasheet_url=None, image_path=None, symbol_svg=None
        )
        mock_db_manager.search_templates.return_value = [existing]

        service = PartsImportService(mock_db_manager)
        part = OCRPartData("-K1", "Relay", "", "G2R-1-SN", 0)

        result = service._process_part(part, update_existing=False)

        assert result.status == ImportStatus.SKIPPED
        assert "Already in library" in result.message
        assert result.library_id == 1

    def test_add_from_ocr_only_new(self, mock_db_manager: Mock) -> None:
        """Test adding new part from OCR data only."""
        service = PartsImportService(mock_db_manager)

        part = OCRPartData("-K1", "Safety Relay", "24VDC", "G7SA-3A1B", 5)
        result = service._add_from_ocr_only(part, existing=None)

        assert result.status == ImportStatus.ADDED
        assert "OCR data" in result.message
        mock_db_manager.add_component_template.assert_called_once()

    def test_add_from_ocr_only_update_existing(self, mock_db_manager: Mock) -> None:
        """Test updating existing part with OCR data."""
        existing = ComponentTemplate(
            id=1, category="Relays", subcategory=None, name="Test",
            designation_prefix="K", component_type="RELAY", default_voltage=None,
            description=None, manufacturer=None, part_number="G2R-1-SN",
            datasheet_url=None, image_path=None, symbol_svg=None
        )

        service = PartsImportService(mock_db_manager)
        part = OCRPartData("-K1", "Updated Description", "", "G2R-1-SN", 0)

        result = service._add_from_ocr_only(part, existing)

        assert result.status == ImportStatus.UPDATED
        mock_db_manager.update_template.assert_called_once()


class TestDigiKeyCategoryMapping:
    """Tests for DigiKey category mapping."""

    def test_relay_categories(self) -> None:
        """Test relay category mappings."""
        assert DIGIKEY_CATEGORY_MAP["Relays"] == ("Relays", "K")
        assert DIGIKEY_CATEGORY_MAP["Power Relays"] == ("Relays", "K")
        assert DIGIKEY_CATEGORY_MAP["Signal Relays"] == ("Relays", "K")

    def test_sensor_categories(self) -> None:
        """Test sensor category mappings."""
        assert DIGIKEY_CATEGORY_MAP["Proximity Sensors"] == ("Sensors", "B")
        assert DIGIKEY_CATEGORY_MAP["Photoelectric Sensors"] == ("Sensors", "B")

    def test_protection_categories(self) -> None:
        """Test protection category mappings."""
        assert DIGIKEY_CATEGORY_MAP["Fuses"] == ("Protection", "F")
        assert DIGIKEY_CATEGORY_MAP["Circuit Breakers"] == ("Protection", "F")

    def test_default_category(self) -> None:
        """Test default category mapping."""
        assert DIGIKEY_CATEGORY_MAP["default"] == ("Other", "X")


class TestDetermineCategory:
    """Tests for category determination from DigiKey data."""

    def test_determine_from_category(
        self,
        mock_db_manager: Mock,
        sample_digikey_product: DigiKeyProductDetails
    ) -> None:
        """Test category determination from DigiKey category."""
        service = PartsImportService(mock_db_manager)

        category, prefix = service._determine_category(sample_digikey_product)

        assert category == "Relays"
        assert prefix == "K"

    def test_determine_from_family(self, mock_db_manager: Mock) -> None:
        """Test category determination from DigiKey family."""
        service = PartsImportService(mock_db_manager)

        product = DigiKeyProductDetails(
            part_number="TEST123",
            manufacturer="Test",
            manufacturer_part_number="T123",
            description="Test product",
            detailed_description="",
            primary_photo=None,
            primary_datasheet=None,
            datasheets=[],
            product_url="",
            parameters={},
            category="Unknown",  # Unknown category
            family="Power Relays",  # But known family
            limited_taxonomy={},
            packaging=None,
            quantity_available=0,
            minimum_order_quantity=1,
            standard_pricing=[]
        )

        category, prefix = service._determine_category(product)
        assert category == "Relays"

    def test_determine_from_description_keywords(self, mock_db_manager: Mock) -> None:
        """Test category determination from description keywords."""
        service = PartsImportService(mock_db_manager)

        product = DigiKeyProductDetails(
            part_number="TEST123",
            manufacturer="Test",
            manufacturer_part_number="T123",
            description="Motor driver IC",  # Has 'motor' keyword
            detailed_description="",
            primary_photo=None,
            primary_datasheet=None,
            datasheets=[],
            product_url="",
            parameters={},
            category="Integrated Circuits",
            family="Driver ICs",
            limited_taxonomy={},
            packaging=None,
            quantity_available=0,
            minimum_order_quantity=1,
            standard_pricing=[]
        )

        category, prefix = service._determine_category(product)
        assert category == "Motors"
        assert prefix == "M"


class TestComponentTypeFromPrefix:
    """Tests for component type determination from prefix."""

    def test_known_prefixes(self, mock_db_manager: Mock) -> None:
        """Test component type for known prefixes."""
        service = PartsImportService(mock_db_manager)

        assert service._component_type_from_prefix("K") == "RELAY"
        assert service._component_type_from_prefix("M") == "MOTOR"
        assert service._component_type_from_prefix("F") == "FUSE"
        assert service._component_type_from_prefix("B") == "SENSOR"
        assert service._component_type_from_prefix("A") == "PLC"
        assert service._component_type_from_prefix("S") == "SWITCH"

    def test_unknown_prefix(self, mock_db_manager: Mock) -> None:
        """Test component type for unknown prefix."""
        service = PartsImportService(mock_db_manager)

        assert service._component_type_from_prefix("Z") == "OTHER"


class TestIntegrationWorkflow:
    """Integration tests for the complete import workflow."""

    @patch('electrical_schematics.api.parts_import_service.OCRPartsExtractor')
    def test_import_parts_no_parts_found(
        self,
        mock_extractor_class: Mock,
        mock_db_manager: Mock
    ) -> None:
        """Test import workflow when no parts are found."""
        # Setup mock to return no parts
        mock_extractor = MagicMock()
        mock_extractor.__enter__ = Mock(return_value=mock_extractor)
        mock_extractor.__exit__ = Mock(return_value=False)
        mock_extractor.extract_parts.return_value = []
        mock_extractor.check_dependencies.return_value = (True, "")
        mock_extractor_class.return_value = mock_extractor

        service = PartsImportService(mock_db_manager)
        result = service.import_parts(Path("test.pdf"))

        assert result.parts_extracted == 0
        assert "No parts found" in result.errors[0]

    @patch('electrical_schematics.api.parts_import_service.OCRPartsExtractor')
    def test_import_parts_success(
        self,
        mock_extractor_class: Mock,
        mock_db_manager: Mock
    ) -> None:
        """Test successful import workflow."""
        # Setup mock to return parts
        mock_extractor = MagicMock()
        mock_extractor.__enter__ = Mock(return_value=mock_extractor)
        mock_extractor.__exit__ = Mock(return_value=False)
        mock_extractor.extract_parts.return_value = [
            OCRPartData("-K1", "Relay", "24VDC", "G2R-1-SN", 0, 90.0),
            OCRPartData("-F1", "Fuse", "", "5SY6210-7", 0, 85.0),
        ]
        mock_extractor.check_dependencies.return_value = (True, "")
        mock_extractor_class.return_value = mock_extractor

        # No DigiKey client, so parts will be added from OCR only
        service = PartsImportService(mock_db_manager)
        result = service.import_parts(Path("test.pdf"))

        assert result.parts_extracted == 2
        assert result.parts_added == 2
        assert len(result.details) == 2

    @patch('electrical_schematics.api.parts_import_service.OCRPartsExtractor')
    def test_import_parts_with_progress_callback(
        self,
        mock_extractor_class: Mock,
        mock_db_manager: Mock
    ) -> None:
        """Test import workflow with progress callback."""
        mock_extractor = MagicMock()
        mock_extractor.__enter__ = Mock(return_value=mock_extractor)
        mock_extractor.__exit__ = Mock(return_value=False)
        mock_extractor.extract_parts.return_value = [
            OCRPartData("-K1", "Relay", "", "G2R-1", 0)
        ]
        mock_extractor.check_dependencies.return_value = (True, "")
        mock_extractor_class.return_value = mock_extractor

        progress_calls = []

        def progress_callback(msg: str, current: int, total: int) -> None:
            progress_calls.append((msg, current, total))

        service = PartsImportService(mock_db_manager)
        service.import_parts(Path("test.pdf"), progress_callback=progress_callback)

        # Should have received progress callbacks
        assert len(progress_calls) > 0
