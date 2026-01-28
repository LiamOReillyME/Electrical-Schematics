#!/usr/bin/env python3
"""Test script to verify wire rendering from cable routing tables."""

from pathlib import Path
from electrical_schematics.pdf.auto_loader import DiagramAutoLoader

def test_wire_data_exists():
    """Check if wires are created from cable routing tables."""
    pdf_path = Path("/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf")

    if not pdf_path.exists():
        print(f"ERROR: DRAWER.pdf not found at {pdf_path}")
        return

    print("="* 80)
    print("WIRE RENDERING VERIFICATION TEST")
    print("="* 80)
    print()

    # Load diagram
    print("Loading DRAWER.pdf...")
    diagram, format_type = DiagramAutoLoader.load_diagram(pdf_path)

    print(f"Format detected: {format_type}")
    print(f"Components loaded: {len(diagram.components)}")
    print(f"Wires loaded: {len(diagram.wires)}")
    print()

    if not diagram.wires:
        print("❌ ISSUE: No wires found in diagram!")
        print("   Expected: Wires from cable routing tables")
        print()
        return False

    print(f"✓ Wires exist: {len(diagram.wires)} wires loaded")
    print()

    # Check wire data structure
    print("Sample Wire Data:")
    print("-" * 80)

    for i, wire in enumerate(diagram.wires[:3]):  # Show first 3 wires
        print(f"\nWire {i+1}:")
        print(f"  ID: {wire.id}")
        print(f"  From: {wire.from_component_id} (terminal: {wire.from_terminal})")
        print(f"  To: {wire.to_component_id} (terminal: {wire.to_terminal})")
        print(f"  Color: {wire.color}")
        print(f"  Voltage: {wire.voltage_level}")
        print(f"  Path: {len(wire.path) if wire.path else 0} points")

        if wire.path:
            print(f"    Path points: {[(p.x, p.y) for p in wire.path]}")
        else:
            print(f"    ⚠ No path data (wire will not be visible)")

    print()
    print("=" * 80)

    # Check wire path status
    wires_with_paths = sum(1 for w in diagram.wires if w.path and len(w.path) > 0)
    wires_without_paths = len(diagram.wires) - wires_with_paths

    print("Wire Path Summary:")
    print(f"  Wires with paths: {wires_with_paths}/{len(diagram.wires)}")
    print(f"  Wires without paths: {wires_without_paths}/{len(diagram.wires)}")
    print()

    if wires_without_paths > 0:
        print("⚠ WARNING: Some wires lack path data")
        print("   These wires will not be rendered in the GUI")
        print("   Solution: Call DiagramAutoLoader.generate_wire_paths()")
        print()

    # Check component positions (needed for wire paths)
    components_with_positions = sum(
        1 for c in diagram.components
        if c.x != 0.0 or c.y != 0.0
    )

    print("Component Position Summary:")
    print(f"  Components with positions: {components_with_positions}/{len(diagram.components)}")
    print()

    if components_with_positions == 0:
        print("❌ CRITICAL: No components have positions!")
        print("   Wire paths cannot be generated without component positions")
        print()
        return False

    # Test wire path generation
    print("Testing wire path generation...")
    print("-" * 80)

    try:
        DiagramAutoLoader.generate_wire_paths(diagram, routing_style="manhattan")

        wires_with_paths_after = sum(
            1 for w in diagram.wires
            if w.path and len(w.path) > 0
        )

        print(f"✓ Path generation successful!")
        print(f"  Wires with paths after generation: {wires_with_paths_after}/{len(diagram.wires)}")
        print()

        # Show a sample path
        if diagram.wires and diagram.wires[0].path:
            wire = diagram.wires[0]
            print(f"Sample wire path (Wire 1):")
            print(f"  From component: {wire.from_component_id}")
            print(f"  To component: {wire.to_component_id}")
            print(f"  Path points: {len(wire.path)}")
            for j, point in enumerate(wire.path):
                print(f"    Point {j}: ({point.x:.1f}, {point.y:.1f})")

    except Exception as e:
        print(f"❌ ERROR generating wire paths: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)

    if wires_with_paths_after > 0:
        print("✓ Wire rendering data is COMPLETE")
        print()
        print("Next steps:")
        print("  1. Ensure pdf_viewer.set_wires() is called after loading")
        print("  2. Verify _draw_wires() is called in _update_display()")
        print("  3. Check that show_wires flag is True")
        print("  4. Test in GUI by loading DRAWER.pdf")
    else:
        print("❌ Wire rendering data is INCOMPLETE")
        print()
        print("Issues to fix:")
        print("  1. Wire paths are not being generated")
        print("  2. Component positions may be missing")

    return True


if __name__ == "__main__":
    test_wire_data_exists()
