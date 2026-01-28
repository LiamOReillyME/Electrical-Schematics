"""Data models for electrical components."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ComponentType(Enum):
    """Types of electrical components."""
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    DIODE = "diode"
    TRANSISTOR = "transistor"
    IC = "integrated_circuit"
    CONNECTOR = "connector"
    SWITCH = "switch"
    RELAY = "relay"
    FUSE = "fuse"
    POWER_SOURCE = "power_source"
    GROUND = "ground"
    OTHER = "other"


@dataclass
class Component:
    """Represents an electrical component in a schematic."""

    id: str
    type: ComponentType
    value: Optional[str] = None
    reference: Optional[str] = None  # e.g., "R1", "C2"
    description: Optional[str] = None
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0

    def __str__(self) -> str:
        """String representation of the component."""
        ref = self.reference or self.id
        val = f" ({self.value})" if self.value else ""
        return f"{ref}: {self.type.value}{val}"
