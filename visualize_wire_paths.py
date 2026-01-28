#!/usr/bin/env python3
"""Visualize wire paths in ASCII for documentation."""

from pathlib import Path
from electrical_schematics.pdf.auto_loader import DiagramAutoLoader

def draw_wire_path_ascii(wire, scale=0.02):
    """Draw a simple ASCII representation of a wire path."""
    if not wire.path or len(wire.path) < 2:
        return "No path available"
    
    # Get bounds
    xs = [p.x for p in wire.path]
    ys = [p.y for p in wire.path]
    
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    
    # Normalize to ASCII grid
    width = 60
    height = 20
    
    grid = [[' ' for _ in range(width)] for _ in range(height)]
    
    # Plot path
    for i in range(len(wire.path) - 1):
        p1 = wire.path[i]
        p2 = wire.path[i + 1]
        
        # Convert to grid coordinates
        x1 = int((p1.x - min_x) / (max_x - min_x + 1) * (width - 1)) if max_x > min_x else 0
        y1 = int((p1.y - min_y) / (max_y - min_y + 1) * (height - 1)) if max_y > min_y else 0
        x2 = int((p2.x - min_x) / (max_x - min_x + 1) * (width - 1)) if max_x > min_x else 0
        y2 = int((p2.y - min_y) / (max_y - min_y + 1) * (height - 1)) if max_y > min_y else 0
        
        # Draw line
        if x1 == x2:  # Vertical line
            for y in range(min(y1, y2), max(y1, y2) + 1):
                grid[y][x1] = '|'
        elif y1 == y2:  # Horizontal line
            for x in range(min(x1, x2), max(x1, x2) + 1):
                grid[y1][x] = '-'
        
        # Mark connection points
        grid[y1][x1] = '+'
        grid[y2][x2] = '+'
    
    # Convert to string
    return '\n'.join(''.join(row) for row in grid)

# Load diagram
pdf_path = Path("DRAWER.pdf")
if pdf_path.exists():
    diagram, _ = DiagramAutoLoader.load_diagram(pdf_path)
    
    print("=" * 70)
    print("WIRE PATH VISUALIZATION")
    print("=" * 70)
    
    # Show 3 different wire examples
    sample_wires = [w for w in diagram.wires if w.path and len(w.path) >= 2][:3]
    
    for i, wire in enumerate(sample_wires, 1):
        print(f"\nWire {i}: {wire.id}")
        print(f"From: {wire.from_component_id} → To: {wire.to_component_id}")
        print(f"Voltage: {wire.voltage_level}")
        print(f"Path type: Manhattan (orthogonal)")
        print(f"Points: {len(wire.path)}")
        
        # Show coordinates
        print("\nPath coordinates:")
        for j, point in enumerate(wire.path):
            marker = "START" if j == 0 else "END" if j == len(wire.path)-1 else f"MID{j}"
            print(f"  [{marker}] ({point.x:.1f}, {point.y:.1f})")
        
        print("\nVisual representation:")
        print(draw_wire_path_ascii(wire))
        print("-" * 70)
    
    # Summary statistics
    total_path_points = sum(len(w.path) for w in diagram.wires if w.path)
    avg_points = total_path_points / len([w for w in diagram.wires if w.path])
    
    print(f"\nSTATISTICS:")
    print(f"  Total wires: {len(diagram.wires)}")
    print(f"  Wires with paths: {len([w for w in diagram.wires if w.path])}")
    print(f"  Total path points: {total_path_points}")
    print(f"  Average points per wire: {avg_points:.1f}")
    print(f"  Routing style: Manhattan (4 points typical)")
    
else:
    print("DRAWER.pdf not found")
