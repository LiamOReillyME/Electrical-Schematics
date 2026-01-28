"""Parts import service for orchestrating PDF OCR to DigiKey to Library workflow.

This service coordinates:
1. OCR extraction of parts from PDF
2. DigiKey API lookup for part details
3. Component library population/updates
"""

import logging
from pathlib import Path
from typing import Optional, List, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

from electrical_schematics.pdf.ocr_parts_extractor import OCRPartsExtractor, OCRPartData
from electrical_schematics.api.digikey_client import DigiKeyClient, DigiKeyAPIError
from electrical_schematics.api.digikey_models import DigiKeyProductDetails
from electrical_schematics.database.manager import DatabaseManager, ComponentTemplate
from electrical_schematics.config.settings import DigiKeyConfig


logger = logging.getLogger(__name__)


class ImportStatus(Enum):
    """Status of individual part import."""
    ADDED = "added"
    UPDATED = "updated"
    NOT_FOUND = "not_found"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class PartImportDetail:
    """Detail for a single part import operation."""
    part_number: str
    device_tag: str
    status: ImportStatus
    message: str
    digikey_url: Optional[str] = None
    library_id: Optional[int] = None


@dataclass
class ImportResult:
    """Results of parts import operation."""
    total_parts: int = 0
    parts_extracted: int = 0
    parts_added: int = 0
    parts_updated: int = 0
    parts_not_found: int = 0
    parts_skipped: int = 0
    errors: List[str] = field(default_factory=list)
    details: List[PartImportDetail] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.parts_extracted == 0:
            return 0.0
        successful = self.parts_added + self.parts_updated
        return (successful / self.parts_extracted) * 100


# Category mapping from DigiKey taxonomy to our categories
DIGIKEY_CATEGORY_MAP = {
    # Relays
    "Relays": ("Relays", "K"),
    "Power Relays": ("Relays", "K"),
    "Signal Relays": ("Relays", "K"),
    "Solid State Relays": ("Relays", "K"),
    "Relay Sockets": ("Relays", "K"),

    # Contactors
    "Contactors": ("Contactors", "K"),
    "Motor Starters": ("Contactors", "K"),

    # Circuit Protection
    "Fuses": ("Protection", "F"),
    "Circuit Breakers": ("Protection", "F"),
    "Fuse Holders": ("Protection", "F"),
    "Surge Protectors": ("Protection", "F"),

    # Sensors
    "Proximity Sensors": ("Sensors", "B"),
    "Photoelectric Sensors": ("Sensors", "B"),
    "Limit Switches": ("Sensors", "S"),
    "Pressure Sensors": ("Sensors", "B"),
    "Temperature Sensors": ("Sensors", "B"),
    "Encoders": ("Sensors", "B"),
    "Optical Sensors": ("Sensors", "B"),

    # Switches
    "Pushbutton Switches": ("Switches", "S"),
    "Toggle Switches": ("Switches", "S"),
    "Selector Switches": ("Switches", "S"),
    "Emergency Stop": ("Switches", "S"),
    "Rotary Switches": ("Switches", "S"),

    # Motors
    "AC Motors": ("Motors", "M"),
    "DC Motors": ("Motors", "M"),
    "Stepper Motors": ("Motors", "M"),
    "Servo Motors": ("Motors", "M"),
    "Motor Drivers": ("Drives", "U"),

    # Power Supplies
    "Power Supplies": ("Power Supplies", "G"),
    "DC-DC Converters": ("Power Supplies", "G"),
    "AC-DC Converters": ("Power Supplies", "G"),

    # PLCs and Controllers
    "Programmable Logic Controllers": ("PLCs", "A"),
    "PLCs": ("PLCs", "A"),
    "I/O Modules": ("PLCs", "A"),
    "HMI": ("HMI", "A"),

    # Connectors
    "Terminal Blocks": ("Connectors", "X"),
    "Connectors": ("Connectors", "X"),
    "Wire Terminals": ("Connectors", "X"),

    # Indicators
    "Pilot Lights": ("Indicators", "H"),
    "LED Indicators": ("Indicators", "H"),
    "Panel Meters": ("Indicators", "P"),

    # Transformers
    "Transformers": ("Transformers", "T"),
    "Current Transformers": ("Transformers", "T"),

    # Default
    "default": ("Other", "X"),
}


class PartsImportService:
    """Service to orchestrate parts list import workflow.

    This service:
    1. Uses OCR to extract part numbers from PDF parts lists
    2. Queries DigiKey API for each part number
    3. Adds or updates components in the library
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        digikey_config: Optional[DigiKeyConfig] = None
    ):
        """Initialize parts import service.

        Args:
            db_manager: Database manager for library operations
            digikey_config: DigiKey API configuration (optional, can be set later)
        """
        self.db = db_manager
        self.digikey_config = digikey_config
        self._digikey_client: Optional[DigiKeyClient] = None

    @property
    def digikey_client(self) -> Optional[DigiKeyClient]:
        """Get or create DigiKey client."""
        if self._digikey_client is None and self.digikey_config:
            self._digikey_client = DigiKeyClient(self.digikey_config)
        return self._digikey_client

    def set_digikey_config(self, config: DigiKeyConfig) -> None:
        """Set DigiKey configuration.

        Args:
            config: DigiKey API configuration
        """
        self.digikey_config = config
        self._digikey_client = None  # Reset client

    def import_parts(
        self,
        pdf_path: Path,
        update_existing: bool = True,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> ImportResult:
        """Execute full import workflow.

        Args:
            pdf_path: Path to PDF file
            update_existing: Whether to update existing library entries
            progress_callback: Optional callback(phase, current, total)

        Returns:
            ImportResult with summary and details
        """
        result = ImportResult()

        # Phase 1: Extract parts via OCR
        if progress_callback:
            progress_callback("Extracting parts from PDF...", 0, 0)

        try:
            parts = self._extract_parts(pdf_path, progress_callback)
            result.parts_extracted = len(parts)
            result.total_parts = len(parts)
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            result.errors.append(f"OCR extraction failed: {e}")
            return result

        if not parts:
            result.errors.append("No parts found in PDF")
            return result

        # Deduplicate by part number
        unique_parts = self._deduplicate_parts(parts)
        logger.info(f"Found {len(unique_parts)} unique parts from {len(parts)} total entries")

        # Phase 2: Lookup and import each part
        total = len(unique_parts)
        for idx, part in enumerate(unique_parts):
            if progress_callback:
                progress_callback(
                    f"Processing: {part.type_designation or part.device_tag}",
                    idx + 1,
                    total
                )

            detail = self._process_part(part, update_existing)
            result.details.append(detail)

            # Update counters
            if detail.status == ImportStatus.ADDED:
                result.parts_added += 1
            elif detail.status == ImportStatus.UPDATED:
                result.parts_updated += 1
            elif detail.status == ImportStatus.NOT_FOUND:
                result.parts_not_found += 1
            elif detail.status == ImportStatus.SKIPPED:
                result.parts_skipped += 1
            elif detail.status == ImportStatus.ERROR:
                result.errors.append(f"{part.device_tag}: {detail.message}")

        return result

    def _extract_parts(
        self,
        pdf_path: Path,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[OCRPartData]:
        """Extract parts from PDF using OCR."""

        def ocr_progress(current: int, total: int, message: str) -> None:
            if progress_callback:
                progress_callback(f"OCR: {message}", current, total)

        with OCRPartsExtractor(pdf_path) as extractor:
            # Check dependencies
            ok, error = extractor.check_dependencies()
            if not ok:
                logger.warning(f"OCR dependencies not available: {error}")
                # Fall back to text extraction only
                return extractor.extract_parts(use_ocr=False, progress_callback=ocr_progress)

            return extractor.extract_parts(progress_callback=ocr_progress)

    def _deduplicate_parts(self, parts: List[OCRPartData]) -> List[OCRPartData]:
        """Remove duplicate parts, keeping highest confidence version."""
        seen = {}
        for part in parts:
            key = part.type_designation or part.device_tag
            if key not in seen or part.confidence > seen[key].confidence:
                seen[key] = part
        return list(seen.values())

    def _process_part(
        self,
        part: OCRPartData,
        update_existing: bool
    ) -> PartImportDetail:
        """Process a single part: lookup in DigiKey and add/update library."""
        part_number = part.type_designation

        # Skip if no part number
        if not part_number or len(part_number) < 3:
            return PartImportDetail(
                part_number=part_number or "N/A",
                device_tag=part.device_tag,
                status=ImportStatus.SKIPPED,
                message="No valid part number"
            )

        # Check if already in library
        existing = self._find_existing(part_number)

        # Skip if exists and not updating
        if existing and not update_existing:
            return PartImportDetail(
                part_number=part_number,
                device_tag=part.device_tag,
                status=ImportStatus.SKIPPED,
                message="Already in library",
                library_id=existing.id
            )

        # Lookup in DigiKey
        digikey_data = None
        if self.digikey_client:
            try:
                digikey_data = self._lookup_digikey(part_number)
            except DigiKeyAPIError as e:
                logger.warning(f"DigiKey lookup failed for {part_number}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error looking up {part_number}: {e}")

        # If DigiKey lookup failed, try searching
        if not digikey_data and self.digikey_client:
            try:
                search_result = self.digikey_client.search_products(part_number, limit=1)
                if search_result.products:
                    product = search_result.products[0]
                    # Get full details
                    digikey_data = self._lookup_digikey(product.part_number)
            except Exception as e:
                logger.warning(f"DigiKey search failed for {part_number}: {e}")

        # If still no DigiKey data
        if not digikey_data:
            # Still add to library with OCR data only
            return self._add_from_ocr_only(part, existing)

        # Add or update library entry
        return self._add_or_update_library(part, digikey_data, existing)

    def _find_existing(self, part_number: str) -> Optional[ComponentTemplate]:
        """Find existing component in library by part number."""
        results = self.db.search_templates(part_number)
        for template in results:
            if template.part_number and part_number.lower() in template.part_number.lower():
                return template
        return None

    def _lookup_digikey(self, part_number: str) -> Optional[DigiKeyProductDetails]:
        """Query DigiKey for part details."""
        if not self.digikey_client:
            return None

        try:
            return self.digikey_client.get_product_details(part_number)
        except DigiKeyAPIError:
            return None

    def _add_from_ocr_only(
        self,
        part: OCRPartData,
        existing: Optional[ComponentTemplate]
    ) -> PartImportDetail:
        """Add part to library using only OCR-extracted data."""
        # Determine category from device tag
        category, prefix = self._category_from_device_tag(part.device_tag)

        if existing:
            # Update existing with OCR data if we have more info
            if part.designation and not existing.description:
                existing.description = part.designation
            self.db.update_template(existing.id, existing)
            return PartImportDetail(
                part_number=part.type_designation or "N/A",
                device_tag=part.device_tag,
                status=ImportStatus.UPDATED,
                message="Updated with OCR data (DigiKey not found)",
                library_id=existing.id
            )

        # Create new entry from OCR data
        template = ComponentTemplate(
            id=None,
            category=category,
            subcategory=None,
            name=part.type_designation or part.device_tag,
            designation_prefix=prefix,
            component_type=self._component_type_from_prefix(prefix),
            default_voltage=self._extract_voltage(part.technical_data),
            description=part.designation,
            manufacturer=None,
            part_number=part.type_designation,
            datasheet_url=None,
            image_path=None,
            symbol_svg=None
        )

        try:
            template_id = self.db.add_component_template(template)
            return PartImportDetail(
                part_number=part.type_designation or "N/A",
                device_tag=part.device_tag,
                status=ImportStatus.ADDED,
                message="Added from OCR data (DigiKey not found)",
                library_id=template_id
            )
        except Exception as e:
            return PartImportDetail(
                part_number=part.type_designation or "N/A",
                device_tag=part.device_tag,
                status=ImportStatus.ERROR,
                message=f"Database error: {e}"
            )

    def _add_or_update_library(
        self,
        part: OCRPartData,
        digikey_data: DigiKeyProductDetails,
        existing: Optional[ComponentTemplate]
    ) -> PartImportDetail:
        """Add or update library entry with DigiKey data."""
        # Determine category
        category, prefix = self._determine_category(digikey_data)

        # Fall back to device tag category if DigiKey doesn't provide good match
        if category == "Other":
            tag_category, tag_prefix = self._category_from_device_tag(part.device_tag)
            if tag_category != "Other":
                category, prefix = tag_category, tag_prefix

        # Determine voltage from DigiKey parameters
        voltage = None
        for param_name, param_value in digikey_data.parameters.items():
            param_lower = param_name.lower()
            if 'voltage' in param_lower or 'coil' in param_lower:
                voltage = param_value
                break

        if existing:
            # Update existing entry
            existing.name = f"{digikey_data.manufacturer} {digikey_data.manufacturer_part_number}"
            existing.description = digikey_data.description
            existing.manufacturer = digikey_data.manufacturer
            existing.part_number = digikey_data.part_number
            existing.datasheet_url = digikey_data.primary_datasheet
            existing.image_path = digikey_data.primary_photo
            if voltage:
                existing.default_voltage = voltage

            try:
                self.db.update_template(existing.id, existing)

                # Update specs
                for param_name, param_value in digikey_data.parameters.items():
                    from electrical_schematics.database.manager import ComponentSpec
                    spec = ComponentSpec(
                        id=None,
                        component_id=existing.id,
                        spec_name=param_name,
                        spec_value=param_value,
                        unit=None
                    )
                    try:
                        self.db.add_component_spec(spec)
                    except Exception:
                        pass  # Ignore duplicate specs

                return PartImportDetail(
                    part_number=digikey_data.part_number,
                    device_tag=part.device_tag,
                    status=ImportStatus.UPDATED,
                    message="Updated with DigiKey data",
                    digikey_url=digikey_data.product_url,
                    library_id=existing.id
                )
            except Exception as e:
                return PartImportDetail(
                    part_number=digikey_data.part_number,
                    device_tag=part.device_tag,
                    status=ImportStatus.ERROR,
                    message=f"Update failed: {e}"
                )

        # Add new entry
        try:
            component_id = self.db.add_from_digikey(
                digikey_data,
                category=category,
                subcategory=digikey_data.family,
                component_type=self._component_type_from_prefix(prefix),
                designation_prefix=prefix
            )

            return PartImportDetail(
                part_number=digikey_data.part_number,
                device_tag=part.device_tag,
                status=ImportStatus.ADDED,
                message="Added with DigiKey data",
                digikey_url=digikey_data.product_url,
                library_id=component_id
            )
        except Exception as e:
            return PartImportDetail(
                part_number=digikey_data.part_number,
                device_tag=part.device_tag,
                status=ImportStatus.ERROR,
                message=f"Add failed: {e}"
            )

    def _determine_category(
        self,
        digikey_data: DigiKeyProductDetails
    ) -> Tuple[str, str]:
        """Map DigiKey taxonomy to our category and designation prefix."""
        # Try category first
        category_name = digikey_data.category
        if category_name in DIGIKEY_CATEGORY_MAP:
            return DIGIKEY_CATEGORY_MAP[category_name]

        # Try family
        family_name = digikey_data.family
        if family_name in DIGIKEY_CATEGORY_MAP:
            return DIGIKEY_CATEGORY_MAP[family_name]

        # Try matching keywords in description
        desc_lower = digikey_data.description.lower()
        if 'relay' in desc_lower:
            return ("Relays", "K")
        if 'contactor' in desc_lower:
            return ("Contactors", "K")
        if 'fuse' in desc_lower or 'breaker' in desc_lower:
            return ("Protection", "F")
        if 'sensor' in desc_lower or 'proximity' in desc_lower:
            return ("Sensors", "B")
        if 'switch' in desc_lower:
            return ("Switches", "S")
        if 'motor' in desc_lower:
            return ("Motors", "M")
        if 'power supply' in desc_lower or 'converter' in desc_lower:
            return ("Power Supplies", "G")
        if 'plc' in desc_lower or 'controller' in desc_lower:
            return ("PLCs", "A")

        return DIGIKEY_CATEGORY_MAP["default"]

    def _category_from_device_tag(self, device_tag: str) -> Tuple[str, str]:
        """Determine category from device tag prefix."""
        # Remove leading +/- and location prefix
        tag = device_tag.lstrip('+-')
        if '-' in tag:
            tag = tag.split('-')[-1]

        # Get first letter
        prefix = tag[0].upper() if tag else 'X'

        prefix_map = {
            'A': ('PLCs', 'A'),
            'B': ('Sensors', 'B'),
            'F': ('Protection', 'F'),
            'G': ('Power Supplies', 'G'),
            'H': ('Indicators', 'H'),
            'K': ('Relays', 'K'),
            'M': ('Motors', 'M'),
            'P': ('Indicators', 'P'),
            'Q': ('Contactors', 'Q'),
            'S': ('Switches', 'S'),
            'T': ('Transformers', 'T'),
            'U': ('Drives', 'U'),
            'V': ('Valves', 'V'),
            'X': ('Connectors', 'X'),
        }

        return prefix_map.get(prefix, ('Other', 'X'))

    def _component_type_from_prefix(self, prefix: str) -> str:
        """Get component type string from designation prefix."""
        type_map = {
            'A': 'PLC',
            'B': 'SENSOR',
            'F': 'FUSE',
            'G': 'POWER_SUPPLY',
            'H': 'INDICATOR',
            'K': 'RELAY',
            'M': 'MOTOR',
            'P': 'METER',
            'Q': 'CONTACTOR',
            'S': 'SWITCH',
            'T': 'TRANSFORMER',
            'U': 'VFD',
            'V': 'VALVE',
            'X': 'TERMINAL',
        }
        return type_map.get(prefix.upper(), 'OTHER')

    def _extract_voltage(self, technical_data: str) -> Optional[str]:
        """Extract voltage rating from technical data string."""
        import re

        # Common voltage patterns
        patterns = [
            r'(\d+)\s*VDC',
            r'(\d+)\s*VAC',
            r'(\d+)\s*V\s*DC',
            r'(\d+)\s*V\s*AC',
            r'(\d+)V',
        ]

        for pattern in patterns:
            match = re.search(pattern, technical_data, re.IGNORECASE)
            if match:
                voltage = match.group(0).replace(' ', '')
                return voltage.upper()

        return None
