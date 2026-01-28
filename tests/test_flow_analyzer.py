"""Tests for flow analyzer."""

import pytest
from electrical_schematics.models import (
    Schematic, Component, ComponentType, Connection, Pin
)
from electrical_schematics.analysis import FlowAnalyzer


def test_flow_analyzer_initialization() -> None:
    """Test initializing the flow analyzer."""
    schematic = Schematic(name="test")
    analyzer = FlowAnalyzer(schematic)

    assert analyzer.schematic == schematic
    assert analyzer.graph is not None


def test_find_power_sources() -> None:
    """Test finding power sources in a schematic."""
    schematic = Schematic(name="test")
    schematic.components.append(
        Component(id="VCC", type=ComponentType.POWER_SOURCE)
    )
    schematic.components.append(
        Component(id="R1", type=ComponentType.RESISTOR)
    )

    analyzer = FlowAnalyzer(schematic)
    sources = analyzer.find_power_sources()

    assert len(sources) == 1
    assert sources[0].id == "VCC"


def test_find_signal_path() -> None:
    """Test finding a signal path between components."""
    schematic = Schematic(name="test")

    # Create components
    r1 = Component(id="R1", type=ComponentType.RESISTOR)
    r2 = Component(id="R2", type=ComponentType.RESISTOR)
    r3 = Component(id="R3", type=ComponentType.RESISTOR)

    schematic.components.extend([r1, r2, r3])

    # Create connections R1 -> R2 -> R3
    conn1 = Connection(
        id="c1",
        from_pin=Pin("R1", "2"),
        to_pin=Pin("R2", "1")
    )
    conn2 = Connection(
        id="c2",
        from_pin=Pin("R2", "2"),
        to_pin=Pin("R3", "1")
    )

    schematic.connections.extend([conn1, conn2])

    analyzer = FlowAnalyzer(schematic)
    path = analyzer.find_signal_path("R1", "R3")

    assert path == ["R1", "R2", "R3"]
