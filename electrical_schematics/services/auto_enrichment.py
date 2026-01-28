"""Auto-enrichment service for library parts using DigiKey API.

This service automatically queries DigiKey API to populate library parts
with additional data such as pricing, stock availability, datasheets,
and technical parameters.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Callable, Union

from electrical_schematics.api.digikey_client import (
    DigiKeyClient,
    DigiKeyAPIError,
)
from electrical_schematics.api.digikey_models import (
    DigiKeyProduct,
    DigiKeyProductDetails,
)
from electrical_schematics.config.settings import (
    DigiKeyConfig,
    get_settings,
)
from electrical_schematics.models.library_part import LibraryPart


logger = logging.getLogger(__name__)


class EnrichmentStatus(Enum):
    """Status of an enrichment operation."""
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    API_ERROR = "api_error"
    NO_CLIENT = "no_client"
    ALREADY_ENRICHED = "already_enriched"
    SKIPPED = "skipped"


@dataclass
class EnrichmentResult:
    """Result of an enrichment operation.

    Attributes:
        part: The library part that was processed
        status: Status of the enrichment
        message: Human-readable status message
        digikey_part_number: DigiKey part number if found
        error: Exception if an error occurred
    """
    part: LibraryPart
    status: EnrichmentStatus
    message: str
    digikey_part_number: Optional[str] = None
    error: Optional[Exception] = None

    @property
    def success(self) -> bool:
        """Check if enrichment was successful."""
        return self.status == EnrichmentStatus.SUCCESS


class EnrichmentError(Exception):
    """Exception raised when enrichment fails."""

    def __init__(self, message: str, part: Optional[LibraryPart] = None):
        super().__init__(message)
        self.part = part


class AutoEnrichmentService:
    """Service to automatically enrich library parts with DigiKey data.

    This service handles:
    - Single part enrichment with direct lookup or search fallback
    - Batch enrichment with rate limiting
    - Graceful error handling and status tracking

    Example:
        >>> service = AutoEnrichmentService()
        >>> part = LibraryPart(manufacturer_part_number="LM7805CT")
        >>> result = service.enrich_part(part)
        >>> if result.success:
        ...     print(f"Found: {part.digikey_description}")
        ...     print(f"Price: ${part.unit_price}")
    """

    # Default rate limiting: 100ms between calls for batch operations
    DEFAULT_BATCH_DELAY_MS = 100

    def __init__(
        self,
        digikey_client: Optional[DigiKeyClient] = None,
        auto_create_client: bool = True,
    ):
        """Initialize the auto-enrichment service.

        Args:
            digikey_client: Pre-configured DigiKey client. If None and
                auto_create_client is True, will attempt to create from settings.
            auto_create_client: If True, attempt to create client from app settings
                when digikey_client is None.
        """
        self._digikey_client = digikey_client
        self._client_creation_attempted = False

        if digikey_client is None and auto_create_client:
            self._digikey_client = self._create_client_from_settings()

    def _create_client_from_settings(self) -> Optional[DigiKeyClient]:
        """Create DigiKey client from application settings.

        Returns:
            DigiKey client if settings are configured, None otherwise
        """
        if self._client_creation_attempted:
            return None

        self._client_creation_attempted = True

        try:
            settings = get_settings()
            if settings.settings.digikey:
                return DigiKeyClient(settings.settings.digikey)
        except Exception as e:
            logger.warning(f"Failed to create DigiKey client from settings: {e}")

        return None

    @property
    def digikey_client(self) -> Optional[DigiKeyClient]:
        """Get the DigiKey client.

        Returns:
            DigiKey client if available
        """
        return self._digikey_client

    @digikey_client.setter
    def digikey_client(self, client: Optional[DigiKeyClient]) -> None:
        """Set the DigiKey client.

        Args:
            client: DigiKey client to use
        """
        self._digikey_client = client

    def is_available(self) -> bool:
        """Check if the enrichment service is available.

        Returns:
            True if DigiKey client is configured and ready
        """
        return self._digikey_client is not None

    def enrich_part(
        self,
        part: LibraryPart,
        force: bool = False,
    ) -> EnrichmentResult:
        """Enrich a library part with DigiKey data.

        Attempts to look up the part by manufacturer part number and
        populate available fields. Uses direct lookup first, then
        falls back to search if direct lookup returns no results.

        Args:
            part: Library part to enrich
            force: If True, re-enrich even if already attempted

        Returns:
            EnrichmentResult with status and details
        """
        # Check if client is available
        if not self._digikey_client:
            return EnrichmentResult(
                part=part,
                status=EnrichmentStatus.NO_CLIENT,
                message="DigiKey client not configured",
            )

        # Check if already enriched (unless forcing)
        if not force and part.digikey_lookup_attempted:
            if part.digikey_lookup_success:
                return EnrichmentResult(
                    part=part,
                    status=EnrichmentStatus.ALREADY_ENRICHED,
                    message="Part already enriched with DigiKey data",
                    digikey_part_number=part.digikey_part_number,
                )
            else:
                return EnrichmentResult(
                    part=part,
                    status=EnrichmentStatus.ALREADY_ENRICHED,
                    message="DigiKey lookup already attempted (no result)",
                )

        # Mark lookup as attempted
        part.digikey_lookup_attempted = True

        try:
            # Try direct lookup by manufacturer part number
            details = self._lookup_product_details(part.manufacturer_part_number)

            if details:
                self._populate_from_product_details(part, details)
                part.digikey_lookup_success = True
                part.updated_at = datetime.now()

                logger.info(
                    f"Successfully enriched part {part.manufacturer_part_number} "
                    f"from DigiKey (DK#: {part.digikey_part_number})"
                )

                return EnrichmentResult(
                    part=part,
                    status=EnrichmentStatus.SUCCESS,
                    message=f"Found and enriched from DigiKey",
                    digikey_part_number=part.digikey_part_number,
                )

            # Fallback: Try search
            search_result = self._search_and_get_details(
                part.manufacturer_part_number
            )

            if search_result:
                self._populate_from_product_details(part, search_result)
                part.digikey_lookup_success = True
                part.updated_at = datetime.now()

                logger.info(
                    f"Successfully enriched part {part.manufacturer_part_number} "
                    f"via search (DK#: {part.digikey_part_number})"
                )

                return EnrichmentResult(
                    part=part,
                    status=EnrichmentStatus.SUCCESS,
                    message=f"Found via search and enriched from DigiKey",
                    digikey_part_number=part.digikey_part_number,
                )

            # Part not found
            part.digikey_lookup_success = False
            part.updated_at = datetime.now()

            logger.info(
                f"Part {part.manufacturer_part_number} not found on DigiKey"
            )

            return EnrichmentResult(
                part=part,
                status=EnrichmentStatus.NOT_FOUND,
                message=f"Part not found on DigiKey",
            )

        except DigiKeyAPIError as e:
            part.digikey_lookup_success = False
            part.updated_at = datetime.now()

            logger.warning(
                f"DigiKey API error enriching {part.manufacturer_part_number}: {e}"
            )

            return EnrichmentResult(
                part=part,
                status=EnrichmentStatus.API_ERROR,
                message=f"DigiKey API error: {e}",
                error=e,
            )

        except Exception as e:
            part.digikey_lookup_success = False
            part.updated_at = datetime.now()

            logger.exception(
                f"Unexpected error enriching {part.manufacturer_part_number}"
            )

            return EnrichmentResult(
                part=part,
                status=EnrichmentStatus.API_ERROR,
                message=f"Unexpected error: {e}",
                error=e,
            )

    def _lookup_product_details(
        self,
        part_number: str
    ) -> Optional[DigiKeyProductDetails]:
        """Look up product details directly by part number.

        Args:
            part_number: Manufacturer or DigiKey part number

        Returns:
            Product details if found, None otherwise
        """
        try:
            return self._digikey_client.get_product_details(part_number)
        except DigiKeyAPIError as e:
            # 404 is expected for not-found, other errors should propagate
            if "404" in str(e) or "not found" in str(e).lower():
                return None
            raise

    def _search_and_get_details(
        self,
        query: str,
    ) -> Optional[DigiKeyProductDetails]:
        """Search for a product and get its details.

        Args:
            query: Search query (usually manufacturer part number)

        Returns:
            Product details if found, None otherwise
        """
        search_response = self._digikey_client.search_products(query, limit=1)

        if not search_response.products:
            return None

        # Get the first (best) match
        best_match = search_response.products[0]

        # Fetch full details for this product
        return self._digikey_client.get_product_details(best_match.part_number)

    def _populate_from_product_details(
        self,
        part: LibraryPart,
        details: DigiKeyProductDetails,
    ) -> None:
        """Populate library part fields from DigiKey product details.

        Args:
            part: Library part to update
            details: DigiKey product details
        """
        # Core identifiers
        part.digikey_part_number = details.part_number
        part.digikey_description = details.description

        # URLs
        part.digikey_url = details.product_url
        part.datasheet_url = details.primary_datasheet
        part.image_url = details.primary_photo

        # Stock and pricing
        part.stock_quantity = details.quantity_available

        # Extract unit price from pricing tiers
        if details.standard_pricing:
            # Get the lowest quantity price tier
            sorted_pricing = sorted(
                details.standard_pricing,
                key=lambda x: x.get('break_quantity', 0)
            )
            if sorted_pricing:
                part.unit_price = sorted_pricing[0].get('unit_price')

        # Technical parameters
        if details.parameters:
            part.parameters = details.parameters.copy()

        # Update manufacturer if not set
        if not part.manufacturer and details.manufacturer:
            part.manufacturer = details.manufacturer

        # Update category if available
        if details.category and not part.category:
            part.category = details.category

    def _populate_from_search_result(
        self,
        part: LibraryPart,
        product: DigiKeyProduct,
    ) -> None:
        """Populate library part fields from DigiKey search result.

        This is used as a fallback when full details are not available.

        Args:
            part: Library part to update
            product: DigiKey search result product
        """
        # Core identifiers
        part.digikey_part_number = product.part_number
        part.digikey_description = product.description

        # URLs
        part.digikey_url = product.product_url
        part.datasheet_url = product.primary_datasheet
        part.image_url = product.primary_photo

        # Stock and pricing
        part.stock_quantity = product.quantity_available
        part.unit_price = product.unit_price

        # Parameters from search result
        if product.parameters:
            part.parameters = {
                p.parameter: p.value for p in product.parameters
            }

        # Update manufacturer if not set
        if not part.manufacturer and product.manufacturer:
            part.manufacturer = product.manufacturer

        # Update category if available
        if product.category and not part.category:
            part.category = product.category

    def enrich_parts_batch(
        self,
        parts: List[LibraryPart],
        force: bool = False,
        delay_ms: int = DEFAULT_BATCH_DELAY_MS,
        progress_callback: Optional[Callable[[int, int, EnrichmentResult], None]] = None,
        stop_on_error: bool = False,
    ) -> List[EnrichmentResult]:
        """Enrich multiple parts with rate limiting.

        Args:
            parts: List of parts to enrich
            force: If True, re-enrich even if already attempted
            delay_ms: Delay between API calls in milliseconds (default 100ms)
            progress_callback: Optional callback(current, total, result) for progress
            stop_on_error: If True, stop processing on first error

        Returns:
            List of EnrichmentResults for each part
        """
        results = []
        total = len(parts)

        for i, part in enumerate(parts):
            result = self.enrich_part(part, force=force)
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, total, result)

            if stop_on_error and result.status == EnrichmentStatus.API_ERROR:
                logger.warning(
                    f"Stopping batch enrichment due to error on part "
                    f"{part.manufacturer_part_number}"
                )
                # Mark remaining parts as skipped
                for remaining_part in parts[i + 1:]:
                    results.append(EnrichmentResult(
                        part=remaining_part,
                        status=EnrichmentStatus.SKIPPED,
                        message="Skipped due to previous error",
                    ))
                break

            # Rate limiting delay (only between API calls)
            if i < total - 1 and result.status in (
                EnrichmentStatus.SUCCESS,
                EnrichmentStatus.NOT_FOUND,
                EnrichmentStatus.API_ERROR,
            ):
                time.sleep(delay_ms / 1000.0)

        return results

    def enrich_parts_async(
        self,
        parts: List[LibraryPart],
        callback: Optional[Callable[[int, int, LibraryPart], None]] = None,
        force: bool = False,
        delay_ms: int = DEFAULT_BATCH_DELAY_MS,
    ) -> None:
        """Enrich multiple parts asynchronously with progress callback.

        This is a convenience wrapper around enrich_parts_batch that
        uses a simpler callback signature.

        Args:
            parts: List of parts to enrich
            callback: Optional callback(current, total, part) for progress
            force: If True, re-enrich even if already attempted
            delay_ms: Delay between API calls in milliseconds
        """
        def progress_adapter(current: int, total: int, result: EnrichmentResult):
            if callback:
                callback(current, total, result.part)

        self.enrich_parts_batch(
            parts=parts,
            force=force,
            delay_ms=delay_ms,
            progress_callback=progress_adapter,
            stop_on_error=False,
        )

    def get_enrichment_stats(
        self,
        results: List[EnrichmentResult]
    ) -> dict:
        """Get statistics from a batch of enrichment results.

        Args:
            results: List of enrichment results

        Returns:
            Dictionary with enrichment statistics
        """
        stats = {
            "total": len(results),
            "success": 0,
            "not_found": 0,
            "api_error": 0,
            "no_client": 0,
            "already_enriched": 0,
            "skipped": 0,
        }

        for result in results:
            if result.status == EnrichmentStatus.SUCCESS:
                stats["success"] += 1
            elif result.status == EnrichmentStatus.NOT_FOUND:
                stats["not_found"] += 1
            elif result.status == EnrichmentStatus.API_ERROR:
                stats["api_error"] += 1
            elif result.status == EnrichmentStatus.NO_CLIENT:
                stats["no_client"] += 1
            elif result.status == EnrichmentStatus.ALREADY_ENRICHED:
                stats["already_enriched"] += 1
            elif result.status == EnrichmentStatus.SKIPPED:
                stats["skipped"] += 1

        return stats
