"""Data models for connections between components."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Pin:
    """Represents a pin on a component."""

    component_id: str
    pin_number: str
    pin_name: Optional[str] = None
    x: float = 0.0
    y: float = 0.0


@dataclass
class Connection:
    """Represents a connection (wire/net) between pins."""

    id: str
    from_pin: Pin
    to_pin: Pin
    net_name: Optional[str] = None

    def __str__(self) -> str:
        """String representation of the connection."""
        net = f" [{self.net_name}]" if self.net_name else ""
        return f"{self.from_pin.component_id}.{self.from_pin.pin_number} -> {self.to_pin.component_id}.{self.to_pin.pin_number}{net}"
