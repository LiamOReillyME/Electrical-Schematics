"""Example: Creating and simulating a simple industrial circuit programmatically."""

from electrical_schematics.models import (
    WiringDiagram,
    IndustrialComponent,
    IndustrialComponentType,
    SensorState,
    Wire
)
from electrical_schematics.simulation import VoltageSimulator
from electrical_schematics.diagnostics import FaultAnalyzer, FaultCondition


def create_example_circuit() -> WiringDiagram:
    """
    Create a simple motor control circuit:
    24VDC -> E-Stop (NC) -> Start Button (NO) -> Contactor K1 -> Motor M1
    """
    diagram = WiringDiagram(name="Simple Motor Control")

    # Power source
    power = IndustrialComponent(
        id="PS1",
        type=IndustrialComponentType.POWER_24VDC,
        designation="24V+",
        voltage_rating="24VDC",
        description="24V DC Power Supply"
    )

    # Emergency stop (normally closed)
    estop = IndustrialComponent(
        id="E1",
        type=IndustrialComponentType.EMERGENCY_STOP,
        designation="E1",
        voltage_rating="24VDC",
        description="Emergency Stop Button",
        normally_open=False,  # NC contact
        state=SensorState.OFF  # Not pressed = circuit closed
    )

    # Start button (normally open)
    start_btn = IndustrialComponent(
        id="S1",
        type=IndustrialComponentType.PUSH_BUTTON,
        designation="S1",
        voltage_rating="24VDC",
        description="Start Button",
        normally_open=True,  # NO contact
        state=SensorState.ON  # Pressed = circuit closed
    )

    # Contactor
    contactor = IndustrialComponent(
        id="K1",
        type=IndustrialComponentType.CONTACTOR,
        designation="K1",
        voltage_rating="24VDC",
        description="Main Contactor"
    )

    # Motor
    motor = IndustrialComponent(
        id="M1",
        type=IndustrialComponentType.MOTOR,
        designation="M1",
        voltage_rating="400VAC",
        description="Main Motor"
    )

    diagram.components.extend([power, estop, start_btn, contactor, motor])

    # Create wire connections
    diagram.wires.extend([
        Wire(id="W1", from_component_id="PS1", to_component_id="E1",
             wire_number="1", voltage_level="24VDC"),
        Wire(id="W2", from_component_id="E1", to_component_id="S1",
             wire_number="2", voltage_level="24VDC"),
        Wire(id="W3", from_component_id="S1", to_component_id="K1",
             wire_number="3", voltage_level="24VDC"),
        Wire(id="W4", from_component_id="K1", to_component_id="M1",
             wire_number="4", voltage_level="24VDC"),
    ])

    return diagram


def main() -> None:
    """Run example simulation and diagnostics."""
    print("=" * 60)
    print("Industrial Wiring Diagram Analyzer - Example")
    print("=" * 60)
    print()

    # Create circuit
    diagram = create_example_circuit()
    print(f"Created diagram: {diagram}")
    print()

    # Simulate normal operation
    print("SIMULATION 1: Normal operation (E-stop not pressed, start button pressed)")
    print("-" * 60)
    simulator = VoltageSimulator(diagram)
    energized = simulator.simulate()

    for comp_id, is_energized in energized.items():
        comp = diagram.get_component(comp_id)
        if comp:
            status = "✓ ENERGIZED" if is_energized else "✗ DE-ENERGIZED"
            print(f"  {status}: {comp.designation} - {comp.description}")
    print()

    # Simulate E-stop pressed
    print("SIMULATION 2: E-stop pressed")
    print("-" * 60)
    diagram.set_sensor_state("E1", SensorState.ON)  # E-stop pressed
    simulator = VoltageSimulator(diagram)
    energized = simulator.simulate()

    for comp_id, is_energized in energized.items():
        comp = diagram.get_component(comp_id)
        if comp and comp.designation in ["K1", "M1"]:
            status = "✓ ENERGIZED" if is_energized else "✗ DE-ENERGIZED"
            print(f"  {status}: {comp.designation} - {comp.description}")
    print()

    # Run diagnostics
    print("DIAGNOSTICS: Why isn't motor running?")
    print("-" * 60)
    fault = FaultCondition(
        symptom="Motor won't start",
        expected_component="M1",
        expected_state="Energized"
    )

    analyzer = FaultAnalyzer(diagram)
    result = analyzer.diagnose(fault)

    print(f"Symptom: {fault.symptom}")
    print(f"Expected: {fault.expected_component} should be {fault.expected_state}")
    print()
    print("Possible Causes:")
    for i, cause in enumerate(result.possible_causes, 1):
        print(f"  {i}. {cause}")
    print()
    print("Suggested Checks:")
    for i, check in enumerate(result.suggested_checks, 1):
        print(f"  {i}. {check}")
    print()


if __name__ == "__main__":
    main()
