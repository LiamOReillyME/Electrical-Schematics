"""Data model for library parts (master catalog)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class LibraryPart:
    """A unique part in the master component library.

    Represents a physical part identified by its manufacturer part number.
    This is the master record that can be referenced by multiple ProjectComponent
    instances across different schematics.

    Example:
        A Siemens contactor "3RT2026-1DB40-1AAO" is stored once in the library,
        even if it appears as -K1 in one schematic and -K5 in another.
    """

    # Primary identifier - manufacturer part number (required, unique)
    manufacturer_part_number: str  # e.g., "3RT2026-1DB40-1AAO"

    # Basic info
    manufacturer: str = ""  # e.g., "Siemens"
    description: str = ""  # e.g., "Contactor AC-3 11KW/400V"
    category: str = ""  # e.g., "Contactors"
    subcategory: str = ""  # e.g., "AC Contactors"

    # Technical specifications from PDF
    technical_data: str = ""  # Raw tech data from PDF
    voltage_rating: str = ""  # e.g., "400VAC", "24VDC"
    current_rating: str = ""  # e.g., "16A", "25A"
    power_rating: str = ""  # e.g., "11kW"

    # Component classification (maps to IndustrialComponentType)
    component_type: str = ""  # e.g., "contactor", "relay", "motor"

    # DigiKey data (auto-populated from API)
    digikey_part_number: Optional[str] = None
    digikey_description: Optional[str] = None
    digikey_url: Optional[str] = None
    datasheet_url: Optional[str] = None
    image_url: Optional[str] = None
    unit_price: Optional[float] = None
    stock_quantity: Optional[int] = None

    # Extended specifications from DigiKey API
    parameters: Dict[str, str] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    digikey_lookup_attempted: bool = False
    digikey_lookup_success: bool = False

    # Custom tags/notes
    tags: list = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate and normalize the part number."""
        if not self.manufacturer_part_number:
            raise ValueError("manufacturer_part_number is required")
        # Normalize part number: strip whitespace, uppercase
        self.manufacturer_part_number = self.manufacturer_part_number.strip().upper()

    def update_from_digikey(self, digikey_data: Dict[str, Any]) -> None:
        """Update part with data from DigiKey API response.

        Args:
            digikey_data: Dictionary containing DigiKey API response fields
        """
        self.digikey_lookup_attempted = True

        if not digikey_data:
            self.digikey_lookup_success = False
            return

        self.digikey_lookup_success = True
        self.digikey_part_number = digikey_data.get("digi_key_part_number")
        self.digikey_description = digikey_data.get("product_description")
        self.digikey_url = digikey_data.get("product_url")
        self.datasheet_url = digikey_data.get("datasheet_url")
        self.image_url = digikey_data.get("primary_photo")

        # Parse pricing
        if "unit_price" in digikey_data:
            try:
                self.unit_price = float(digikey_data["unit_price"])
            except (ValueError, TypeError):
                pass

        # Parse stock
        if "quantity_available" in digikey_data:
            try:
                self.stock_quantity = int(digikey_data["quantity_available"])
            except (ValueError, TypeError):
                pass

        # Store parameters
        if "parameters" in digikey_data:
            for param in digikey_data["parameters"]:
                param_name = param.get("parameter_name", "")
                param_value = param.get("value", "")
                if param_name and param_value:
                    self.parameters[param_name] = param_value

        # Update manufacturer if not set
        if not self.manufacturer and "manufacturer" in digikey_data:
            manufacturer = digikey_data["manufacturer"]
            if isinstance(manufacturer, dict):
                self.manufacturer = manufacturer.get("name", "")
            else:
                self.manufacturer = str(manufacturer)

        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the part
        """
        return {
            "manufacturer_part_number": self.manufacturer_part_number,
            "manufacturer": self.manufacturer,
            "description": self.description,
            "category": self.category,
            "subcategory": self.subcategory,
            "technical_data": self.technical_data,
            "voltage_rating": self.voltage_rating,
            "current_rating": self.current_rating,
            "power_rating": self.power_rating,
            "component_type": self.component_type,
            "digikey_part_number": self.digikey_part_number,
            "digikey_description": self.digikey_description,
            "digikey_url": self.digikey_url,
            "datasheet_url": self.datasheet_url,
            "image_url": self.image_url,
            "unit_price": self.unit_price,
            "stock_quantity": self.stock_quantity,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "digikey_lookup_attempted": self.digikey_lookup_attempted,
            "digikey_lookup_success": self.digikey_lookup_success,
            "tags": self.tags,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LibraryPart":
        """Create a LibraryPart from a dictionary.

        Args:
            data: Dictionary with part data

        Returns:
            LibraryPart instance
        """
        # Parse datetime fields
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now()

        return cls(
            manufacturer_part_number=data["manufacturer_part_number"],
            manufacturer=data.get("manufacturer", ""),
            description=data.get("description", ""),
            category=data.get("category", ""),
            subcategory=data.get("subcategory", ""),
            technical_data=data.get("technical_data", ""),
            voltage_rating=data.get("voltage_rating", ""),
            current_rating=data.get("current_rating", ""),
            power_rating=data.get("power_rating", ""),
            component_type=data.get("component_type", ""),
            digikey_part_number=data.get("digikey_part_number"),
            digikey_description=data.get("digikey_description"),
            digikey_url=data.get("digikey_url"),
            datasheet_url=data.get("datasheet_url"),
            image_url=data.get("image_url"),
            unit_price=data.get("unit_price"),
            stock_quantity=data.get("stock_quantity"),
            parameters=data.get("parameters", {}),
            created_at=created_at,
            updated_at=updated_at,
            digikey_lookup_attempted=data.get("digikey_lookup_attempted", False),
            digikey_lookup_success=data.get("digikey_lookup_success", False),
            tags=data.get("tags", []),
            notes=data.get("notes", ""),
        )

    def get_display_name(self) -> str:
        """Get a human-readable display name for the part.

        Returns:
            Display name combining manufacturer and part number
        """
        if self.manufacturer:
            return f"{self.manufacturer} {self.manufacturer_part_number}"
        return self.manufacturer_part_number

    def __str__(self) -> str:
        """String representation of the part."""
        parts = [self.manufacturer_part_number]
        if self.manufacturer:
            parts.append(f"({self.manufacturer})")
        if self.description:
            parts.append(f"- {self.description}")
        return " ".join(parts)

    def __eq__(self, other: object) -> bool:
        """Check equality based on manufacturer part number."""
        if not isinstance(other, LibraryPart):
            return False
        return self.manufacturer_part_number == other.manufacturer_part_number

    def __hash__(self) -> int:
        """Hash based on manufacturer part number."""
        return hash(self.manufacturer_part_number)
