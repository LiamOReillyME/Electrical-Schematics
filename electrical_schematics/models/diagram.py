"""Data model for complete wiring diagrams."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional
from electrical_schematics.models.industrial_component import IndustrialComponent, SensorState
from electrical_schematics.models.wire import Wire


@dataclass
class WiringDiagram:
    """Represents a complete industrial wiring diagram."""

    name: str
    pdf_path: Optional[Path] = None
    page_number: int = 0

    components: List[IndustrialComponent] = field(default_factory=list)
    wires: List[Wire] = field(default_factory=list)

    metadata: Dict[str, str] = field(default_factory=dict)

    def get_component(self, component_id: str) -> Optional[IndustrialComponent]:
        """Get a component by ID."""
        for comp in self.components:
            if comp.id == component_id:
                return comp
        return None

    def get_component_by_designation(self, designation: str) -> Optional[IndustrialComponent]:
        """Get a component by its designation (e.g., 'S1', 'K1')."""
        for comp in self.components:
            if comp.designation == designation:
                return comp
        return None

    def get_wires_for_component(self, component_id: str) -> List[Wire]:
        """Get all wires connected to a specific component."""
        return [wire for wire in self.wires if wire.connects_to(component_id)]

    def get_power_sources(self) -> List[IndustrialComponent]:
        """Get all power source components."""
        return [comp for comp in self.components if comp.is_power_source()]

    def get_sensors(self) -> List[IndustrialComponent]:
        """Get all sensor/switch components."""
        return [comp for comp in self.components if comp.is_sensor()]

    def set_sensor_state(self, designation: str, state: SensorState) -> bool:
        """
        Set the state of a sensor.

        Args:
            designation: Component designation (e.g., 'S1')
            state: New sensor state

        Returns:
            True if sensor was found and updated
        """
        comp = self.get_component_by_designation(designation)
        if comp and comp.is_sensor():
            comp.state = state
            return True
        return False

    def reset_all_sensor_states(self) -> None:
        """Reset all sensors to UNKNOWN state."""
        for comp in self.get_sensors():
            comp.state = SensorState.UNKNOWN

    def __str__(self) -> str:
        """String representation of the diagram."""
        return (f"Diagram '{self.name}': "
                f"{len(self.components)} components, "
                f"{len(self.wires)} wires")
