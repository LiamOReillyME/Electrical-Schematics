"""Data model for complete schematics."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from electrical_schematics.models.component import Component
from electrical_schematics.models.connection import Connection


@dataclass
class Schematic:
    """Represents a complete electrical schematic."""

    name: str
    components: List[Component] = field(default_factory=list)
    connections: List[Connection] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

    def get_component(self, component_id: str) -> Optional[Component]:
        """Get a component by ID."""
        for comp in self.components:
            if comp.id == component_id:
                return comp
        return None

    def get_connections_for_component(self, component_id: str) -> List[Connection]:
        """Get all connections involving a specific component."""
        return [
            conn for conn in self.connections
            if conn.from_pin.component_id == component_id
            or conn.to_pin.component_id == component_id
        ]

    def __str__(self) -> str:
        """String representation of the schematic."""
        return f"Schematic '{self.name}': {len(self.components)} components, {len(self.connections)} connections"
