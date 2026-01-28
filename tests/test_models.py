"""Tests for data models."""

import pytest
from electrical_schematics.models import Component, ComponentType, Connection, Pin, Schematic


def test_component_creation() -> None:
    """Test creating a component."""
    comp = Component(
        id="R1",
        type=ComponentType.RESISTOR,
        value="10k",
        reference="R1"
    )
    assert comp.id == "R1"
    assert comp.type == ComponentType.RESISTOR
    assert comp.value == "10k"
    assert str(comp) == "R1: resistor (10k)"


def test_connection_creation() -> None:
    """Test creating a connection."""
    pin1 = Pin(component_id="R1", pin_number="1")
    pin2 = Pin(component_id="C1", pin_number="1")
    conn = Connection(id="net1", from_pin=pin1, to_pin=pin2, net_name="VCC")

    assert conn.from_pin.component_id == "R1"
    assert conn.to_pin.component_id == "C1"
    assert conn.net_name == "VCC"


def test_schematic_get_component() -> None:
    """Test getting a component from a schematic."""
    schematic = Schematic(name="test")
    comp = Component(id="R1", type=ComponentType.RESISTOR)
    schematic.components.append(comp)

    found = schematic.get_component("R1")
    assert found is not None
    assert found.id == "R1"

    not_found = schematic.get_component("R2")
    assert not_found is None
