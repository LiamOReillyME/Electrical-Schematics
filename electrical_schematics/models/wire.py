"""Data models for wires and connections."""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class WirePoint:
    """A point in a wire path."""
    x: float
    y: float


@dataclass
class Wire:
    """Represents a wire connection between components or terminals."""

    id: str
    wire_number: Optional[str] = None  # e.g., "W1", "24V+"
    voltage_level: Optional[str] = None  # e.g., "24VDC", "400VAC"
    color: Optional[str] = None  # Wire color from diagram

    # Connection points
    from_component_id: Optional[str] = None
    from_terminal: Optional[str] = None
    to_component_id: Optional[str] = None
    to_terminal: Optional[str] = None

    # Visual path in PDF
    path: List[WirePoint] = None

    # Current voltage state (for simulation)
    is_energized: bool = False
    current_voltage: Optional[float] = None

    def __post_init__(self) -> None:
        """Initialize mutable defaults."""
        if self.path is None:
            self.path = []

    def connects_to(self, component_id: str) -> bool:
        """Check if wire connects to a specific component."""
        return (self.from_component_id == component_id or
                self.to_component_id == component_id)

    def __str__(self) -> str:
        """String representation of the wire."""
        wire_num = f"[{self.wire_number}]" if self.wire_number else ""
        from_str = f"{self.from_component_id}"
        if self.from_terminal:
            from_str += f".{self.from_terminal}"
        to_str = f"{self.to_component_id}"
        if self.to_terminal:
            to_str += f".{self.to_terminal}"

        return f"{wire_num} {from_str} -> {to_str}"
