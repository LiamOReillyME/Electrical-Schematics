"""Tests for PLC INPUT STATE component functionality."""

import pytest
from electrical_schematics.models import (
    IndustrialComponent,
    IndustrialComponentType,
    SensorState,
    WiringDiagram,
    Wire
)
from electrical_schematics.simulation.interactive_simulator import InteractiveSimulator
from electrical_schematics.gui.electrical_symbols import get_component_symbol


class TestPLCInputStateComponent:
    """Test PLC INPUT STATE component creation and behavior."""

    def test_component_type_exists(self):
        """Test that PLC_INPUT_STATE type is defined."""
        assert hasattr(IndustrialComponentType, 'PLC_INPUT_STATE')
        assert IndustrialComponentType.PLC_INPUT_STATE.value == "plc_input_state"

    def test_create_plc_input_no(self):
        """Test creating a normally-open PLC input."""
        plc_input = IndustrialComponent(
            id="i0_0",
            type=IndustrialComponentType.PLC_INPUT_STATE,
            designation="I0.0",
            voltage_rating="24VDC",
            state=SensorState.OFF,
            normally_open=True
        )

        assert plc_input.type == IndustrialComponentType.PLC_INPUT_STATE
        assert plc_input.designation == "I0.0"
        assert plc_input.state == SensorState.OFF
        assert plc_input.normally_open is True

    def test_create_plc_input_nc(self):
        """Test creating a normally-closed PLC input."""
        plc_input = IndustrialComponent(
            id="i0_1",
            type=IndustrialComponentType.PLC_INPUT_STATE,
            designation="I0.1",
            voltage_rating="24VDC",
            state=SensorState.ON,
            normally_open=False
        )

        assert plc_input.type == IndustrialComponentType.PLC_INPUT_STATE
        assert plc_input.designation == "I0.1"
        assert plc_input.state == SensorState.ON
        assert plc_input.normally_open is False

    def test_plc_input_is_sensor(self):
        """Test that PLC input is recognized as a sensor."""
        plc_input = IndustrialComponent(
            id="i0_0",
            type=IndustrialComponentType.PLC_INPUT_STATE,
            designation="I0.0",
            voltage_rating="24VDC"
        )

        assert plc_input.is_sensor() is True

    def test_plc_input_no_energization(self):
        """Test NO PLC input energization logic."""
        plc_input = IndustrialComponent(
            id="i0_0",
            type=IndustrialComponentType.PLC_INPUT_STATE,
            designation="I0.0",
            state=SensorState.OFF,
            normally_open=True
        )

        # NO input: not energized when OFF
        assert plc_input.is_energized() is False

        # NO input: energized when ON
        plc_input.state = SensorState.ON
        assert plc_input.is_energized() is True

    def test_plc_input_nc_energization(self):
        """Test NC PLC input energization logic."""
        plc_input = IndustrialComponent(
            id="i0_1",
            type=IndustrialComponentType.PLC_INPUT_STATE,
            designation="I0.1",
            state=SensorState.ON,
            normally_open=False
        )

        # NC input: not energized when ON
        assert plc_input.is_energized() is False

        # NC input: energized when OFF
        plc_input.state = SensorState.OFF
        assert plc_input.is_energized() is True


class TestPLCInputStateSymbol:
    """Test PLC INPUT STATE symbol generation."""

    def test_symbol_generation_off(self):
        """Test symbol generation for OFF state."""
        svg = get_component_symbol(
            component_type="plc_input_state",
            designation="I0.0",
            address="I0.0",
            state=False
        )

        assert svg is not None
        assert len(svg) > 0
        assert 'svg' in svg.lower()
        assert 'I0.0' in svg
        assert 'circle' in svg  # LED indicator

    def test_symbol_generation_on(self):
        """Test symbol generation for ON state."""
        svg = get_component_symbol(
            component_type="plc_input_state",
            designation="I0.1",
            address="I0.1",
            state=True
        )

        assert svg is not None
        assert len(svg) > 0
        assert 'svg' in svg.lower()
        assert 'I0.1' in svg
        assert 'circle' in svg  # LED indicator

    def test_symbol_color_off(self):
        """Test that OFF symbol uses gray color."""
        svg = get_component_symbol(
            component_type="plc_input_state",
            designation="I0.0",
            address="I0.0",
            state=False
        )

        # OFF state should use gray LED
        assert '#95a5a6' in svg or 'gray' in svg.lower()

    def test_symbol_color_on(self):
        """Test that ON symbol uses green color."""
        svg = get_component_symbol(
            component_type="plc_input_state",
            designation="I0.0",
            address="I0.0",
            state=True
        )

        # ON state should use green LED (energized color)
        assert '#27AE60' in svg or '#27ae60' in svg


class TestPLCInputStateSimulation:
    """Test PLC INPUT STATE in circuit simulation."""

    def test_simple_circuit_with_plc_input(self):
        """Test a simple circuit with PLC input controlling a contactor."""
        diagram = WiringDiagram(name="Test Circuit")

        # Power source
        power = IndustrialComponent(
            id="pwr",
            type=IndustrialComponentType.POWER_24VDC,
            designation="+24V",
            voltage_rating="24VDC"
        )

        # PLC Input (NO)
        plc_input = IndustrialComponent(
            id="i0_0",
            type=IndustrialComponentType.PLC_INPUT_STATE,
            designation="I0.0",
            voltage_rating="24VDC",
            state=SensorState.OFF,
            normally_open=True
        )

        # Contactor
        contactor = IndustrialComponent(
            id="k1",
            type=IndustrialComponentType.CONTACTOR,
            designation="K1",
            voltage_rating="24VDC"
        )

        # Add components
        diagram.components.extend([power, plc_input, contactor])

        # Wire: +24V -> I0.0 -> K1
        wire1 = Wire(
            id="w1",
            from_component_id="pwr",
            to_component_id="i0_0",
            voltage_level="24VDC"
        )

        wire2 = Wire(
            id="w2",
            from_component_id="i0_0",
            to_component_id="k1",
            voltage_level="24VDC"
        )

        diagram.wires.extend([wire1, wire2])

        # Create simulator
        simulator = InteractiveSimulator(diagram)

        # Initial state: PLC input OFF, contactor should be de-energized
        simulator.simulate_step()
        k1_node = simulator.voltage_nodes.get("k1")
        assert k1_node.is_energized is False

        # Toggle PLC input ON
        plc_input.state = SensorState.ON
        simulator.simulate_step()
        k1_node = simulator.voltage_nodes.get("k1")
        assert k1_node.is_energized is True

        # Toggle PLC input OFF
        plc_input.state = SensorState.OFF
        simulator.simulate_step()
        k1_node = simulator.voltage_nodes.get("k1")
        assert k1_node.is_energized is False

    def test_toggle_component_method(self):
        """Test toggling PLC input using simulator method."""
        diagram = WiringDiagram(name="Test Circuit")

        plc_input = IndustrialComponent(
            id="i0_0",
            type=IndustrialComponentType.PLC_INPUT_STATE,
            designation="I0.0",
            voltage_rating="24VDC",
            state=SensorState.OFF,
            normally_open=True
        )

        diagram.components.append(plc_input)

        simulator = InteractiveSimulator(diagram)

        # Initial state
        assert plc_input.state == SensorState.OFF

        # Toggle ON
        simulator.toggle_component("I0.0")
        assert plc_input.state == SensorState.ON

        # Toggle OFF
        simulator.toggle_component("I0.0")
        assert plc_input.state == SensorState.OFF

    def test_start_stop_circuit(self):
        """Test start/stop motor circuit with PLC inputs."""
        diagram = WiringDiagram(name="Start/Stop Circuit")

        # Power
        power = IndustrialComponent(
            id="pwr",
            type=IndustrialComponentType.POWER_24VDC,
            designation="+24V",
            voltage_rating="24VDC"
        )

        # Start button (NO)
        start = IndustrialComponent(
            id="i0_0",
            type=IndustrialComponentType.PLC_INPUT_STATE,
            designation="I0.0",
            voltage_rating="24VDC",
            state=SensorState.OFF,
            normally_open=True
        )

        # Stop button (NC - Normally Closed)
        # For NC: state=OFF means not pressed, contact is CLOSED (allows current)
        # For NC: state=ON means pressed, contact is OPEN (blocks current)
        stop = IndustrialComponent(
            id="i0_1",
            type=IndustrialComponentType.PLC_INPUT_STATE,
            designation="I0.1",
            voltage_rating="24VDC",
            state=SensorState.OFF,  # Not pressed = NC contact closed = current flows
            normally_open=False
        )

        # Contactor
        contactor = IndustrialComponent(
            id="k1",
            type=IndustrialComponentType.CONTACTOR,
            designation="K1",
            voltage_rating="24VDC"
        )

        diagram.components.extend([power, start, stop, contactor])

        # Wiring: +24V -> Start -> Stop -> K1
        diagram.wires.extend([
            Wire(id="w1", from_component_id="pwr", to_component_id="i0_0", voltage_level="24VDC"),
            Wire(id="w2", from_component_id="i0_0", to_component_id="i0_1", voltage_level="24VDC"),
            Wire(id="w3", from_component_id="i0_1", to_component_id="k1", voltage_level="24VDC")
        ])

        simulator = InteractiveSimulator(diagram)

        # Initial: Start OFF, Stop ON (not pressed)
        # Contactor should be OFF (start not pressed)
        simulator.simulate_step()
        k1_node = simulator.voltage_nodes.get("k1")
        assert k1_node.is_energized is False

        # Press start (I0.0 ON)
        # Contactor should be ON (both start pressed and stop not pressed)
        start.state = SensorState.ON
        simulator.simulate_step()
        k1_node = simulator.voltage_nodes.get("k1")
        assert k1_node.is_energized is True

        # Press stop (I0.1 ON - pressing NC button opens the contact)
        # Contactor should be OFF (stop pressed breaks circuit)
        stop.state = SensorState.ON
        simulator.simulate_step()
        k1_node = simulator.voltage_nodes.get("k1")
        assert k1_node.is_energized is False


class TestPLCInputStateIntegration:
    """Test PLC INPUT STATE integration with existing features."""

    def test_component_string_representation(self):
        """Test string representation of PLC input component."""
        plc_input = IndustrialComponent(
            id="i0_0",
            type=IndustrialComponentType.PLC_INPUT_STATE,
            designation="I0.0",
            voltage_rating="24VDC",
            description="Start button"
        )

        str_repr = str(plc_input)
        assert "I0.0" in str_repr
        assert "plc_input_state" in str_repr
        assert "24VDC" in str_repr

    def test_get_sensors_includes_plc_inputs(self):
        """Test that diagram.get_sensors() includes PLC inputs."""
        diagram = WiringDiagram(name="Test")

        plc_input = IndustrialComponent(
            id="i0_0",
            type=IndustrialComponentType.PLC_INPUT_STATE,
            designation="I0.0",
            voltage_rating="24VDC"
        )

        diagram.components.append(plc_input)

        sensors = diagram.get_sensors()
        assert len(sensors) == 1
        assert sensors[0].designation == "I0.0"

    def test_set_sensor_state_works_for_plc_input(self):
        """Test that WiringDiagram.set_sensor_state() works for PLC inputs."""
        diagram = WiringDiagram(name="Test")

        plc_input = IndustrialComponent(
            id="i0_0",
            type=IndustrialComponentType.PLC_INPUT_STATE,
            designation="I0.0",
            voltage_rating="24VDC",
            state=SensorState.OFF
        )

        diagram.components.append(plc_input)

        # Set state to ON
        result = diagram.set_sensor_state("I0.0", SensorState.ON)
        assert result is True
        assert plc_input.state == SensorState.ON

        # Set state to OFF
        result = diagram.set_sensor_state("I0.0", SensorState.OFF)
        assert result is True
        assert plc_input.state == SensorState.OFF


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
