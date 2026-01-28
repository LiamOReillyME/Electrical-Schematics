"""Data models for electrical schematics."""

from electrical_schematics.models.industrial_component import (
    IndustrialComponent,
    IndustrialComponentType,
    SensorState,
    ContactType,
    ContactBlock,
    CoilTerminals,
    PagePosition
)
from electrical_schematics.models.wire import Wire, WirePoint
from electrical_schematics.models.diagram import WiringDiagram

# New data model for library separation
from electrical_schematics.models.library_part import LibraryPart
from electrical_schematics.models.project_component import ProjectComponent

# Terminal strips/blocks
from electrical_schematics.models.terminal_strip import (
    TerminalStrip,
    TerminalStripType,
    TerminalColor,
    TerminalPosition
)

# Legacy imports for backwards compatibility
from electrical_schematics.models.component import Component, ComponentType
from electrical_schematics.models.connection import Connection, Pin
from electrical_schematics.models.schematic import Schematic

__all__ = [
    # Industrial components (current)
    "IndustrialComponent",
    "IndustrialComponentType",
    "SensorState",
    "ContactType",
    "ContactBlock",
    "CoilTerminals",
    "PagePosition",
    "Wire",
    "WirePoint",
    "WiringDiagram",
    # Library separation (new)
    "LibraryPart",
    "ProjectComponent",
    # Terminal strips
    "TerminalStrip",
    "TerminalStripType",
    "TerminalColor",
    "TerminalPosition",
    # Legacy
    "Component",
    "ComponentType",
    "Connection",
    "Pin",
    "Schematic",
]
