"""Example: Analyzing a DRAWER-style industrial electrical diagram.

This example demonstrates how to parse and analyze PDF electrical diagrams
in the DRAWER format, including:
- Extracting device tags with voltage classifications
- Tracing wire connections across multiple pages
- Following signal paths through the circuit
- Identifying voltage levels (24VDC vs 400VAC)
"""

from pathlib import Path
from collections import defaultdict
from electrical_schematics.pdf.drawer_parser import DrawerParser


def main() -> None:
    """Analyze the DRAWER.pdf diagram."""
    print("="*80)
    print("DRAWER ELECTRICAL DIAGRAM ANALYSIS")
    print("="*80)

    # Parse the PDF
    pdf_path = Path("DRAWER.pdf")
    if not pdf_path.exists():
        print(f"\nError: {pdf_path} not found!")
        print("Please place the DRAWER.pdf file in the current directory.")
        return

    parser = DrawerParser(pdf_path)
    diagram = parser.parse()

    print(f"\nParsing complete:")
    print(f"  Devices found: {len(diagram.devices)}")
    print(f"  Connections found: {len(diagram.connections)}")

    # 1. Show devices grouped by voltage level
    print("\n" + "="*80)
    print("1. DEVICES GROUPED BY VOLTAGE LEVEL")
    print("="*80)

    by_voltage = defaultdict(list)
    for tag, device in diagram.devices.items():
        by_voltage[device.voltage_level].append((tag, device))

    # Show low voltage devices first (control circuits)
    for voltage in ['5VDC', '24VDC', '230VAC', '400VAC', 'UNKNOWN']:
        if voltage not in by_voltage:
            continue

        devices_list = sorted(by_voltage[voltage], key=lambda x: x[0])

        if voltage in ['5VDC', '24VDC']:
            category = "LOW VOLTAGE - Control & Signals"
        elif voltage in ['230VAC', '400VAC']:
            category = "HIGH VOLTAGE - Power"
        else:
            category = "Passive/Unknown"

        print(f"\n{voltage} - {category} ({len(devices_list)} devices):")
        for tag, device in devices_list:
            print(f"  {tag:10s} | Page {device.page_ref:5s} | {device.tech_data}")

    # 2. Trace connections for a specific device
    print("\n" + "="*80)
    print("2. TRACING CONNECTIONS FOR PLC (-A1)")
    print("="*80)

    a1_device = diagram.get_device("-A1")
    if a1_device:
        print(f"\nDevice: -A1")
        print(f"  Type: {a1_device.type_designation}")
        print(f"  Specs: {a1_device.tech_data}")
        print(f"  Location: Page {a1_device.page_ref}")

    a1_connections = diagram.get_connections_for_device("-A1")
    print(f"\nFound {len(a1_connections)} wire connections")

    # Group connections by cable
    by_cable = defaultdict(list)
    for conn in a1_connections:
        by_cable[conn.cable_name].append(conn)

    for cable_name in sorted(by_cable.keys())[:3]:  # Show first 3 cables
        connections = by_cable[cable_name]
        print(f"\n{cable_name} ({connections[0].cable_type}):")
        for conn in connections[:5]:  # Show first 5 conductors
            source_dev = diagram._extract_device_tag(conn.source)
            target_dev = diagram._extract_device_tag(conn.target)
            print(f"  {conn.wire_color:4s}: {conn.source} -> {conn.target}")

            # Show connected device info
            if source_dev != "-A1":
                other_dev = diagram.get_device(source_dev)
                if other_dev:
                    print(f"        Connected to: {source_dev} ({other_dev.voltage_level})")
            else:
                other_dev = diagram.get_device(target_dev)
                if other_dev:
                    print(f"        Connected to: {target_dev} ({other_dev.voltage_level})")

        if len(connections) > 5:
            print(f"  ... and {len(connections) - 5} more conductors")

    # 3. Find power distribution paths
    print("\n" + "="*80)
    print("3. POWER DISTRIBUTION")
    print("="*80)

    # Find 400VAC devices (motors, VFDs)
    power_devices = [
        (tag, dev) for tag, dev in diagram.devices.items()
        if dev.voltage_level == "400VAC"
    ]

    print(f"\n400VAC Power Equipment ({len(power_devices)} devices):")
    for tag, device in sorted(power_devices):
        connections = diagram.get_connections_for_device(tag)
        print(f"\n  {tag} - {device.tech_data}")
        print(f"    Page: {device.page_ref}")
        print(f"    Cables: {len(connections)} connections")

        # Show power cable if found
        for conn in connections[:2]:
            if 'M' in conn.cable_type or 'power' in conn.function_source.lower():
                print(f"    Power cable: {conn.cable_name} ({conn.cable_type})")
                break

    # 4. Control circuit analysis
    print("\n" + "="*80)
    print("4. CONTROL CIRCUIT ANALYSIS (24VDC)")
    print("="*80)

    control_devices = [
        (tag, dev) for tag, dev in diagram.devices.items()
        if dev.voltage_level == "24VDC"
    ]

    print(f"\n24VDC Control Devices ({len(control_devices)} devices):")
    for tag, device in sorted(control_devices):
        print(f"\n  {tag:10s} - {device.tech_data}")
        print(f"    Type: {device.type_designation}")

        # Count connections
        connections = diagram.get_connections_for_device(tag)
        print(f"    Wired connections: {len(connections)}")

    # 5. Summary statistics
    print("\n" + "="*80)
    print("5. SUMMARY STATISTICS")
    print("="*80)

    # Count cables
    unique_cables = set(conn.cable_name for conn in diagram.connections)
    print(f"\nTotal unique cables: {len(unique_cables)}")

    # Count conductors by color
    by_color = defaultdict(int)
    for conn in diagram.connections:
        if conn.wire_color:
            by_color[conn.wire_color] += 1

    print(f"\nConductors by color:")
    for color, count in sorted(by_color.items(), key=lambda x: -x[1])[:10]:
        print(f"  {color:6s}: {count}")

    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)


if __name__ == "__main__":
    main()
