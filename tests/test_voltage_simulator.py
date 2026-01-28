"""Tests for voltage flow simulator."""

import pytest
from electrical_schematics.models import (
    WiringDiagram,
    IndustrialComponent,
    IndustrialComponentType,
    SensorState,
    Wire
)
from electrical_schematics.simulation import VoltageSimulator


def test_simple_voltage_flow() -> None:
    """Test voltage flow through a simple circuit."""
    diagram = WiringDiagram(name="test")

    # Create circuit: 24V -> S1 (ON) -> M1
    power = IndustrialComponent(
        id="PS1",
        type=IndustrialComponentType.POWER_24VDC,
        designation="24V+"
    )
    sensor = IndustrialComponent(
        id="S1",
        type=IndustrialComponentType.PROXIMITY_SENSOR,
        designation="S1",
        state=SensorState.ON,
        normally_open=True
    )
    motor = IndustrialComponent(
        id="M1",
        type=IndustrialComponentType.MOTOR,
        designation="M1"
    )

    diagram.components.extend([power, sensor, motor])

    # Create connections
    wire1 = Wire(id="W1", from_component_id="PS1", to_component_id="S1")
    wire2 = Wire(id="W2", from_component_id="S1", to_component_id="M1")
    diagram.wires.extend([wire1, wire2])

    # Simulate
    simulator = VoltageSimulator(diagram)
    energized = simulator.simulate()

    # All components should be energized
    assert energized.get("PS1", False)
    assert energized.get("S1", False)
    assert energized.get("M1", False)


def test_blocked_voltage_flow() -> None:
    """Test voltage flow blocked by OFF sensor."""
    diagram = WiringDiagram(name="test")

    # Create circuit: 24V -> S1 (OFF) -> M1
    power = IndustrialComponent(
        id="PS1",
        type=IndustrialComponentType.POWER_24VDC,
        designation="24V+"
    )
    sensor = IndustrialComponent(
        id="S1",
        type=IndustrialComponentType.PROXIMITY_SENSOR,
        designation="S1",
        state=SensorState.OFF,
        normally_open=True
    )
    motor = IndustrialComponent(
        id="M1",
        type=IndustrialComponentType.MOTOR,
        designation="M1"
    )

    diagram.components.extend([power, sensor, motor])

    wire1 = Wire(id="W1", from_component_id="PS1", to_component_id="S1")
    wire2 = Wire(id="W2", from_component_id="S1", to_component_id="M1")
    diagram.wires.extend([wire1, wire2])

    # Simulate
    simulator = VoltageSimulator(diagram)
    energized = simulator.simulate()

    # Power and sensor should be in graph, but motor should not be energized
    assert energized.get("PS1", False)
    # Motor should not be energized due to OFF sensor
    assert not energized.get("M1", False)


def test_voltage_path_finding() -> None:
    """Test finding voltage path between components."""
    diagram = WiringDiagram(name="test")

    # Create circuit: 24V -> S1 (ON) -> R1 -> M1
    power = IndustrialComponent(
        id="PS1",
        type=IndustrialComponentType.POWER_24VDC,
        designation="24V+"
    )
    sensor = IndustrialComponent(
        id="S1",
        type=IndustrialComponentType.PROXIMITY_SENSOR,
        designation="S1",
        state=SensorState.ON,
        normally_open=True
    )
    relay = IndustrialComponent(
        id="K1",
        type=IndustrialComponentType.RELAY,
        designation="K1"
    )
    motor = IndustrialComponent(
        id="M1",
        type=IndustrialComponentType.MOTOR,
        designation="M1"
    )

    diagram.components.extend([power, sensor, relay, motor])

    wire1 = Wire(id="W1", from_component_id="PS1", to_component_id="S1")
    wire2 = Wire(id="W2", from_component_id="S1", to_component_id="K1")
    wire3 = Wire(id="W3", from_component_id="K1", to_component_id="M1")
    diagram.wires.extend([wire1, wire2, wire3])

    # Simulate and find path
    simulator = VoltageSimulator(diagram)
    path = simulator.get_voltage_path("PS1", "M1")

    assert path == ["PS1", "S1", "K1", "M1"]
