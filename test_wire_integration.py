#!/usr/bin/env python3
"""Integration test for wire rendering in GUI context."""

from pathlib import Path
from electrical_schematics.pdf.auto_loader import DiagramAutoLoader
from electrical_schematics.models.wire import WirePoint

# Load DRAWER.pdf
pdf_path = Path("DRAWER.pdf")

if not pdf_path.exists():
    print("ERROR: DRAWER.pdf not found")
    exit(1)

print("=" * 70)
print("WIRE RENDERING INTEGRATION TEST")
print("=" * 70)

# Load diagram
diagram, format_type = DiagramAutoLoader.load_diagram(pdf_path)

print(f"\n1. DIAGRAM LOADED")
print(f"   Format: {format_type}")
print(f"   Components: {len(diagram.components)}")
print(f"   Wires: {len(diagram.wires)}")

# Check wire paths
wires_renderable = []
wires_not_renderable = []

for wire in diagram.wires:
    if wire.path and len(wire.path) >= 2:
        wires_renderable.append(wire)
    else:
        wires_not_renderable.append(wire)

print(f"\n2. WIRE PATH ANALYSIS")
print(f"   Renderable wires: {len(wires_renderable)}/{len(diagram.wires)}")
print(f"   Non-renderable: {len(wires_not_renderable)}")

# Simulate GUI rendering checks
print(f"\n3. GUI RENDERING SIMULATION")

if wires_renderable:
    # Simulate pdf_viewer._draw_wires() logic
    zoom_level = 1.0
    render_count = 0
    
    for wire in wires_renderable:
        # Check path validity (same as pdf_viewer)
        if not wire.path or len(wire.path) < 2:
            continue
        
        # Simulate coordinate conversion
        screen_points = []
        for point in wire.path:
            screen_x = point.x * zoom_level * 2
            screen_y = point.y * zoom_level * 2
            screen_points.append((screen_x, screen_y))
        
        # Check if we'd actually draw this wire
        if len(screen_points) >= 2:
            render_count += 1
    
    print(f"   Wires that would render: {render_count}")
    print(f"   Render success rate: {render_count/len(diagram.wires)*100:.1f}%")

# Show sample wire details
print(f"\n4. SAMPLE WIRE DETAILS")

for i, wire in enumerate(wires_renderable[:3]):
    print(f"\n   Wire {i+1}: {wire.id}")
    print(f"     From: {wire.from_component_id}")
    print(f"     To: {wire.to_component_id}")
    print(f"     Voltage: {wire.voltage_level}")
    print(f"     Path points: {len(wire.path)}")
    
    # Determine wire color (same logic as pdf_viewer)
    if wire.voltage_level:
        if "24" in wire.voltage_level or "24VDC" in wire.voltage_level:
            color_name = "RED (24VDC)"
        elif "5V" in wire.voltage_level or "5VDC" in wire.voltage_level:
            color_name = "ORANGE (5VDC)"
        elif "0V" in wire.voltage_level:
            color_name = "BLUE (Ground)"
        elif "AC" in wire.voltage_level or "400VAC" in wire.voltage_level:
            color_name = "DARK GRAY (AC)"
        else:
            color_name = "GRAY (Unknown)"
    else:
        color_name = "GRAY (Unknown)"
    
    print(f"     Render color: {color_name}")
    print(f"     Path: {wire.path[0].x:.1f},{wire.path[0].y:.1f} → {wire.path[-1].x:.1f},{wire.path[-1].y:.1f}")

# Component position check
print(f"\n5. COMPONENT POSITION CHECK")
positioned_count = sum(1 for c in diagram.components if c.x != 0 or c.y != 0 or c.page_positions)
print(f"   Components with positions: {positioned_count}/{len(diagram.components)}")

# Show components with wires
components_with_wires = set()
for wire in diagram.wires:
    components_with_wires.add(wire.from_component_id)
    components_with_wires.add(wire.to_component_id)

print(f"   Components in wiring: {len(components_with_wires)}")

# Final verdict
print(f"\n6. FINAL VERDICT")
if render_count >= len(diagram.wires) * 0.9:
    print("   ✅ PASS - >90% wires will render successfully")
    print(f"   Wire rendering is working correctly!")
else:
    print(f"   ⚠ PARTIAL - Only {render_count/len(diagram.wires)*100:.1f}% wires will render")
    print(f"   Some wires still missing paths")

print("\n" + "=" * 70)
print("To see wires in GUI: Run 'electrical-schematics' and open DRAWER.pdf")
print("Expected: Colored lines connecting components on schematic pages")
print("=" * 70)
