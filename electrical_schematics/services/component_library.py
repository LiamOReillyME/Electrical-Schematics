"""Component library service for managing parts and project components."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Iterator, Callable, TYPE_CHECKING

from electrical_schematics.models.library_part import LibraryPart
from electrical_schematics.models.project_component import ProjectComponent

if TYPE_CHECKING:
    from electrical_schematics.services.auto_enrichment import (
        AutoEnrichmentService,
        EnrichmentResult,
    )


logger = logging.getLogger(__name__)


@dataclass
class LibraryStats:
    """Statistics about the component library."""

    total_parts: int
    total_projects: int
    total_components: int
    parts_with_digikey: int
    parts_without_digikey: int

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "total_parts": self.total_parts,
            "total_projects": self.total_projects,
            "total_components": self.total_components,
            "parts_with_digikey": self.parts_with_digikey,
            "parts_without_digikey": self.parts_without_digikey,
        }


class ComponentLibrary:
    """Service for managing the component library and project components.

    The library maintains two separate collections:
    1. LibraryParts: Master catalog of unique parts by manufacturer part number
    2. ProjectComponents: Device tag instances specific to each schematic/PDF

    Example usage:
        library = ComponentLibrary()
        library.load()

        # Add a part to the master catalog
        part = LibraryPart(
            manufacturer_part_number="3RT2026-1DB40-1AAO",
            manufacturer="Siemens",
            description="Contactor AC-3 11KW/400V"
        )
        library.add_part(part)

        # Add a project component that references the part
        component = ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="3RT2026-1DB40-1AAO"
        )
        library.add_project_component(component)

        library.save()

    Auto-enrichment with DigiKey:
        library = ComponentLibrary()
        library.load()

        # Add part with auto-enrichment
        part = LibraryPart(manufacturer_part_number="LM7805CT")
        library.add_part(part, auto_enrich=True)  # Queries DigiKey automatically

        # Or enrich all parts that need it
        results = library.enrich_all_parts()
    """

    VERSION = "2.0"

    def __init__(
        self,
        library_path: Optional[Path] = None,
        enrichment_service: Optional["AutoEnrichmentService"] = None,
    ) -> None:
        """Initialize the component library.

        Args:
            library_path: Path to the library JSON file. If not provided,
                         uses the default location in the config directory.
            enrichment_service: Optional AutoEnrichmentService for DigiKey lookups.
                               If not provided, one will be created on demand.
        """
        if library_path is None:
            # Default to config directory
            library_path = (
                Path(__file__).parent.parent / "config" / "default_library.json"
            )
        self.library_path = library_path

        # Master catalog: part number -> LibraryPart
        self._parts: Dict[str, LibraryPart] = {}

        # Project components: project_id -> {device_tag -> ProjectComponent}
        self._projects: Dict[str, Dict[str, ProjectComponent]] = {}

        # Track if library has been modified
        self._modified = False

        # Auto-enrichment service (lazy-initialized)
        self._enrichment_service = enrichment_service
        self._enrichment_service_initialized = enrichment_service is not None

    # =========================================================================
    # Auto-Enrichment Integration
    # =========================================================================

    @property
    def enrichment_service(self) -> Optional["AutoEnrichmentService"]:
        """Get the auto-enrichment service, creating it if needed.

        Returns:
            AutoEnrichmentService instance or None if unavailable
        """
        if not self._enrichment_service_initialized:
            self._enrichment_service_initialized = True
            try:
                from electrical_schematics.services.auto_enrichment import (
                    AutoEnrichmentService,
                )
                self._enrichment_service = AutoEnrichmentService()
            except Exception as e:
                logger.warning(f"Failed to create enrichment service: {e}")
                self._enrichment_service = None

        return self._enrichment_service

    @enrichment_service.setter
    def enrichment_service(self, service: Optional["AutoEnrichmentService"]) -> None:
        """Set the auto-enrichment service.

        Args:
            service: AutoEnrichmentService instance or None
        """
        self._enrichment_service = service
        self._enrichment_service_initialized = True

    def is_enrichment_available(self) -> bool:
        """Check if auto-enrichment is available.

        Returns:
            True if enrichment service is configured and ready
        """
        service = self.enrichment_service
        return service is not None and service.is_available()

    # =========================================================================
    # Library Part Methods (Master Catalog)
    # =========================================================================

    def add_part(
        self,
        part: LibraryPart,
        auto_enrich: bool = False,
    ) -> bool:
        """Add a part to the master catalog.

        If a part with the same manufacturer part number already exists,
        it will be updated with the new data.

        Args:
            part: The LibraryPart to add
            auto_enrich: If True and part hasn't been looked up yet,
                        automatically query DigiKey for additional data

        Returns:
            True if the part was added (new), False if it was updated
        """
        key = part.manufacturer_part_number
        is_new = key not in self._parts

        if not is_new:
            # Preserve existing DigiKey data if available
            existing = self._parts[key]
            if existing.digikey_lookup_success and not part.digikey_lookup_success:
                part.digikey_part_number = existing.digikey_part_number
                part.digikey_description = existing.digikey_description
                part.digikey_url = existing.digikey_url
                part.datasheet_url = existing.datasheet_url
                part.image_url = existing.image_url
                part.unit_price = existing.unit_price
                part.stock_quantity = existing.stock_quantity
                part.parameters = existing.parameters
                part.digikey_lookup_attempted = existing.digikey_lookup_attempted
                part.digikey_lookup_success = existing.digikey_lookup_success

            # Preserve created_at
            part.created_at = existing.created_at

        # Auto-enrich if requested and not already attempted
        if auto_enrich and not part.digikey_lookup_attempted:
            self._enrich_part(part)

        part.updated_at = datetime.now()
        self._parts[key] = part
        self._modified = True

        logger.debug(f"{'Added' if is_new else 'Updated'} part: {key}")
        return is_new

    def _enrich_part(self, part: LibraryPart) -> Optional["EnrichmentResult"]:
        """Internal method to enrich a single part.

        Args:
            part: The part to enrich

        Returns:
            EnrichmentResult or None if service unavailable
        """
        service = self.enrichment_service
        if service and service.is_available():
            return service.enrich_part(part)
        return None

    def enrich_part(
        self,
        manufacturer_part_number: str,
        force: bool = False,
    ) -> Optional["EnrichmentResult"]:
        """Enrich a specific part with DigiKey data.

        Args:
            manufacturer_part_number: The part number to enrich
            force: If True, re-enrich even if already attempted

        Returns:
            EnrichmentResult or None if part not found or service unavailable
        """
        part = self.get_part(manufacturer_part_number)
        if not part:
            logger.warning(f"Part not found: {manufacturer_part_number}")
            return None

        service = self.enrichment_service
        if not service or not service.is_available():
            logger.warning("Enrichment service not available")
            return None

        result = service.enrich_part(part, force=force)
        if result and result.success:
            self._modified = True

        return result

    def enrich_all_parts(
        self,
        force: bool = False,
        progress_callback: Optional[Callable[[int, int, "EnrichmentResult"], None]] = None,
    ) -> List["EnrichmentResult"]:
        """Enrich all parts that need DigiKey lookup.

        Args:
            force: If True, re-enrich all parts regardless of previous attempts
            progress_callback: Optional callback(current, total, result) for progress

        Returns:
            List of EnrichmentResults for each part processed
        """
        service = self.enrichment_service
        if not service or not service.is_available():
            logger.warning("Enrichment service not available")
            return []

        if force:
            parts = self.get_all_parts()
        else:
            parts = self.get_parts_needing_digikey_lookup()

        if not parts:
            logger.info("No parts need enrichment")
            return []

        results = service.enrich_parts_batch(
            parts=parts,
            force=force,
            progress_callback=progress_callback,
        )

        # Mark modified if any enrichment succeeded
        if any(r.success for r in results):
            self._modified = True

        return results

    def get_part(self, manufacturer_part_number: str) -> Optional[LibraryPart]:
        """Get a part from the master catalog.

        Args:
            manufacturer_part_number: The part number to look up

        Returns:
            The LibraryPart if found, None otherwise
        """
        key = manufacturer_part_number.strip().upper()
        return self._parts.get(key)

    def part_exists(self, manufacturer_part_number: str) -> bool:
        """Check if a part exists in the master catalog.

        Args:
            manufacturer_part_number: The part number to check

        Returns:
            True if the part exists, False otherwise
        """
        key = manufacturer_part_number.strip().upper()
        return key in self._parts

    def remove_part(self, manufacturer_part_number: str) -> bool:
        """Remove a part from the master catalog.

        Note: This will NOT remove ProjectComponents that reference this part.

        Args:
            manufacturer_part_number: The part number to remove

        Returns:
            True if the part was removed, False if it wasn't found
        """
        key = manufacturer_part_number.strip().upper()
        if key in self._parts:
            del self._parts[key]
            self._modified = True
            logger.debug(f"Removed part: {key}")
            return True
        return False

    def get_all_parts(self) -> List[LibraryPart]:
        """Get all parts in the master catalog.

        Returns:
            List of all LibraryPart objects
        """
        return list(self._parts.values())

    def iter_parts(self) -> Iterator[LibraryPart]:
        """Iterate over all parts in the master catalog.

        Yields:
            LibraryPart objects
        """
        yield from self._parts.values()

    def search_parts(
        self,
        query: str,
        search_fields: Optional[List[str]] = None,
    ) -> List[LibraryPart]:
        """Search for parts matching a query.

        Args:
            query: Search query (case-insensitive)
            search_fields: Fields to search in. Default: part number,
                          manufacturer, description

        Returns:
            List of matching LibraryPart objects
        """
        if not query:
            return self.get_all_parts()

        query = query.lower()
        if search_fields is None:
            search_fields = ["manufacturer_part_number", "manufacturer", "description"]

        results = []
        for part in self._parts.values():
            for field in search_fields:
                value = getattr(part, field, "")
                if value and query in value.lower():
                    results.append(part)
                    break

        return results

    def get_parts_needing_digikey_lookup(self) -> List[LibraryPart]:
        """Get all parts that haven't had a DigiKey lookup attempted.

        Returns:
            List of LibraryPart objects needing lookup
        """
        return [
            part
            for part in self._parts.values()
            if not part.digikey_lookup_attempted
        ]

    # =========================================================================
    # Project Component Methods (Schematic Instances)
    # =========================================================================

    def add_project_component(self, component: ProjectComponent) -> bool:
        """Add a project component (device tag instance).

        If a component with the same project_id and device_tag exists,
        it will be updated.

        Args:
            component: The ProjectComponent to add

        Returns:
            True if the component was added (new), False if updated
        """
        project_id = component.project_id
        device_tag = component.device_tag

        # Initialize project dict if needed
        if project_id not in self._projects:
            self._projects[project_id] = {}

        is_new = device_tag not in self._projects[project_id]

        if not is_new:
            # Preserve created_at
            existing = self._projects[project_id][device_tag]
            component.created_at = existing.created_at

        component.updated_at = datetime.now()
        self._projects[project_id][device_tag] = component
        self._modified = True

        logger.debug(
            f"{'Added' if is_new else 'Updated'} component: "
            f"{project_id}::{device_tag}"
        )
        return is_new

    def get_project_component(
        self, project_id: str, device_tag: str
    ) -> Optional[ProjectComponent]:
        """Get a specific project component.

        Args:
            project_id: The project/PDF identifier
            device_tag: The device tag (e.g., "-K1")

        Returns:
            The ProjectComponent if found, None otherwise
        """
        project_dict = self._projects.get(project_id)
        if project_dict:
            return project_dict.get(device_tag)
        return None

    def get_project_components(self, project_id: str) -> List[ProjectComponent]:
        """Get all components for a project.

        Args:
            project_id: The project/PDF identifier

        Returns:
            List of ProjectComponent objects for the project
        """
        project_dict = self._projects.get(project_id, {})
        return list(project_dict.values())

    def remove_project_component(self, project_id: str, device_tag: str) -> bool:
        """Remove a project component.

        Args:
            project_id: The project/PDF identifier
            device_tag: The device tag to remove

        Returns:
            True if removed, False if not found
        """
        project_dict = self._projects.get(project_id)
        if project_dict and device_tag in project_dict:
            del project_dict[device_tag]
            self._modified = True
            logger.debug(f"Removed component: {project_id}::{device_tag}")
            return True
        return False

    def remove_project(self, project_id: str) -> bool:
        """Remove all components for a project.

        Args:
            project_id: The project/PDF identifier

        Returns:
            True if project was removed, False if not found
        """
        if project_id in self._projects:
            del self._projects[project_id]
            self._modified = True
            logger.debug(f"Removed project: {project_id}")
            return True
        return False

    def get_all_projects(self) -> List[str]:
        """Get all project IDs.

        Returns:
            List of project identifiers
        """
        return list(self._projects.keys())

    def get_components_for_part(
        self, manufacturer_part_number: str
    ) -> List[ProjectComponent]:
        """Get all project components that reference a specific part.

        Args:
            manufacturer_part_number: The part number to search for

        Returns:
            List of ProjectComponent objects referencing this part
        """
        key = manufacturer_part_number.strip().upper()
        results = []

        for project_dict in self._projects.values():
            for component in project_dict.values():
                if component.manufacturer_part_number == key:
                    results.append(component)

        return results

    # =========================================================================
    # Combined Operations
    # =========================================================================

    def get_part_with_usage(
        self, manufacturer_part_number: str
    ) -> tuple[Optional[LibraryPart], List[ProjectComponent]]:
        """Get a part and all components that use it.

        Args:
            manufacturer_part_number: The part number to look up

        Returns:
            Tuple of (LibraryPart or None, list of ProjectComponents)
        """
        part = self.get_part(manufacturer_part_number)
        components = self.get_components_for_part(manufacturer_part_number)
        return part, components

    def get_component_with_part(
        self, project_id: str, device_tag: str
    ) -> tuple[Optional[ProjectComponent], Optional[LibraryPart]]:
        """Get a project component and its associated library part.

        Args:
            project_id: The project/PDF identifier
            device_tag: The device tag

        Returns:
            Tuple of (ProjectComponent or None, LibraryPart or None)
        """
        component = self.get_project_component(project_id, device_tag)
        part = None
        if component:
            part = self.get_part(component.manufacturer_part_number)
        return component, part

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> LibraryStats:
        """Get statistics about the library.

        Returns:
            LibraryStats object with counts
        """
        total_components = sum(
            len(project_dict) for project_dict in self._projects.values()
        )
        parts_with_digikey = sum(
            1 for part in self._parts.values() if part.digikey_lookup_success
        )

        return LibraryStats(
            total_parts=len(self._parts),
            total_projects=len(self._projects),
            total_components=total_components,
            parts_with_digikey=parts_with_digikey,
            parts_without_digikey=len(self._parts) - parts_with_digikey,
        )

    # =========================================================================
    # Persistence
    # =========================================================================

    def save(self, path: Optional[Path] = None) -> None:
        """Save the library to a JSON file.

        Args:
            path: Path to save to. Uses default path if not provided.
        """
        if path is None:
            path = self.library_path

        data = {
            "version": self.VERSION,
            "description": "Component library with master catalog and project components",
            "library_parts": [part.to_dict() for part in self._parts.values()],
            "projects": {
                project_id: {
                    device_tag: component.to_dict()
                    for device_tag, component in components.items()
                }
                for project_id, components in self._projects.items()
            },
        }

        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self._modified = False
        logger.info(f"Saved library to {path}")

    def load(self, path: Optional[Path] = None) -> None:
        """Load the library from a JSON file.

        Args:
            path: Path to load from. Uses default path if not provided.
        """
        if path is None:
            path = self.library_path

        if not path.exists():
            logger.info(f"Library file not found at {path}, starting with empty library")
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        version = data.get("version", "1.0")
        was_migrated = False

        if version == "1.0":
            # Migrate from old format
            self._migrate_v1_to_v2(data)
            was_migrated = True
        elif version == "2.0":
            self._load_v2(data)
        else:
            logger.warning(f"Unknown library version: {version}, attempting to load")
            self._load_v2(data)

        # Only clear modified flag if we didn't migrate
        # Migration sets modified=True so it gets saved in new format
        if not was_migrated:
            self._modified = False

        logger.info(f"Loaded library from {path}")

    def _load_v2(self, data: Dict[str, Any]) -> None:
        """Load version 2.0 format data.

        Args:
            data: Parsed JSON data
        """
        # Load library parts
        self._parts.clear()
        for part_data in data.get("library_parts", []):
            part = LibraryPart.from_dict(part_data)
            self._parts[part.manufacturer_part_number] = part

        # Load project components
        self._projects.clear()
        for project_id, components_data in data.get("projects", {}).items():
            self._projects[project_id] = {}
            for device_tag, component_data in components_data.items():
                component = ProjectComponent.from_dict(component_data)
                self._projects[project_id][device_tag] = component

    def _migrate_v1_to_v2(self, data: Dict[str, Any]) -> None:
        """Migrate version 1.0 format to 2.0.

        Version 1.0 had a flat "components" list with mixed data.

        Args:
            data: Parsed JSON data in v1.0 format
        """
        logger.info("Migrating library from v1.0 to v2.0 format")

        self._parts.clear()
        self._projects.clear()

        # Old format had a flat "components" list
        for old_component in data.get("components", []):
            # Try to extract part number from the old data
            part_number = old_component.get(
                "manufacturer_part_number",
                old_component.get("part_number", ""),
            )

            if part_number:
                # Create library part if we have a part number
                part = LibraryPart(
                    manufacturer_part_number=part_number,
                    manufacturer=old_component.get("manufacturer", ""),
                    description=old_component.get("description", ""),
                    technical_data=old_component.get("technical_data", ""),
                    voltage_rating=old_component.get("voltage_rating", ""),
                )

                # Migrate DigiKey data if present
                if old_component.get("digikey_part_number"):
                    part.digikey_part_number = old_component["digikey_part_number"]
                    part.digikey_lookup_attempted = True
                    part.digikey_lookup_success = True

                self._parts[part.manufacturer_part_number] = part

        # Mark as modified so it gets saved in new format
        self._modified = True

    @property
    def is_modified(self) -> bool:
        """Check if the library has been modified since last save/load."""
        return self._modified

    def clear(self) -> None:
        """Clear all data from the library."""
        self._parts.clear()
        self._projects.clear()
        self._modified = True
        logger.info("Cleared library")
