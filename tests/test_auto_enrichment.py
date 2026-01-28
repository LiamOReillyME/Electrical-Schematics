"""Unit tests for AutoEnrichmentService."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from typing import List

from electrical_schematics.services.auto_enrichment import (
    AutoEnrichmentService,
    EnrichmentResult,
    EnrichmentStatus,
    EnrichmentError,
)
from electrical_schematics.models.library_part import LibraryPart
from electrical_schematics.api.digikey_client import DigiKeyClient, DigiKeyAPIError
from electrical_schematics.api.digikey_models import (
    DigiKeyProduct,
    DigiKeyProductDetails,
    DigiKeySearchResponse,
    DigiKeyParameter,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_digikey_client():
    """Create a mock DigiKey client."""
    return Mock(spec=DigiKeyClient)


@pytest.fixture
def service(mock_digikey_client):
    """Create an AutoEnrichmentService with mock client."""
    return AutoEnrichmentService(
        digikey_client=mock_digikey_client,
        auto_create_client=False,
    )


@pytest.fixture
def service_no_client():
    """Create an AutoEnrichmentService without a client."""
    return AutoEnrichmentService(
        digikey_client=None,
        auto_create_client=False,
    )


@pytest.fixture
def sample_part():
    """Create a sample library part."""
    return LibraryPart(
        manufacturer_part_number="LM7805CT",
        manufacturer="Texas Instruments",
        description="Linear Voltage Regulator",
    )


@pytest.fixture
def sample_product_details():
    """Create sample DigiKey product details."""
    return DigiKeyProductDetails(
        part_number="296-LM7805CT-ND",
        manufacturer="Texas Instruments",
        manufacturer_part_number="LM7805CT",
        description="IC REG LINEAR 5V 1.5A TO220-3",
        detailed_description="Linear Voltage Regulator IC Positive Fixed 1 Output",
        primary_photo="https://example.com/image.jpg",
        primary_datasheet="https://example.com/datasheet.pdf",
        datasheets=["https://example.com/datasheet.pdf"],
        product_url="https://www.digikey.com/product-detail/...",
        parameters={
            "Voltage - Output": "5V",
            "Current - Output": "1.5A",
            "Package / Case": "TO-220-3",
        },
        category="PMIC - Voltage Regulators - Linear",
        family="Linear Voltage Regulators",
        limited_taxonomy={"CategoryName": "PMIC"},
        packaging="Tube",
        quantity_available=5000,
        minimum_order_quantity=1,
        standard_pricing=[
            {"break_quantity": 1, "unit_price": 0.75},
            {"break_quantity": 10, "unit_price": 0.65},
            {"break_quantity": 100, "unit_price": 0.50},
        ],
    )


@pytest.fixture
def sample_search_response():
    """Create sample DigiKey search response."""
    product = DigiKeyProduct(
        part_number="296-LM7805CT-ND",
        manufacturer="Texas Instruments",
        manufacturer_part_number="LM7805CT",
        description="IC REG LINEAR 5V 1.5A TO220-3",
        detailed_description="Linear Voltage Regulator",
        quantity_available=5000,
        unit_price=0.75,
        primary_photo="https://example.com/image.jpg",
        primary_datasheet="https://example.com/datasheet.pdf",
        product_url="https://www.digikey.com/product-detail/...",
        parameters=[
            DigiKeyParameter(parameter="Voltage - Output", value="5V"),
            DigiKeyParameter(parameter="Current - Output", value="1.5A"),
        ],
        category="PMIC - Voltage Regulators - Linear",
        family="Linear Voltage Regulators",
    )
    return DigiKeySearchResponse(
        products=[product],
        products_count=1,
        exact_manufacturer_products_count=1,
    )


# ============================================================================
# Initialization Tests
# ============================================================================

class TestAutoEnrichmentServiceInit:
    """Tests for AutoEnrichmentService initialization."""

    def test_init_with_client(self, mock_digikey_client):
        """Service should accept a pre-configured client."""
        service = AutoEnrichmentService(
            digikey_client=mock_digikey_client,
            auto_create_client=False,
        )
        assert service.digikey_client is mock_digikey_client
        assert service.is_available()

    def test_init_without_client(self):
        """Service should work without a client."""
        service = AutoEnrichmentService(
            digikey_client=None,
            auto_create_client=False,
        )
        assert service.digikey_client is None
        assert not service.is_available()

    def test_init_auto_create_client_no_settings(self):
        """Service should handle missing settings gracefully."""
        with patch(
            "electrical_schematics.services.auto_enrichment.get_settings"
        ) as mock_settings:
            mock_settings.return_value.settings.digikey = None
            service = AutoEnrichmentService(
                digikey_client=None,
                auto_create_client=True,
            )
            assert service.digikey_client is None

    def test_is_available_with_client(self, service):
        """is_available should return True when client exists."""
        assert service.is_available()

    def test_is_available_without_client(self, service_no_client):
        """is_available should return False when no client."""
        assert not service_no_client.is_available()


# ============================================================================
# Single Part Enrichment Tests
# ============================================================================

class TestEnrichPart:
    """Tests for single part enrichment."""

    def test_enrich_part_success_direct_lookup(
        self,
        service,
        mock_digikey_client,
        sample_part,
        sample_product_details,
    ):
        """Should successfully enrich part via direct lookup."""
        mock_digikey_client.get_product_details.return_value = sample_product_details

        result = service.enrich_part(sample_part)

        assert result.success
        assert result.status == EnrichmentStatus.SUCCESS
        assert result.digikey_part_number == "296-LM7805CT-ND"
        assert sample_part.digikey_part_number == "296-LM7805CT-ND"
        assert sample_part.digikey_description == "IC REG LINEAR 5V 1.5A TO220-3"
        assert sample_part.unit_price == 0.75
        assert sample_part.stock_quantity == 5000
        assert sample_part.datasheet_url == "https://example.com/datasheet.pdf"
        assert sample_part.digikey_lookup_success
        assert sample_part.digikey_lookup_attempted

    def test_enrich_part_success_search_fallback(
        self,
        service,
        mock_digikey_client,
        sample_part,
        sample_product_details,
        sample_search_response,
    ):
        """Should fall back to search when direct lookup fails."""
        # Direct lookup returns None
        mock_digikey_client.get_product_details.side_effect = [
            None,  # First call (direct lookup) fails
            sample_product_details,  # Second call (from search) succeeds
        ]
        mock_digikey_client.search_products.return_value = sample_search_response

        result = service.enrich_part(sample_part)

        assert result.success
        assert result.status == EnrichmentStatus.SUCCESS
        assert sample_part.digikey_lookup_success
        mock_digikey_client.search_products.assert_called_once_with(
            "LM7805CT", limit=1
        )

    def test_enrich_part_not_found(
        self,
        service,
        mock_digikey_client,
        sample_part,
    ):
        """Should handle part not found on DigiKey."""
        mock_digikey_client.get_product_details.return_value = None
        mock_digikey_client.search_products.return_value = DigiKeySearchResponse(
            products=[], products_count=0, exact_manufacturer_products_count=0
        )

        result = service.enrich_part(sample_part)

        assert not result.success
        assert result.status == EnrichmentStatus.NOT_FOUND
        assert sample_part.digikey_lookup_attempted
        assert not sample_part.digikey_lookup_success

    def test_enrich_part_no_client(self, service_no_client, sample_part):
        """Should return NO_CLIENT status when no client configured."""
        result = service_no_client.enrich_part(sample_part)

        assert not result.success
        assert result.status == EnrichmentStatus.NO_CLIENT
        assert "not configured" in result.message.lower()

    def test_enrich_part_already_enriched(
        self,
        service,
        sample_part,
    ):
        """Should skip already enriched parts."""
        sample_part.digikey_lookup_attempted = True
        sample_part.digikey_lookup_success = True
        sample_part.digikey_part_number = "EXISTING-PN"

        result = service.enrich_part(sample_part)

        assert result.status == EnrichmentStatus.ALREADY_ENRICHED
        assert result.digikey_part_number == "EXISTING-PN"

    def test_enrich_part_force_re_enrichment(
        self,
        service,
        mock_digikey_client,
        sample_part,
        sample_product_details,
    ):
        """Should re-enrich when force=True."""
        sample_part.digikey_lookup_attempted = True
        sample_part.digikey_lookup_success = True
        sample_part.digikey_part_number = "OLD-PN"

        mock_digikey_client.get_product_details.return_value = sample_product_details

        result = service.enrich_part(sample_part, force=True)

        assert result.success
        assert sample_part.digikey_part_number == "296-LM7805CT-ND"

    def test_enrich_part_api_error(
        self,
        service,
        mock_digikey_client,
        sample_part,
    ):
        """Should handle API errors gracefully."""
        mock_digikey_client.get_product_details.side_effect = DigiKeyAPIError(
            "API rate limit exceeded"
        )

        result = service.enrich_part(sample_part)

        assert not result.success
        assert result.status == EnrichmentStatus.API_ERROR
        assert result.error is not None
        assert sample_part.digikey_lookup_attempted
        assert not sample_part.digikey_lookup_success

    def test_enrich_part_unexpected_error(
        self,
        service,
        mock_digikey_client,
        sample_part,
    ):
        """Should handle unexpected errors gracefully."""
        mock_digikey_client.get_product_details.side_effect = RuntimeError(
            "Unexpected error"
        )

        result = service.enrich_part(sample_part)

        assert not result.success
        assert result.status == EnrichmentStatus.API_ERROR
        assert result.error is not None

    def test_enrich_part_updates_timestamp(
        self,
        service,
        mock_digikey_client,
        sample_part,
        sample_product_details,
    ):
        """Should update the part's updated_at timestamp."""
        old_timestamp = sample_part.updated_at
        mock_digikey_client.get_product_details.return_value = sample_product_details

        # Ensure some time passes
        import time
        time.sleep(0.01)

        service.enrich_part(sample_part)

        assert sample_part.updated_at > old_timestamp


# ============================================================================
# Data Population Tests
# ============================================================================

class TestDataPopulation:
    """Tests for populating part data from DigiKey responses."""

    def test_populate_all_fields(
        self,
        service,
        mock_digikey_client,
        sample_part,
        sample_product_details,
    ):
        """Should populate all available fields from product details."""
        mock_digikey_client.get_product_details.return_value = sample_product_details

        service.enrich_part(sample_part)

        assert sample_part.digikey_part_number == "296-LM7805CT-ND"
        assert sample_part.digikey_description == "IC REG LINEAR 5V 1.5A TO220-3"
        assert sample_part.digikey_url == "https://www.digikey.com/product-detail/..."
        assert sample_part.datasheet_url == "https://example.com/datasheet.pdf"
        assert sample_part.image_url == "https://example.com/image.jpg"
        assert sample_part.unit_price == 0.75
        assert sample_part.stock_quantity == 5000
        assert sample_part.parameters["Voltage - Output"] == "5V"
        assert sample_part.parameters["Current - Output"] == "1.5A"

    def test_preserve_existing_manufacturer(
        self,
        service,
        mock_digikey_client,
        sample_part,
        sample_product_details,
    ):
        """Should preserve existing manufacturer if set."""
        sample_part.manufacturer = "Original Manufacturer"
        mock_digikey_client.get_product_details.return_value = sample_product_details

        service.enrich_part(sample_part)

        # Should keep original manufacturer
        assert sample_part.manufacturer == "Original Manufacturer"

    def test_populate_manufacturer_if_empty(
        self,
        service,
        mock_digikey_client,
        sample_product_details,
    ):
        """Should populate manufacturer if not set."""
        part = LibraryPart(
            manufacturer_part_number="LM7805CT",
            manufacturer="",  # Empty
        )
        mock_digikey_client.get_product_details.return_value = sample_product_details

        service.enrich_part(part)

        assert part.manufacturer == "Texas Instruments"

    def test_populate_category_if_empty(
        self,
        service,
        mock_digikey_client,
        sample_product_details,
    ):
        """Should populate category if not set."""
        part = LibraryPart(
            manufacturer_part_number="LM7805CT",
            category="",  # Empty
        )
        mock_digikey_client.get_product_details.return_value = sample_product_details

        service.enrich_part(part)

        assert part.category == "PMIC - Voltage Regulators - Linear"

    def test_extract_lowest_price_tier(
        self,
        service,
        mock_digikey_client,
        sample_part,
        sample_product_details,
    ):
        """Should extract price from lowest quantity tier."""
        mock_digikey_client.get_product_details.return_value = sample_product_details

        service.enrich_part(sample_part)

        # Should use the break_quantity=1 tier price
        assert sample_part.unit_price == 0.75

    def test_handle_empty_pricing(
        self,
        service,
        mock_digikey_client,
        sample_part,
    ):
        """Should handle products without pricing."""
        details = DigiKeyProductDetails(
            part_number="TEST-PN",
            manufacturer="Test",
            manufacturer_part_number="TEST",
            description="Test product",
            detailed_description="",
            primary_photo=None,
            primary_datasheet=None,
            datasheets=[],
            product_url="",
            parameters={},
            category="",
            family="",
            limited_taxonomy={},
            packaging=None,
            quantity_available=0,
            minimum_order_quantity=1,
            standard_pricing=[],  # Empty pricing
        )
        mock_digikey_client.get_product_details.return_value = details

        result = service.enrich_part(sample_part)

        assert result.success
        assert sample_part.unit_price is None


# ============================================================================
# Batch Enrichment Tests
# ============================================================================

class TestBatchEnrichment:
    """Tests for batch part enrichment."""

    def test_enrich_parts_batch_all_success(
        self,
        service,
        mock_digikey_client,
        sample_product_details,
    ):
        """Should successfully enrich multiple parts."""
        parts = [
            LibraryPart(manufacturer_part_number=f"PART-{i}")
            for i in range(3)
        ]
        mock_digikey_client.get_product_details.return_value = sample_product_details

        results = service.enrich_parts_batch(parts, delay_ms=1)

        assert len(results) == 3
        assert all(r.success for r in results)

    def test_enrich_parts_batch_progress_callback(
        self,
        service,
        mock_digikey_client,
        sample_product_details,
    ):
        """Should call progress callback for each part."""
        parts = [
            LibraryPart(manufacturer_part_number=f"PART-{i}")
            for i in range(3)
        ]
        mock_digikey_client.get_product_details.return_value = sample_product_details

        progress_calls = []

        def callback(current, total, result):
            progress_calls.append((current, total, result.part.manufacturer_part_number))

        results = service.enrich_parts_batch(
            parts,
            delay_ms=1,
            progress_callback=callback,
        )

        assert len(progress_calls) == 3
        assert progress_calls[0] == (1, 3, "PART-0")
        assert progress_calls[1] == (2, 3, "PART-1")
        assert progress_calls[2] == (3, 3, "PART-2")

    def test_enrich_parts_batch_stop_on_error(
        self,
        service,
        mock_digikey_client,
    ):
        """Should stop processing on error when stop_on_error=True."""
        parts = [
            LibraryPart(manufacturer_part_number=f"PART-{i}")
            for i in range(5)
        ]

        # First two succeed, third fails
        mock_digikey_client.get_product_details.side_effect = [
            DigiKeyProductDetails(
                part_number="DK-1", manufacturer="M", manufacturer_part_number="P1",
                description="D", detailed_description="", primary_photo=None,
                primary_datasheet=None, datasheets=[], product_url="", parameters={},
                category="", family="", limited_taxonomy={}, packaging=None,
                quantity_available=0, minimum_order_quantity=1, standard_pricing=[],
            ),
            DigiKeyProductDetails(
                part_number="DK-2", manufacturer="M", manufacturer_part_number="P2",
                description="D", detailed_description="", primary_photo=None,
                primary_datasheet=None, datasheets=[], product_url="", parameters={},
                category="", family="", limited_taxonomy={}, packaging=None,
                quantity_available=0, minimum_order_quantity=1, standard_pricing=[],
            ),
            DigiKeyAPIError("API Error"),
        ]

        results = service.enrich_parts_batch(
            parts,
            delay_ms=1,
            stop_on_error=True,
        )

        assert len(results) == 5
        assert results[0].status == EnrichmentStatus.SUCCESS
        assert results[1].status == EnrichmentStatus.SUCCESS
        assert results[2].status == EnrichmentStatus.API_ERROR
        assert results[3].status == EnrichmentStatus.SKIPPED
        assert results[4].status == EnrichmentStatus.SKIPPED

    def test_enrich_parts_batch_continue_on_error(
        self,
        service,
        mock_digikey_client,
    ):
        """Should continue processing on error when stop_on_error=False."""
        parts = [
            LibraryPart(manufacturer_part_number=f"PART-{i}")
            for i in range(3)
        ]

        details = DigiKeyProductDetails(
            part_number="DK-1", manufacturer="M", manufacturer_part_number="P",
            description="D", detailed_description="", primary_photo=None,
            primary_datasheet=None, datasheets=[], product_url="", parameters={},
            category="", family="", limited_taxonomy={}, packaging=None,
            quantity_available=0, minimum_order_quantity=1, standard_pricing=[],
        )

        mock_digikey_client.get_product_details.side_effect = [
            details,
            DigiKeyAPIError("API Error"),
            details,
        ]

        results = service.enrich_parts_batch(
            parts,
            delay_ms=1,
            stop_on_error=False,
        )

        assert len(results) == 3
        assert results[0].status == EnrichmentStatus.SUCCESS
        assert results[1].status == EnrichmentStatus.API_ERROR
        assert results[2].status == EnrichmentStatus.SUCCESS

    def test_enrich_parts_batch_skip_already_enriched(
        self,
        service,
        mock_digikey_client,
        sample_product_details,
    ):
        """Should skip parts that are already enriched."""
        parts = [
            LibraryPart(manufacturer_part_number="PART-0"),
            LibraryPart(
                manufacturer_part_number="PART-1",
                digikey_lookup_attempted=True,
                digikey_lookup_success=True,
            ),
            LibraryPart(manufacturer_part_number="PART-2"),
        ]
        mock_digikey_client.get_product_details.return_value = sample_product_details

        results = service.enrich_parts_batch(parts, delay_ms=1)

        assert results[0].status == EnrichmentStatus.SUCCESS
        assert results[1].status == EnrichmentStatus.ALREADY_ENRICHED
        assert results[2].status == EnrichmentStatus.SUCCESS

        # Should only make 2 API calls (skipping the already enriched part)
        assert mock_digikey_client.get_product_details.call_count == 2

    def test_enrich_parts_batch_force_re_enrichment(
        self,
        service,
        mock_digikey_client,
        sample_product_details,
    ):
        """Should re-enrich all parts when force=True."""
        parts = [
            LibraryPart(
                manufacturer_part_number="PART-0",
                digikey_lookup_attempted=True,
                digikey_lookup_success=True,
            ),
            LibraryPart(manufacturer_part_number="PART-1"),
        ]
        mock_digikey_client.get_product_details.return_value = sample_product_details

        results = service.enrich_parts_batch(parts, force=True, delay_ms=1)

        assert all(r.status == EnrichmentStatus.SUCCESS for r in results)
        assert mock_digikey_client.get_product_details.call_count == 2


# ============================================================================
# Async Enrichment Tests
# ============================================================================

class TestAsyncEnrichment:
    """Tests for async/callback-based enrichment."""

    def test_enrich_parts_async_callback(
        self,
        service,
        mock_digikey_client,
        sample_product_details,
    ):
        """Should call callback with simpler signature."""
        parts = [
            LibraryPart(manufacturer_part_number=f"PART-{i}")
            for i in range(3)
        ]
        mock_digikey_client.get_product_details.return_value = sample_product_details

        callback_calls = []

        def callback(current, total, part):
            callback_calls.append((current, total, part.manufacturer_part_number))

        service.enrich_parts_async(parts, callback=callback, delay_ms=1)

        assert len(callback_calls) == 3


# ============================================================================
# Statistics Tests
# ============================================================================

class TestEnrichmentStats:
    """Tests for enrichment statistics."""

    def test_get_enrichment_stats(self, service, sample_part):
        """Should calculate correct statistics."""
        results = [
            EnrichmentResult(sample_part, EnrichmentStatus.SUCCESS, "OK"),
            EnrichmentResult(sample_part, EnrichmentStatus.SUCCESS, "OK"),
            EnrichmentResult(sample_part, EnrichmentStatus.NOT_FOUND, "Not found"),
            EnrichmentResult(sample_part, EnrichmentStatus.API_ERROR, "Error"),
            EnrichmentResult(sample_part, EnrichmentStatus.ALREADY_ENRICHED, "Skip"),
        ]

        stats = service.get_enrichment_stats(results)

        assert stats["total"] == 5
        assert stats["success"] == 2
        assert stats["not_found"] == 1
        assert stats["api_error"] == 1
        assert stats["already_enriched"] == 1
        assert stats["skipped"] == 0

    def test_get_enrichment_stats_empty(self, service):
        """Should handle empty results list."""
        stats = service.get_enrichment_stats([])

        assert stats["total"] == 0
        assert all(v == 0 for k, v in stats.items() if k != "total")


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_manufacturer_part_number(self, service, mock_digikey_client):
        """Should handle empty manufacturer part number."""
        # LibraryPart validates MPN, so we test with whitespace that gets stripped
        part = LibraryPart(manufacturer_part_number="   TEST   ")
        mock_digikey_client.get_product_details.return_value = None
        mock_digikey_client.search_products.return_value = DigiKeySearchResponse(
            products=[], products_count=0, exact_manufacturer_products_count=0
        )

        result = service.enrich_part(part)

        # Should still attempt lookup with normalized MPN
        assert result.status == EnrichmentStatus.NOT_FOUND

    def test_special_characters_in_part_number(
        self,
        service,
        mock_digikey_client,
        sample_product_details,
    ):
        """Should handle special characters in part numbers."""
        part = LibraryPart(manufacturer_part_number="LM7805CT/NOPB")
        mock_digikey_client.get_product_details.return_value = sample_product_details

        result = service.enrich_part(part)

        assert result.success

    def test_404_error_treated_as_not_found(
        self,
        service,
        mock_digikey_client,
        sample_part,
    ):
        """Should treat 404 errors as part not found."""
        mock_digikey_client.get_product_details.side_effect = DigiKeyAPIError(
            "404 Not Found"
        )
        mock_digikey_client.search_products.return_value = DigiKeySearchResponse(
            products=[], products_count=0, exact_manufacturer_products_count=0
        )

        result = service.enrich_part(sample_part)

        # 404 on direct lookup should trigger search fallback
        mock_digikey_client.search_products.assert_called_once()

    def test_client_setter(self, service_no_client, mock_digikey_client):
        """Should allow setting client after initialization."""
        assert not service_no_client.is_available()

        service_no_client.digikey_client = mock_digikey_client

        assert service_no_client.is_available()
        assert service_no_client.digikey_client is mock_digikey_client


# ============================================================================
# Integration-Style Tests (with mock)
# ============================================================================

class TestEnrichmentWorkflow:
    """Tests for complete enrichment workflows."""

    def test_full_enrichment_workflow(
        self,
        service,
        mock_digikey_client,
        sample_product_details,
    ):
        """Test complete workflow: create part, enrich, verify."""
        # Create a new part
        part = LibraryPart(
            manufacturer_part_number="LM7805CT",
            description="5V Regulator",
        )

        # Verify initial state
        assert not part.digikey_lookup_attempted
        assert not part.digikey_lookup_success
        assert part.digikey_part_number is None

        # Set up mock
        mock_digikey_client.get_product_details.return_value = sample_product_details

        # Enrich the part
        result = service.enrich_part(part)

        # Verify enrichment succeeded
        assert result.success
        assert part.digikey_lookup_attempted
        assert part.digikey_lookup_success
        assert part.digikey_part_number == "296-LM7805CT-ND"
        assert part.digikey_description == "IC REG LINEAR 5V 1.5A TO220-3"
        assert part.unit_price == 0.75
        assert part.stock_quantity == 5000
        assert len(part.parameters) > 0

        # Try to enrich again (should skip)
        result2 = service.enrich_part(part)
        assert result2.status == EnrichmentStatus.ALREADY_ENRICHED

        # Force re-enrichment
        result3 = service.enrich_part(part, force=True)
        assert result3.success
