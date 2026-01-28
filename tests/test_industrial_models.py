"""Tests for industrial component models."""

import pytest
from electrical_schematics.models import (
    IndustrialComponent,
    IndustrialComponentType,
    SensorState,
    WiringDiagram,
    Wire,
    PagePosition
)


def test_sensor_normally_open_energization() -> None:
    """Test NO sensor energization logic."""
    sensor = IndustrialComponent(
        id="S1",
        type=IndustrialComponentType.PROXIMITY_SENSOR,
        designation="S1",
        normally_open=True
    )

    # NO sensor OFF = not energized
    sensor.state = SensorState.OFF
    assert not sensor.is_energized()

    # NO sensor ON = energized
    sensor.state = SensorState.ON
    assert sensor.is_energized()


def test_sensor_normally_closed_energization() -> None:
    """Test NC sensor energization logic."""
    sensor = IndustrialComponent(
        id="S2",
        type=IndustrialComponentType.LIMIT_SWITCH,
        designation="S2",
        normally_open=False
    )

    # NC sensor OFF = energized
    sensor.state = SensorState.OFF
    assert sensor.is_energized()

    # NC sensor ON = not energized
    sensor.state = SensorState.ON
    assert not sensor.is_energized()


def test_diagram_sensor_state_management() -> None:
    """Test setting sensor states in a diagram."""
    diagram = WiringDiagram(name="test")

    sensor = IndustrialComponent(
        id="S1",
        type=IndustrialComponentType.PROXIMITY_SENSOR,
        designation="S1"
    )
    diagram.components.append(sensor)

    # Set state
    assert diagram.set_sensor_state("S1", SensorState.ON)
    assert sensor.state == SensorState.ON

    # Reset all sensors
    diagram.reset_all_sensor_states()
    assert sensor.state == SensorState.UNKNOWN


def test_power_source_identification() -> None:
    """Test identifying power sources."""
    diagram = WiringDiagram(name="test")

    power = IndustrialComponent(
        id="PS1",
        type=IndustrialComponentType.POWER_24VDC,
        designation="24V+",
        voltage_rating="24VDC"
    )
    motor = IndustrialComponent(
        id="M1",
        type=IndustrialComponentType.MOTOR,
        designation="M1"
    )

    diagram.components.extend([power, motor])

    sources = diagram.get_power_sources()
    assert len(sources) == 1
    assert sources[0].id == "PS1"


def test_component_page_field() -> None:
    """Test that component has page field."""
    component = IndustrialComponent(
        id="K1",
        type=IndustrialComponentType.CONTACTOR,
        designation="-K1",
        page=5
    )

    assert component.page == 5


def test_component_default_page() -> None:
    """Test that component page defaults to 0."""
    component = IndustrialComponent(
        id="K1",
        type=IndustrialComponentType.CONTACTOR,
        designation="-K1"
    )

    assert component.page == 0


def test_component_add_page_position() -> None:
    """Test adding page positions for multi-page components."""
    component = IndustrialComponent(
        id="K1",
        type=IndustrialComponentType.CONTACTOR,
        designation="-K1"
    )

    # Add first position
    component.add_page_position(
        page=5,
        x=100.0,
        y=200.0,
        width=50.0,
        height=40.0,
        confidence=0.9
    )

    # Check primary position is set
    assert component.page == 5
    assert component.x == 100.0
    assert component.y == 200.0

    # Check page_positions dictionary
    assert 5 in component.page_positions
    pos = component.page_positions[5]
    assert pos.x == 100.0
    assert pos.y == 200.0
    assert pos.confidence == 0.9


def test_component_multi_page_positions() -> None:
    """Test component appearing on multiple pages."""
    component = IndustrialComponent(
        id="K1",
        type=IndustrialComponentType.CONTACTOR,
        designation="-K1"
    )

    # Add positions on multiple pages
    component.add_page_position(page=3, x=100.0, y=200.0, width=50.0, height=40.0, confidence=0.8)
    component.add_page_position(page=7, x=150.0, y=250.0, width=50.0, height=40.0, confidence=0.9)
    component.add_page_position(page=12, x=200.0, y=300.0, width=50.0, height=40.0, confidence=0.7)

    # Check all pages are tracked
    assert component.get_pages() == [3, 7, 12]

    # Check primary position is highest confidence (page 7)
    assert component.page == 7
    assert component.x == 150.0

    # Check individual page positions
    pos_3 = component.get_position_for_page(3)
    assert pos_3 is not None
    assert pos_3.x == 100.0

    pos_7 = component.get_position_for_page(7)
    assert pos_7 is not None
    assert pos_7.x == 150.0

    pos_12 = component.get_position_for_page(12)
    assert pos_12 is not None
    assert pos_12.x == 200.0


def test_component_is_on_page() -> None:
    """Test checking if component is on a specific page."""
    component = IndustrialComponent(
        id="K1",
        type=IndustrialComponentType.CONTACTOR,
        designation="-K1"
    )

    # Add positions
    component.add_page_position(page=5, x=100.0, y=200.0, width=50.0, height=40.0)
    component.add_page_position(page=8, x=150.0, y=250.0, width=50.0, height=40.0)

    # Check is_on_page
    assert component.is_on_page(5) is True
    assert component.is_on_page(8) is True
    assert component.is_on_page(3) is False
    assert component.is_on_page(10) is False


def test_component_get_pages_empty() -> None:
    """Test get_pages with no positions."""
    component = IndustrialComponent(
        id="K1",
        type=IndustrialComponentType.CONTACTOR,
        designation="-K1"
    )

    # No positions set (x=0, y=0)
    assert component.get_pages() == []


def test_component_get_pages_single() -> None:
    """Test get_pages with single position via primary fields."""
    component = IndustrialComponent(
        id="K1",
        type=IndustrialComponentType.CONTACTOR,
        designation="-K1",
        x=100.0,
        y=200.0,
        page=5
    )

    # Single position via primary fields
    assert component.get_pages() == [5]


def test_page_position_dataclass() -> None:
    """Test PagePosition dataclass."""
    pos = PagePosition(
        page=5,
        x=100.0,
        y=200.0,
        width=50.0,
        height=40.0,
        confidence=0.95
    )

    assert pos.page == 5
    assert pos.x == 100.0
    assert pos.y == 200.0
    assert pos.width == 50.0
    assert pos.height == 40.0
    assert pos.confidence == 0.95


def test_page_position_default_confidence() -> None:
    """Test PagePosition default confidence."""
    pos = PagePosition(
        page=5,
        x=100.0,
        y=200.0,
        width=50.0,
        height=40.0
    )

    assert pos.confidence == 1.0
