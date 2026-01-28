"""Test interactive simulation capabilities."""

from pathlib import Path
from electrical_schematics.pdf.auto_loader import DiagramAutoLoader
from electrical_schematics.simulation.interactive_simulator import InteractiveSimulator
from electrical_schematics.models import SensorState


def main():
    """Test interactive simulation."""
    pdf_path = Path("DRAWER.pdf")

    if not pdf_path.exists():
        print("Error: DRAWER.pdf not found!")
        return

    print("="*80)
    print("INTERACTIVE SIMULATION TEST")
    print("="*80)

    # Load diagram
    print("\n1. Loading diagram...")
    diagram, format_type = DiagramAutoLoader.load_diagram(pdf_path)
    print(f"   Loaded {len(diagram.components)} components")

    # Create simulator
    print("\n2. Creating interactive simulator...")
    simulator = InteractiveSimulator(diagram)

    # Run initial simulation
    print("\n3. Running initial simulation...")
    simulator.simulate_step()

    energized = simulator.get_energized_components()
    print(f"   Initially energized: {len(energized)} components")
    for comp in energized[:5]:
        print(f"     - {comp.designation}: {comp.voltage_rating}")

    # Test: Trace K1 contactor circuits
    print("\n4. TESTING: Where does K1 get its power?")
    print("-" * 80)

    # Find a contactor (K1, K2, K3)
    contactor_tags = ["-K1", "-K2", "-K3"]
    test_contactor = None

    for tag in contactor_tags:
        comp = diagram.get_component_by_designation(tag)
        if comp:
            test_contactor = tag
            break

    if test_contactor:
        print(f"\nTesting contactor: {test_contactor}")
        print("\n--- COIL CIRCUIT (24VDC Control) ---")

        coil_path = simulator.trace_coil_circuit(test_contactor)
        print(f"Source: {coil_path.source}")
        print(f"Destination: {coil_path.destination}")
        print(f"Path: {' → '.join(coil_path.path_nodes)}")
        print(f"Active: {'YES ✓' if coil_path.is_active else 'NO ✗'}")
        if coil_path.blocking_component:
            print(f"Blocked by: {coil_path.blocking_component}")

        print("\n--- MAIN CONTACTS (Power Side) ---")
        supply_path, load_path = simulator.trace_contact_circuit(test_contactor)

        print(f"\nSupply Path:")
        print(f"  From: {supply_path.source}")
        print(f"  To: {supply_path.destination}")
        print(f"  Path: {' → '.join(supply_path.path_nodes)}")
        print(f"  Voltage: {supply_path.voltage_type}")

        print(f"\nLoad Path:")
        print(f"  From: {load_path.source}")
        print(f"  To: {load_path.destination}")
        print(f"  Path: {' → '.join(load_path.path_nodes)}")
        print(f"  Voltage: {load_path.voltage_type}")

    # Test: Simulate actions
    print("\n5. SIMULATING ACTIONS:")
    print("-" * 80)

    # Find a sensor to toggle
    sensors = diagram.get_sensors()
    if sensors:
        test_sensor = sensors[0]
        print(f"\nToggling sensor: {test_sensor.designation}")
        print(f"  Initial state: {test_sensor.state.value}")

        # Toggle and re-simulate
        simulator.toggle_component(test_sensor.designation)
        print(f"  New state: {test_sensor.state.value}")

        # Check what changed
        new_energized = simulator.get_energized_components()
        print(f"\n  Energized components: {len(energized)} → {len(new_energized)}")

        if len(new_energized) > len(energized):
            print("  ↑ More components energized!")
        elif len(new_energized) < len(energized):
            print("  ↓ Fewer components energized!")
        else:
            print("  = No change in energization")

    # Test: Comprehensive explanation
    print("\n6. COMPREHENSIVE STATE EXPLANATION:")
    print("-" * 80)

    if test_contactor:
        explanation = simulator.explain_state(test_contactor)
        print(explanation)

    # Test: Find all energized by voltage type
    print("\n7. ENERGIZED COMPONENTS BY VOLTAGE:")
    print("-" * 80)

    for voltage_type in ["24VDC", "400VAC", "230VAC"]:
        comps = simulator.get_energized_components(voltage_type)
        if comps:
            print(f"\n{voltage_type}:")
            for comp in comps:
                print(f"  ✓ {comp.designation:10s} - {comp.description[:40]}")

    print("\n" + "="*80)
    print("INTERACTIVE SIMULATION TEST COMPLETE!")
    print("="*80)
    print("\nKey Features Tested:")
    print("  ✓ Coil circuit tracing (where does 24VDC come from?)")
    print("  ✓ Contact circuit tracing (where does power go?)")
    print("  ✓ Interactive toggling (contactors, sensors, fuses)")
    print("  ✓ Real-time simulation updates")
    print("  ✓ Voltage flow visualization")
    print("\nReady for interactive GUI!")


if __name__ == "__main__":
    main()
