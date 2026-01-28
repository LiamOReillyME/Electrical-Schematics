"""Data model for project components (schematic instances)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class ProjectComponent:
    """An instance of a part used in a specific project/schematic.

    Represents a device tag in a schematic that references a LibraryPart.
    The same physical part (LibraryPart) can appear multiple times in the
    same schematic with different device tags, or in different schematics.

    Example:
        Project "DRAWER.pdf" has:
        - "-K1" -> references "3RT2026-1DB40-1AAO" (contactor)
        - "-K2" -> references "3RT2026-1DB40-1AAO" (same contactor model)
        - "-U1" -> references "6SL3210-1PE21-8AL0" (VFD)

        A different project "MACHINE_B.pdf" might have:
        - "-K5" -> references "3RT2026-1DB40-1AAO" (same contactor)
    """

    # Project reference (required)
    project_id: str  # PDF filename or project identifier, e.g., "DRAWER.pdf"

    # Device tag - specific to this schematic (required)
    device_tag: str  # e.g., "-K1", "-U1", "+DG-M1"

    # Reference to library part (required)
    manufacturer_part_number: str  # Links to LibraryPart

    # Position in PDF (primary position)
    page: int = 0
    x: float = 0.0
    y: float = 0.0
    width: float = 40.0
    height: float = 30.0

    # Additional positions (for components appearing on multiple pages)
    additional_positions: List[Dict[str, Any]] = field(default_factory=list)

    # Schematic-specific info (may differ from library part)
    designation: str = ""  # What the PDF calls it, e.g., "Main Contactor"
    technical_data: str = ""  # Tech data from this specific PDF
    function_description: str = ""  # What it does in this circuit

    # Circuit classification
    circuit_type: str = ""  # e.g., "control", "power", "signal"
    voltage_level: str = ""  # e.g., "24VDC", "400VAC" (for this circuit)

    # Terminal/connection info specific to this schematic
    terminal_assignments: Dict[str, str] = field(default_factory=dict)
    # e.g., {"A1": "+24V", "A2": "0V", "13-14": "K2 coil"}

    # Wire connections (references to wires in the schematic)
    connected_wires: List[str] = field(default_factory=list)

    # State tracking for simulation
    initial_state: str = "unknown"  # Default state when simulation starts

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.project_id:
            raise ValueError("project_id is required")
        if not self.device_tag:
            raise ValueError("device_tag is required")
        if not self.manufacturer_part_number:
            raise ValueError("manufacturer_part_number is required")

        # Normalize device tag (preserve case as industrial tags use specific formats)
        self.device_tag = self.device_tag.strip()

        # Normalize part number
        self.manufacturer_part_number = self.manufacturer_part_number.strip().upper()

    def add_position(
        self,
        page: int,
        x: float,
        y: float,
        width: float = 40.0,
        height: float = 30.0,
        confidence: float = 1.0,
    ) -> None:
        """Add an additional position for this component.

        Used when the component appears on multiple pages.

        Args:
            page: PDF page number (0-indexed)
            x: X coordinate in PDF points
            y: Y coordinate in PDF points
            width: Width in PDF points
            height: Height in PDF points
            confidence: Detection confidence (0.0 to 1.0)
        """
        position = {
            "page": page,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "confidence": confidence,
        }
        self.additional_positions.append(position)
        self.updated_at = datetime.now()

    def get_all_pages(self) -> List[int]:
        """Get all pages where this component appears.

        Returns:
            List of page numbers (0-indexed), sorted
        """
        pages = {self.page} if self.x != 0.0 or self.y != 0.0 else set()
        for pos in self.additional_positions:
            pages.add(pos["page"])
        return sorted(pages)

    def get_position_for_page(self, page: int) -> Optional[Dict[str, Any]]:
        """Get the position of this component on a specific page.

        Args:
            page: PDF page number (0-indexed)

        Returns:
            Position dict if found, None otherwise
        """
        # Check primary position
        if page == self.page and (self.x != 0.0 or self.y != 0.0):
            return {
                "page": self.page,
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
                "confidence": 1.0,
            }

        # Check additional positions
        for pos in self.additional_positions:
            if pos["page"] == page:
                return pos

        return None

    def assign_terminal(self, terminal: str, connection: str) -> None:
        """Assign a connection to a terminal.

        Args:
            terminal: Terminal identifier (e.g., "A1", "13-14")
            connection: What's connected (e.g., "+24V", "K2 coil")
        """
        self.terminal_assignments[terminal] = connection
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the component
        """
        return {
            "project_id": self.project_id,
            "device_tag": self.device_tag,
            "manufacturer_part_number": self.manufacturer_part_number,
            "page": self.page,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "additional_positions": self.additional_positions,
            "designation": self.designation,
            "technical_data": self.technical_data,
            "function_description": self.function_description,
            "circuit_type": self.circuit_type,
            "voltage_level": self.voltage_level,
            "terminal_assignments": self.terminal_assignments,
            "connected_wires": self.connected_wires,
            "initial_state": self.initial_state,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectComponent":
        """Create a ProjectComponent from a dictionary.

        Args:
            data: Dictionary with component data

        Returns:
            ProjectComponent instance
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
            project_id=data["project_id"],
            device_tag=data["device_tag"],
            manufacturer_part_number=data["manufacturer_part_number"],
            page=data.get("page", 0),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            width=data.get("width", 40.0),
            height=data.get("height", 30.0),
            additional_positions=data.get("additional_positions", []),
            designation=data.get("designation", ""),
            technical_data=data.get("technical_data", ""),
            function_description=data.get("function_description", ""),
            circuit_type=data.get("circuit_type", ""),
            voltage_level=data.get("voltage_level", ""),
            terminal_assignments=data.get("terminal_assignments", {}),
            connected_wires=data.get("connected_wires", []),
            initial_state=data.get("initial_state", "unknown"),
            created_at=created_at,
            updated_at=updated_at,
            notes=data.get("notes", ""),
        )

    def get_unique_id(self) -> str:
        """Get a unique identifier for this component within the library.

        Returns:
            Unique ID combining project and device tag
        """
        return f"{self.project_id}::{self.device_tag}"

    def __str__(self) -> str:
        """String representation of the component."""
        parts = [f"{self.device_tag}"]
        if self.designation:
            parts.append(f"({self.designation})")
        parts.append(f"-> {self.manufacturer_part_number}")
        if self.circuit_type:
            parts.append(f"[{self.circuit_type}]")
        return " ".join(parts)

    def __eq__(self, other: object) -> bool:
        """Check equality based on project_id and device_tag."""
        if not isinstance(other, ProjectComponent):
            return False
        return (
            self.project_id == other.project_id
            and self.device_tag == other.device_tag
        )

    def __hash__(self) -> int:
        """Hash based on project_id and device_tag."""
        return hash((self.project_id, self.device_tag))
