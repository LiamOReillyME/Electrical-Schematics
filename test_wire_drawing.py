"""Test wire drawing functionality."""

from pathlib import Path
from PySide6.QtCore import QPointF
from electrical_schematics.models import WiringDiagram, IndustrialComponent, IndustrialComponentType
from electrical_schematics.gui.wire_tool import WireDrawingTool, WireType

def test_wire_drawing():
    """Test wire drawing with terminal detection."""
    print("=== TEST 3: Wire Drawing ===")

    # Create test diagram with 2 components
    comp1 = IndustrialComponent(
        id="K1",
        type=IndustrialComponentType.CONTACTOR,
        designation="K1",
        x=100.0,
        y=100.0,
        width=40.0,
        height=30.0
    )

    comp2 = IndustrialComponent(
        id="S1",
        type=IndustrialComponentType.PHOTOELECTRIC_SENSOR,
        designation="S1",
        x=200.0,
        y=100.0,
        width=40.0,
        height=30.0
    )

    diagram = WiringDiagram(
        name="test",
        components=[comp1, comp2],
        wires=[]
    )

    # Initialize wire tool
    wire_tool = WireDrawingTool()
    wire_tool.set_wire_type(WireType.DC_24V)

    print(f"✓ Wire tool initialized")
    print(f"✓ Wire type: {WireType.DC_24V.value}")

    # Get terminal positions
    terminals = {}
    for comp in diagram.components:
        comp_terminals = wire_tool._get_component_terminals(comp)
        terminals[comp.id] = comp_terminals
        print(f"✓ Component {comp.designation}: {len(comp_terminals)} terminals")

    # Simulate wire drawing: start at K1 terminal
    from PySide6.QtCore import QPointF
    start_pos = QPointF(105.0, 100.0)  # Near K1 first terminal

    # Test terminal detection
    all_terminals = {}
    for comp in diagram.components:
        for term_id, term_pos in wire_tool._get_component_terminals(comp).items():
            all_terminals[term_id] = (comp, term_pos)

    detected = wire_tool._find_terminal_at(start_pos, diagram.components, all_terminals)

    if detected:
        comp, term_id = detected
        print(f"✓ Terminal detected: {comp.designation}.{term_id}")
    else:
        print(f"❌ FAIL: No terminal detected at start position")
        return False

    # Start wire
    handled = wire_tool.handle_click(start_pos, diagram.components, all_terminals)
    print(f"✓ Wire drawing started: {handled}")

    if not wire_tool.is_drawing():
        print("❌ FAIL: Wire tool not in drawing state")
        return False

    # Add waypoint
    waypoint = QPointF(150.0, 150.0)
    wire_tool.handle_click(waypoint, diagram.components, all_terminals)
    print("✓ Waypoint added")

    # End at S1 terminal
    end_pos = QPointF(205.0, 100.0)
    wire_tool.handle_click(end_pos, diagram.components, all_terminals)

    if wire_tool.last_created_wire:
        print(f"✓ Wire created with {len(wire_tool.last_created_wire.path)} points")
        print(f"  From: {wire_tool.last_created_wire.from_component_id}")
        print(f"  To: {wire_tool.last_created_wire.to_component_id}")
        print("\n=== TEST 3: PASSED ===")
        return True
    else:
        print("❌ FAIL: Wire not created")
        return False

if __name__ == "__main__":
    import sys
    success = test_wire_drawing()
    sys.exit(0 if success else 1)
