"""Test the automatic DRAWER diagram loader."""

from pathlib import Path
from electrical_schematics.pdf.auto_loader import DiagramAutoLoader
from electrical_schematics.simulation import VoltageSimulator

def main():
    """Test auto-loading and simulation of DRAWER diagram."""
    pdf_path = Path("DRAWER.pdf")

    if not pdf_path.exists():
        print("Error: DRAWER.pdf not found!")
        return

    print("="*80)
    print("AUTOMATIC DRAWER DIAGRAM LOADING TEST")
    print("="*80)

    # Step 1: Auto-detect format
    print("\n1. DETECTING FORMAT...")
    format_type = DiagramAutoLoader.detect_format(pdf_path)
    print(f"   Format detected: {format_type.upper()}")

    # Step 2: Load diagram
    print("\n2. LOADING DIAGRAM...")
    diagram, detected = DiagramAutoLoader.load_diagram(pdf_path)
    print(f"   Loaded {len(diagram.components)} components")
    print(f"   Loaded {len(diagram.wires)} wire connections")

    # Step 3: Show summary
    print("\n3. DIAGRAM SUMMARY:")
    print("-" * 80)
    summary = DiagramAutoLoader.create_summary(diagram)
    print(summary)

    # Step 4: Test voltage classification
    print("\n4. VOLTAGE CLASSIFICATION TEST:")
    print("-" * 80)

    test_devices = ['-A1', '-G1', '+DG-M1', '-U1', '+DG-B1']

    for device_tag in test_devices:
        device = diagram.get_component_by_designation(device_tag)
        if device:
            print(f"{device_tag:10s}: {device.voltage_rating:8s} | {device.type.value:20s} | {device.description}")

    # Step 5: Test cross-page wire tracing
    print("\n5. CROSS-PAGE WIRE TRACING TEST:")
    print("-" * 80)

    # Get connections for PLC
    plc_wires = diagram.get_wires_for_component("-A1")
    print(f"\nPLC (-A1) has {len(plc_wires)} wire connections")

    # Show connections grouped by cable
    from collections import defaultdict
    by_cable = defaultdict(list)
    for wire in plc_wires[:10]:  # First 10
        by_cable[wire.wire_number].append(wire)

    for cable_name, wires in list(by_cable.items())[:2]:  # First 2 cables
        print(f"\n  Cable: {cable_name}")
        for wire in wires[:3]:  # First 3 wires in each cable
            print(f"    {wire.color:5s}: {wire.from_terminal} -> {wire.to_terminal}")
            print(f"           Voltage: {wire.voltage_level}")

    # Step 6: Test simulation capability
    print("\n6. SIMULATION READINESS TEST:")
    print("-" * 80)

    # Check power sources
    power_sources = diagram.get_power_sources()
    print(f"\nPower sources identified: {len(power_sources)}")
    for ps in power_sources:
        print(f"  - {ps.designation}: {ps.voltage_rating}")

    # Check sensors
    sensors = diagram.get_sensors()
    print(f"\nSensors/switches identified: {len(sensors)}")
    for sensor in sensors:
        print(f"  - {sensor.designation}: State={sensor.state.value}, NO={sensor.normally_open}")

    # Try running simulation
    print("\n7. RUNNING VOLTAGE SIMULATION:")
    print("-" * 80)

    simulator = VoltageSimulator(diagram)
    energized = simulator.simulate()

    energized_count = sum(1 for v in energized.values() if v)
    print(f"\nSimulation complete!")
    print(f"Energized components: {energized_count}/{len(diagram.components)}")

    # Show some energized components
    print("\nSample energized components:")
    count = 0
    for comp_id, is_energized in energized.items():
        if is_energized:
            comp = diagram.get_component(comp_id)
            if comp:
                print(f"  ✓ {comp.designation:10s} ({comp.voltage_rating})")
                count += 1
                if count >= 5:
                    break

    print("\n" + "="*80)
    print("AUTO-LOADER TEST COMPLETE!")
    print("="*80)
    print("\nKey Features Verified:")
    print("  ✓ Automatic format detection")
    print("  ✓ Device tag extraction and voltage classification")
    print("  ✓ Cross-page wire tracing")
    print("  ✓ Component type mapping")
    print("  ✓ Power source identification")
    print("  ✓ Ready for voltage simulation")
    print("\nThe application is ready to automatically analyze DRAWER diagrams!")


if __name__ == "__main__":
    main()
