#!/usr/bin/env python3
"""Debug why wire paths aren't being generated."""

from pathlib import Path
from electrical_schematics.pdf.auto_loader import DiagramAutoLoader

pdf_path = Path("/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf")
diagram, format_type = DiagramAutoLoader.load_diagram(pdf_path)

print(f"Total wires: {len(diagram.wires)}")
print(f"Total components: {len(diagram.components)}")
print()

# Check which components have positions
components_with_pos = {}
for comp in diagram.components:
    has_pos = (comp.x != 0.0 or comp.y != 0.0)
    components_with_pos[comp.id] = has_pos

print(f"Components with positions: {sum(components_with_pos.values())}/{len(diagram.components)}")
print()

# Check which wires have both components with positions
wires_with_both_pos = 0
wires_missing_src = []
wires_missing_tgt = []

for wire in diagram.wires:
    src_has_pos = components_with_pos.get(wire.from_component_id, False)
    tgt_has_pos = components_with_pos.get(wire.to_component_id, False)

    if src_has_pos and tgt_has_pos:
        wires_with_both_pos += 1
    else:
        if not src_has_pos:
            wires_missing_src.append((wire.from_component_id, wire.id))
        if not tgt_has_pos:
            wires_missing_tgt.append((wire.to_component_id, wire.id))

print(f"Wires with both endpoints positioned: {wires_with_both_pos}/{len(diagram.wires)}")
print(f"Wires missing source position: {len(wires_missing_src)}")
print(f"Wires missing target position: {len(wires_missing_tgt)}")
print()

# Show unique missing components
unique_missing_src = set(c[0] for c in wires_missing_src)
unique_missing_tgt = set(c[0] for c in wires_missing_tgt)
all_missing = unique_missing_src | unique_missing_tgt

print(f"Unique missing component IDs: {sorted(all_missing)}")
print()

# Show all component IDs
print("All component IDs in diagram:")
for comp in sorted(diagram.components, key=lambda c: c.id):
    has_pos = components_with_pos[comp.id]
    pos_str = f"({comp.x:.1f}, {comp.y:.1f})" if has_pos else "NO POSITION"
    print(f"  {comp.id:15s} {pos_str}")
