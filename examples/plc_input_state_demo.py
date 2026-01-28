#!/usr/bin/env python3
"""
Demonstration of PLC INPUT STATE component.

This example shows:
1. Creating PLC input state indicators
2. Toggling them to simulate PLC input changes
3. How they affect relay coils and motor control
4. Visual state indication (LED-style)
"""

from electrical_schematics.models import (
    WiringDiagram, IndustrialComponent, IndustrialComponentType,
    SensorState, Wire
)
from electrical_schematics.simulation.interactive_simulator import InteractiveSimulator
from electrical_schematics.gui.electrical_symbols import get_component_symbol


def create_demo_circuit():
    """Create a simple circuit with PLC inputs controlling a motor contactor.

    Circuit Logic:
    - PLC Input I0.0: Start button simulation (NO)
    - PLC Input I0.1: Stop button simulation (NC)
    - Contactor K1: Motor contactor controlled by PLC inputs
    - Motor M1: 400VAC motor

    When I0.0 is ON and I0.1 is ON (not pressed), K1 energizes and starts M1.
    """
    diagram = WiringDiagram(name="PLC Input Demo Circuit")

    # Power sources
    power_24v = IndustrialComponent(
        id="pwr_24v",
        type=IndustrialComponentType.POWER_24VDC,
        designation="+24V",
        voltage_rating="24VDC",
        description="24VDC control power supply"
    )

    power_400v = IndustrialComponent(
        id="pwr_400v",
        type=IndustrialComponentType.POWER_400VAC,
        designation="L1",
        voltage_rating="400VAC",
        description="400VAC main power"
    )

    # PLC Input State Indicators (Toggleable)
    plc_input_start = IndustrialComponent(
        id="plc_i0_0",
        type=IndustrialComponentType.PLC_INPUT_STATE,
        designation="I0.0",
        voltage_rating="24VDC",
        description="Start button (NO) - PLC Input",
        state=SensorState.OFF,  # Initially OFF
        normally_open=True
    )

    plc_input_stop = IndustrialComponent(
        id="plc_i0_1",
        type=IndustrialComponentType.PLC_INPUT_STATE,
        designation="I0.1",
        voltage_rating="24VDC",
        description="Stop button (NC) - PLC Input",
        state=SensorState.ON,  # Initially ON (not pressed)
        normally_open=False  # Normally Closed
    )

    # Contactor K1 (controlled by PLC inputs)
    contactor_k1 = IndustrialComponent(
        id="k1",
        type=IndustrialComponentType.CONTACTOR,
        designation="K1",
        voltage_rating="24VDC",
        description="Main motor contactor",
        state=SensorState.OFF,
        contacts=["K1:13-14", "K1:21-22"]
    )

    # Motor M1
    motor_m1 = IndustrialComponent(
        id="m1",
        type=IndustrialComponentType.MOTOR,
        designation="M1",
        voltage_rating="400VAC",
        description="Main motor 5.5kW"
    )

    # Add all components to the list
    diagram.components.extend([
        power_24v,
        power_400v,
        plc_input_start,
        plc_input_stop,
        contactor_k1,
        motor_m1
    ])

    # Control circuit wiring (24VDC)
    # +24V -> I0.0 (Start) -> I0.1 (Stop) -> K1 Coil -> 0V
    wire1 = Wire(
        id="w1",
        from_component_id="pwr_24v",
        to_component_id="plc_i0_0",
        voltage_level="24VDC",
        color="Red"
    )

    wire2 = Wire(
        id="w2",
        from_component_id="plc_i0_0",
        to_component_id="plc_i0_1",
        voltage_level="24VDC",
        color="Red"
    )

    wire3 = Wire(
        id="w3",
        from_component_id="plc_i0_1",
        to_component_id="k1",
        voltage_level="24VDC",
        color="Red"
    )

    # Power circuit wiring (400VAC)
    # L1 -> K1 Contacts -> M1
    wire4 = Wire(
        id="w4",
        from_component_id="pwr_400v",
        to_component_id="k1",
        voltage_level="400VAC",
        color="Black"
    )

    wire5 = Wire(
        id="w5",
        from_component_id="k1",
        to_component_id="m1",
        voltage_level="400VAC",
        color="Black"
    )

    diagram.wires.extend([wire1, wire2, wire3, wire4, wire5])

    return diagram


def print_circuit_state(simulator: InteractiveSimulator):
    """Print the current state of the circuit."""
    print("\n" + "="*60)
    print("CIRCUIT STATE")
    print("="*60)

    # PLC Inputs
    i0_0 = simulator.diagram.get_component_by_designation("I0.0")
    i0_1 = simulator.diagram.get_component_by_designation("I0.1")

    print(f"\nPLC Inputs:")
    print(f"  I0.0 (Start NO):  {'[ON]  🟢' if i0_0.state == SensorState.ON else '[OFF] ⚫'}")
    print(f"  I0.1 (Stop NC):   {'[ON]  🟢' if i0_1.state == SensorState.ON else '[OFF] ⚫'}")

    # Contactor
    k1 = simulator.diagram.get_component_by_designation("K1")
    k1_node = simulator.voltage_nodes.get(k1.id)
    k1_energized = k1_node.is_energized if k1_node else False

    print(f"\nContactor:")
    print(f"  K1 Coil:          {'[ENERGIZED] 🟢' if k1_energized else '[DE-ENERGIZED] ⚫'}")
    print(f"  K1 Contacts:      {'[CLOSED] ✓' if k1_energized else '[OPEN] ✗'}")

    # Motor
    m1 = simulator.diagram.get_component_by_designation("M1")
    m1_node = simulator.voltage_nodes.get(m1.id)
    m1_energized = m1_node.is_energized if m1_node else False

    print(f"\nMotor:")
    print(f"  M1 (5.5kW):       {'[RUNNING] 🟢' if m1_energized else '[STOPPED] ⚫'}")

    print("\n" + "="*60)


def demonstrate_symbol_generation():
    """Show how to generate PLC input state symbols."""
    print("\n" + "="*60)
    print("PLC INPUT STATE SYMBOL GENERATION")
    print("="*60)

    # Generate symbol in OFF state
    svg_off = get_component_symbol(
        component_type="plc_input_state",
        designation="I0.0",
        address="I0.0",
        state=False
    )

    print("\nGenerated SVG for I0.0 (OFF state):")
    print(f"  Length: {len(svg_off)} characters")
    print(f"  Contains LED indicator: {'circle' in svg_off}")
    print(f"  Contains address label: {'I0.0' in svg_off}")

    # Generate symbol in ON state
    svg_on = get_component_symbol(
        component_type="plc_input_state",
        designation="I0.1",
        address="I0.1",
        state=True
    )

    print("\nGenerated SVG for I0.1 (ON state):")
    print(f"  Length: {len(svg_on)} characters")
    print(f"  Uses energized color: {('#27AE60' in svg_on or '#27ae60' in svg_on)}")


def main():
    """Run the demonstration."""
    print("\n" + "="*60)
    print("PLC INPUT STATE COMPONENT DEMONSTRATION")
    print("="*60)
    print("\nThis demo shows a motor start/stop circuit with PLC inputs.")
    print("The PLC inputs can be toggled to simulate button presses.")

    # Create circuit
    diagram = create_demo_circuit()
    simulator = InteractiveSimulator(diagram)

    # Initial state
    print("\n--- INITIAL STATE (Start OFF, Stop ON) ---")
    simulator.simulate_step()
    print_circuit_state(simulator)

    # Press start button (I0.0 ON)
    print("\n\n--- PRESS START BUTTON (I0.0 -> ON) ---")
    simulator.toggle_component("I0.0")
    print_circuit_state(simulator)
    print("\n✓ Motor should now be RUNNING")

    # Press stop button (I0.1 OFF)
    print("\n\n--- PRESS STOP BUTTON (I0.1 -> OFF) ---")
    simulator.toggle_component("I0.1")
    print_circuit_state(simulator)
    print("\n✓ Motor should now be STOPPED")

    # Release stop button (I0.1 ON)
    print("\n\n--- RELEASE STOP BUTTON (I0.1 -> ON) ---")
    simulator.toggle_component("I0.1")
    print_circuit_state(simulator)
    print("\n✓ Motor should be RUNNING again (start still pressed)")

    # Release start button (I0.0 OFF)
    print("\n\n--- RELEASE START BUTTON (I0.0 -> OFF) ---")
    simulator.toggle_component("I0.0")
    print_circuit_state(simulator)
    print("\n✓ Motor should STOP (no latching)")

    # Symbol generation demo
    demonstrate_symbol_generation()

    print("\n" + "="*60)
    print("INTEGRATION NOTES")
    print("="*60)
    print("""
1. DRAG AND DROP:
   - Add PLC_INPUT_STATE to component palette
   - Users can drag to PDF canvas
   - Double-click to toggle ON/OFF

2. VISUAL FEEDBACK:
   - Green LED when ON
   - Gray LED when OFF
   - Shows PLC address (I0.0, %IX0.0, etc.)

3. SIMULATION:
   - Treated as sensor (toggleable)
   - Normally Open by default
   - Can be NC if needed (stop buttons)
   - Affects downstream relays/contactors

4. USE CASES:
   - Simulate PLC input states
   - Test relay logic sequences
   - Motor start/stop circuits
   - Safety circuit validation
    """)

    print("\n✓ Demo complete!")


if __name__ == "__main__":
    main()
