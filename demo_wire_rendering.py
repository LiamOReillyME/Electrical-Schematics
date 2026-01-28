#!/usr/bin/env python3
"""
Demonstration script for wire rendering from cable routing tables.

This script shows that auto-generated wires from DRAWER format PDFs
are successfully loaded, positioned, and ready for GUI rendering.
"""

from pathlib import Path
from electrical_schematics.pdf.auto_loader import DiagramAutoLoader


def main():
    """Demonstrate wire rendering capabilities."""
    print("=" * 80)
    print("WIRE RENDERING DEMONSTRATION")
    print("=" * 80)
    print()

    pdf_path = Path("/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf")

    if not pdf_path.exists():
        print(f"❌ ERROR: PDF not found at {pdf_path}")
        return 1

    # Load diagram
    print("Loading DRAWER.pdf...")
    diagram, format_type = DiagramAutoLoader.load_diagram(pdf_path)

    print(f"✓ Format detected: {format_type}")
    print(f"✓ Components loaded: {len(diagram.components)}")
    print(f"✓ Wires loaded: {len(diagram.wires)}")
    print()

    if not diagram.wires:
        print("❌ No wires found!")
        return 1

    # Show wire summary
    print("Wire Summary:")
    print("-" * 80)

    # Count wires by voltage
    voltage_counts = {}
    for wire in diagram.wires:
        voltage_counts[wire.voltage_level] = voltage_counts.get(wire.voltage_level, 0) + 1

    for voltage, count in sorted(voltage_counts.items()):
        print(f"  {voltage:12s}: {count:2d} wires")
    print()

    # Count wires with paths
    wires_with_paths = sum(1 for w in diagram.wires if w.path and len(w.path) > 0)
    print(f"Wires with visual paths: {wires_with_paths}/{len(diagram.wires)}")
    print()

    # Show sample wires
    print("Sample Wire Connections:")
    print("-" * 80)

    for i, wire in enumerate(diagram.wires[:5]):
        print(f"\n{i+1}. {wire.from_component_id} → {wire.to_component_id}")
        print(f"   Terminals: {wire.from_terminal} → {wire.to_terminal}")
        print(f"   Color: {wire.color:4s}  Voltage: {wire.voltage_level}")

        if wire.path and len(wire.path) > 0:
            print(f"   Path: {len(wire.path)} points")
            print(f"   Start: ({wire.path[0].x:.1f}, {wire.path[0].y:.1f})")
            print(f"   End:   ({wire.path[-1].x:.1f}, {wire.path[-1].y:.1f})")
        else:
            print(f"   Path: NO PATH (endpoints not positioned)")

    print()
    print("=" * 80)
    print("WIRE RENDERING: READY FOR GUI DISPLAY")
    print("=" * 80)
    print()
    print("To see wires in the GUI:")
    print("  1. Run: electrical-schematics")
    print("  2. File → Open → DRAWER.pdf")
    print("  3. Wires will appear as colored lines:")
    print("     • Red = 24VDC control circuits")
    print("     • Blue = 0V ground circuits")
    print("     • Gray = AC power circuits")
    print()

    # Show component with most connections
    component_wire_count = {}
    for wire in diagram.wires:
        if wire.from_component_id:
            component_wire_count[wire.from_component_id] = \
                component_wire_count.get(wire.from_component_id, 0) + 1
        if wire.to_component_id:
            component_wire_count[wire.to_component_id] = \
                component_wire_count.get(wire.to_component_id, 0) + 1

    if component_wire_count:
        most_connected = max(component_wire_count.items(), key=lambda x: x[1])
        print(f"Most connected component: {most_connected[0]} ({most_connected[1]} wires)")
        print()

    return 0


if __name__ == "__main__":
    exit(main())
