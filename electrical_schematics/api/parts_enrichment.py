"""Parts list enrichment using DigiKey API."""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from electrical_schematics.pdf.exact_parts_parser import parse_parts_list, PartData
from electrical_schematics.api.digikey_client import DigiKeyClient, DigiKeyAPIError
from electrical_schematics.api.digikey_models import DigiKeyProductDetails
from electrical_schematics.database.manager import DatabaseManager, ComponentTemplate
from electrical_schematics.config.settings import get_settings
from electrical_schematics.models import IndustrialComponentType


@dataclass
class EnrichmentResult:
    """Result of enriching a part with DigiKey data."""
    device_tag: str
    part_number: str
    status: str  # 'found', 'not_found', 'already_exists', 'error'
    digikey_product: Optional[DigiKeyProductDetails] = None
    library_id: Optional[int] = None
    error_message: Optional[str] = None


class PartsEnrichmentService:
    """Service for enriching parts list data with DigiKey information."""

    def __init__(self, db_manager: DatabaseManager, digikey_client: Optional[DigiKeyClient] = None):
        """Initialize parts enrichment service.

        Args:
            db_manager: Database manager for component library
            digikey_client: DigiKey API client (optional, will create from settings if not provided)
        """
        self.db = db_manager
        self.digikey = digikey_client

    def _ensure_digikey_client(self) -> bool:
        """Ensure DigiKey client is available.

        Returns:
            True if client is available, False otherwise
        """
        if self.digikey:
            return True

        settings = get_settings()
        if settings.settings.digikey:
            self.digikey = DigiKeyClient(settings.settings.digikey)
            return True

        return False

    def enrich_from_pdf(self, pdf_path: Path) -> List[EnrichmentResult]:
        """Enrich parts from a PDF's parts list.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of enrichment results for each part
        """
        # Parse parts list
        parts = parse_parts_list(pdf_path)
        return self.enrich_parts(parts)

    def enrich_parts(self, parts: List[PartData]) -> List[EnrichmentResult]:
        """Enrich a list of parts with DigiKey data.

        Args:
            parts: List of PartData from parts list parser

        Returns:
            List of enrichment results
        """
        results = []

        for part in parts:
            result = self.enrich_single_part(part)
            results.append(result)

        return results

    def enrich_single_part(self, part: PartData) -> EnrichmentResult:
        """Enrich a single part with DigiKey data.

        Args:
            part: Part data from parser

        Returns:
            Enrichment result
        """
        # Extract clean part numbers from type_designation
        part_numbers = self._extract_part_numbers(part.type_designation)

        if not part_numbers:
            return EnrichmentResult(
                device_tag=part.device_tag,
                part_number=part.type_designation,
                status='error',
                error_message='No valid part numbers found'
            )

        # Check if any part number already exists in library
        for pn in part_numbers:
            existing = self.db.search_templates(pn)
            if existing:
                return EnrichmentResult(
                    device_tag=part.device_tag,
                    part_number=pn,
                    status='already_exists',
                    library_id=existing[0].id
                )

        # Try DigiKey lookup if client available
        if not self._ensure_digikey_client():
            return EnrichmentResult(
                device_tag=part.device_tag,
                part_number=part_numbers[0],
                status='error',
                error_message='DigiKey API not configured'
            )

        # Try each part number
        for pn in part_numbers:
            try:
                product = self.digikey.get_product_details(pn)
                if product:
                    # Create library entry
                    component_type = self._infer_component_type(part.device_tag)
                    designation_prefix = self._extract_prefix(part.device_tag)
                    category = self._infer_category(product)

                    library_id = self.db.add_from_digikey(
                        digikey_product=product,
                        category=category,
                        subcategory=product.family,
                        component_type=component_type,
                        designation_prefix=designation_prefix
                    )

                    return EnrichmentResult(
                        device_tag=part.device_tag,
                        part_number=pn,
                        status='found',
                        digikey_product=product,
                        library_id=library_id
                    )

            except DigiKeyAPIError as e:
                # Continue to next part number
                continue

        # No products found
        return EnrichmentResult(
            device_tag=part.device_tag,
            part_number=part_numbers[0],
            status='not_found'
        )

    def _extract_part_numbers(self, type_designation: str) -> List[str]:
        """Extract valid part numbers from type designation string.

        The type designation may contain multiple part numbers separated by spaces,
        internal reference numbers (starting with E), and other text.

        Args:
            type_designation: Raw type designation string

        Returns:
            List of potential part numbers (cleaned)
        """
        if not type_designation:
            return []

        # Split by spaces
        parts = type_designation.split()

        # Filter out internal reference numbers (typically E followed by digits)
        # and keep likely manufacturer part numbers
        part_numbers = []
        for p in parts:
            p = p.strip()
            if not p:
                continue

            # Skip internal references (E12345)
            if re.match(r'^E\d{4,}$', p):
                continue

            # Skip pure numbers (might be internal IDs)
            if re.match(r'^\d+$', p):
                continue

            # Keep alphanumeric part numbers with typical patterns
            # e.g., 3RT2026-1DB40, 1492-SP1B060, FN3025HL-30-71
            if re.match(r'^[A-Z0-9][-A-Za-z0-9/]{3,}$', p, re.IGNORECASE):
                part_numbers.append(p)

        return part_numbers

    def _infer_component_type(self, device_tag: str) -> str:
        """Infer component type from device tag.

        Args:
            device_tag: Device tag like -A1, -K1, -F2

        Returns:
            IndustrialComponentType enum value string
        """
        prefix = device_tag.lstrip('+-').rstrip('0123456789.')

        type_map = {
            'K': 'contactor',
            'Q': 'circuit_breaker',
            'F': 'fuse',
            'S': 'photoelectric_sensor',
            'B': 'proximity_sensor',
            'M': 'motor',
            'A': 'plc_input',
            'P': 'power_24vdc',
            'T': 'other',
            'R': 'relay',
            'L': 'indicator_light',
            'E': 'emergency_stop',
            'X': 'terminal_block',
            'U': 'other',  # Variable frequency drive
            'G': 'power_24vdc',  # Power supply
            'Z': 'other',  # EMI filter
            'EL': 'other',  # Fan
            'KR': 'relay',  # Safety relay
        }

        return type_map.get(prefix, 'other')

    def _extract_prefix(self, device_tag: str) -> str:
        """Extract designation prefix from device tag.

        Args:
            device_tag: Device tag like -A1, +DG-M1

        Returns:
            Designation prefix (e.g., 'A', 'M', 'K')
        """
        # Remove location prefix (+DG-)
        tag = device_tag.lstrip('+-')
        if '-' in tag:
            tag = tag.split('-')[-1]

        # Extract letter prefix
        prefix = ''
        for char in tag:
            if char.isalpha():
                prefix += char
            else:
                break

        return prefix if prefix else 'X'

    def _infer_category(self, product: DigiKeyProductDetails) -> str:
        """Infer component category from DigiKey product.

        Args:
            product: DigiKey product details

        Returns:
            Category string
        """
        # Use DigiKey category if available
        if product.category:
            # Map DigiKey categories to our categories
            category_lower = product.category.lower()

            if 'relay' in category_lower or 'contactor' in category_lower:
                return 'Relays & Contactors'
            elif 'motor' in category_lower:
                return 'Motors'
            elif 'sensor' in category_lower or 'proximity' in category_lower:
                return 'Sensors'
            elif 'circuit breaker' in category_lower or 'fuse' in category_lower:
                return 'Protection'
            elif 'power supply' in category_lower:
                return 'Power'
            elif 'plc' in category_lower or 'controller' in category_lower:
                return 'Control'
            elif 'terminal' in category_lower or 'connector' in category_lower:
                return 'Connectors'

            return product.category

        return 'Other'


def enrich_pdf_parts(pdf_path: Path, db_path: Optional[Path] = None) -> List[EnrichmentResult]:
    """Convenience function to enrich parts from a PDF.

    Args:
        pdf_path: Path to PDF file
        db_path: Optional database path (uses default if not provided)

    Returns:
        List of enrichment results
    """
    settings = get_settings()
    db_path = db_path or settings.get_database_path()

    db = DatabaseManager(db_path)
    service = PartsEnrichmentService(db)

    try:
        return service.enrich_from_pdf(pdf_path)
    finally:
        db.close()
