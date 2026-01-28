"""Tests for fault diagnostics."""

import pytest
from electrical_schematics.models import (
    WiringDiagram,
    IndustrialComponent,
    IndustrialComponentType,
    SensorState,
    Wire
)
from electrical_schematics.diagnostics import FaultAnalyzer, FaultCondition


def test_diagnose_deenergized_component() -> None:
    """Test diagnosing why a component is not energized."""
    diagram = WiringDiagram(name="test")

    # Create circuit: 24V -> S1 (OFF) -> M1
    power = IndustrialComponent(
        id="PS1",
        type=IndustrialComponentType.POWER_24VDC,
        designation="24V+",
        voltage_rating="24VDC"
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
        designation="M1",
        description="Main motor"
    )

    diagram.components.extend([power, sensor, motor])

    wire1 = Wire(id="W1", from_component_id="PS1", to_component_id="S1")
    wire2 = Wire(id="W2", from_component_id="S1", to_component_id="M1")
    diagram.wires.extend([wire1, wire2])

    # Create fault condition
    fault = FaultCondition(
        symptom="Motor won't start",
        expected_component="M1",
        expected_state="energized"
    )

    # Diagnose
    analyzer = FaultAnalyzer(diagram)
    result = analyzer.diagnose(fault)

    # Should identify S1 as the cause
    assert len(result.possible_causes) > 0
    assert any("S1" in cause for cause in result.possible_causes)
    assert len(result.suggested_checks) > 0


def test_diagnose_component_not_found() -> None:
    """Test diagnosing with non-existent component."""
    diagram = WiringDiagram(name="test")

    fault = FaultCondition(
        symptom="Something broken",
        expected_component="XYZ",
        expected_state="energized"
    )

    analyzer = FaultAnalyzer(diagram)
    result = analyzer.diagnose(fault)

    assert len(result.possible_causes) > 0
    assert "not found" in result.possible_causes[0].lower()
