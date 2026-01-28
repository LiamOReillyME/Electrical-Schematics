#!/usr/bin/env python3
"""Test script to debug wire rendering issue."""

from pathlib import Path
from electrical_schematics.pdf.auto_loader import DiagramAutoLoader

# Load DRAWER.pdf
pdf_path = Path("DRAWER.pdf")

if not pdf_path.exists():
    print(f"ERROR: {pdf_path} not found")
    print("Please ensure DRAWER.pdf is in the current directory")
    exit(1)

print("Loading DRAWER.pdf...")
diagram, format_type = DiagramAutoLoader.load_diagram(pdf_path)

print(f"\nFormat detected: {format_type}")
print(f"Components loaded: {len(diagram.components)}")
print(f"Wires loaded: {len(diagram.wires)}")

if diagram.wires:
    print("\n" + "=" * 60)
    print("WIRE ANALYSIS")
    print("=" * 60)

    wires_with_paths = sum(1 for w in diagram.wires if w.path and len(w.path) > 0)
    wires_without_paths = len(diagram.wires) - wires_with_paths

    print(f"Wires with paths: {wires_with_paths}")
    print(f"Wires without paths: {wires_without_paths}")

    # Show first 5 wires
    print("\nFirst 5 wires:")
    for i, wire in enumerate(diagram.wires[:5]):
        print(f"\n  Wire {i+1}:")
        print(f"    ID: {wire.id}")
        print(f"    From: {wire.from_component_id} (terminal: {wire.from_terminal})")
        print(f"    To: {wire.to_component_id} (terminal: {wire.to_terminal})")
        print(f"    Voltage: {wire.voltage_level}")
        print(f"    Color: {wire.color}")

        if wire.path and len(wire.path) > 0:
            print(f"    Path points: {len(wire.path)}")
            print(f"      Start: ({wire.path[0].x:.1f}, {wire.path[0].y:.1f})")
            print(f"      End: ({wire.path[-1].x:.1f}, {wire.path[-1].y:.1f})")
        else:
            print("    ⚠ NO PATH - Wire cannot be rendered!")

    # Check component positions
    print("\n" + "=" * 60)
    print("COMPONENT POSITION ANALYSIS")
    print("=" * 60)

    components_with_positions = sum(
        1 for c in diagram.components
        if c.x != 0 or c.y != 0 or c.page_positions
    )

    print(f"Components with positions: {components_with_positions}/{len(diagram.components)}")

    # Check if wire endpoints have positions
    print("\nWire endpoint analysis:")
    wires_with_positioned_endpoints = 0

    for wire in diagram.wires:
        from_comp = next((c for c in diagram.components if c.id == wire.from_component_id), None)
        to_comp = next((c for c in diagram.components if c.id == wire.to_component_id), None)

        has_from = from_comp and (from_comp.x != 0 or from_comp.y != 0 or from_comp.page_positions)
        has_to = to_comp and (to_comp.x != 0 or to_comp.y != 0 or to_comp.page_positions)

        if has_from and has_to:
            wires_with_positioned_endpoints += 1

    print(f"  Wires with both endpoints positioned: {wires_with_positioned_endpoints}/{len(diagram.wires)}")

    # Root cause diagnosis
    print("\n" + "=" * 60)
    print("DIAGNOSIS")
    print("=" * 60)

    if wires_without_paths == len(diagram.wires):
        print("ROOT CAUSE: All wires lack path data!")
        print("\nThe wires are loaded from DRAWER cable routing tables,")
        print("but their 'path' field is empty/None.")
        print("\nThis means:")
        print("  1. Wire data exists (from_component, to_component, voltage)")
        print("  2. But visual path (list of x,y points) is missing")
        print("  3. pdf_viewer._draw_wires() skips wires without paths")
        print("\nFIX NEEDED:")
        print("  - Generate wire paths after loading DRAWER diagram")
        print("  - Use component positions to create visual paths")
        print(f"  - Can generate paths for {wires_with_positioned_endpoints} wires")
    elif wires_with_paths > 0:
        print(f"PARTIAL SUCCESS: {wires_with_paths} wires have paths")
        print(f"  - {wires_without_paths} still need path generation")
else:
    print("\nNo wires found in diagram!")
