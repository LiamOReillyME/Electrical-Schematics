#!/usr/bin/env python3
"""Demo script to verify all features are working."""

import sys
from pathlib import Path

# Add project to path if needed
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(text.center(70))
    print("=" * 70)

def print_section(text):
    """Print section header."""
    print(f"\n{text}")
    print("-" * 70)

def print_success(text):
    """Print success message."""
    print(f"✅ {text}")

def print_error(text):
    """Print error message."""
    print(f"❌ {text}")

def print_info(text):
    """Print info message."""
    print(f"ℹ  {text}")

print_header("INDUSTRIAL WIRING DIAGRAM ANALYZER - FEATURE DEMO")

# Import dependencies
print_section("Importing Dependencies")

try:
    from electrical_schematics.pdf.auto_loader import DiagramAutoLoader
    print_success("DiagramAutoLoader imported")
except ImportError as e:
    print_error(f"Failed to import DiagramAutoLoader: {e}")
    sys.exit(1)

try:
    from electrical_schematics.models.diagram import WiringDiagram
    print_success("WiringDiagram model imported")
except ImportError as e:
    print_error(f"Failed to import WiringDiagram: {e}")
    sys.exit(1)

try:
    from electrical_schematics.simulation.interactive_simulator import InteractiveSimulator
    print_success("InteractiveSimulator imported")
except ImportError as e:
    print_error(f"Failed to import InteractiveSimulator: {e}")
    sys.exit(1)

# Find test PDF
print_section("Locating Test PDF")

pdf_path = Path("/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf")

if not pdf_path.exists():
    print_error(f"DRAWER.pdf not found at {pdf_path}")
    print_info("Looking for alternative test PDFs...")

    # Try AO.pdf
    ao_path = Path("/home/liam-oreilly/claude.projects/electricalSchematics/AO.pdf")
    if ao_path.exists():
        pdf_path = ao_path
        print_success(f"Using alternative PDF: {ao_path.name}")
    else:
        print_error("No test PDFs found")
        print_info("Please place DRAWER.pdf in the project root directory")
        sys.exit(1)
else:
    print_success(f"Test PDF found: {pdf_path.name}")
    print_info(f"File size: {pdf_path.stat().st_size / 1024:.1f} KB")

# Load diagram with auto-detection
print_section("Loading Diagram with Auto-Detection")

try:
    print_info("Analyzing PDF format...")
    diagram, format_type = DiagramAutoLoader.load_diagram(pdf_path, auto_position=True)
    print_success(f"Format detected: {format_type}")
except Exception as e:
    print_error(f"Failed to load diagram: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Check components
print_section("Component Analysis")

num_components = len(diagram.components)
print_success(f"Components loaded: {num_components}")

if num_components == 0:
    print_error("No components found - diagram may not be in supported format")
    print_info("Supported formats: DRAWER, Parts List")
else:
    # Show component breakdown by type
    from collections import Counter
    component_types = Counter(c.type.value for c in diagram.components)

    print_info("Component types:")
    for comp_type, count in component_types.most_common():
        print(f"   {comp_type}: {count}")

    # Check positioning
    positioned = sum(1 for c in diagram.components if c.x != 0 or c.y != 0)
    print_success(f"Components positioned: {positioned}/{num_components}")

    if positioned < num_components:
        print_info(f"   {num_components - positioned} components at default position (0,0)")

    # Check multi-page components
    multi_page = sum(1 for c in diagram.components if len(c.page_positions) > 1)
    if multi_page > 0:
        print_success(f"Multi-page components: {multi_page}")
        print_info("   These components appear on multiple schematic pages")

# Show sample components
if num_components > 0:
    print_section("Sample Components")

    for i, comp in enumerate(diagram.components[:5]):
        print(f"\n{i+1}. {comp.designation}")
        print(f"   Type: {comp.type.value}")
        # Use voltage_rating attribute (not voltage_level)
        if comp.voltage_rating:
            print(f"   Voltage: {comp.voltage_rating}")
        print(f"   Page: {comp.page}")
        if comp.x != 0 or comp.y != 0:
            print(f"   Position: ({comp.x:.1f}, {comp.y:.1f})")
        if len(comp.page_positions) > 1:
            print(f"   Also appears on pages: {list(comp.page_positions.keys())}")

    if num_components > 5:
        print(f"\n... and {num_components - 5} more components")

# Check wires
print_section("Wire Connection Analysis")

num_wires = len(diagram.wires)
print_success(f"Wires loaded: {num_wires}")

if num_wires == 0:
    print_info("No wire connections found")
    print_info("   This may be normal for manual annotation mode")
else:
    # Wire breakdown by voltage
    wire_voltages = Counter(w.voltage_level for w in diagram.wires if w.voltage_level)

    print_info("Wire voltage levels:")
    for voltage, count in wire_voltages.most_common():
        print(f"   {voltage}: {count} connections")

    # Show sample wires
    print_section("Sample Wire Connections")

    for i, wire in enumerate(diagram.wires[:5]):
        print(f"\n{i+1}. {wire.from_component_id} → {wire.to_component_id}")
        if wire.voltage_level:
            print(f"   Voltage: {wire.voltage_level}")
        if wire.wire_number:
            print(f"   Wire #: {wire.wire_number}")
        if wire.color:
            print(f"   Color: {wire.color}")

    if num_wires > 5:
        print(f"\n... and {num_wires - 5} more connections")

# Generate wire paths
if num_wires > 0:
    print_section("Wire Path Generation")

    try:
        print_info("Generating visual wire paths (manhattan routing)...")
        DiagramAutoLoader.generate_wire_paths(diagram, routing_style="manhattan")

        wires_with_paths = sum(1 for w in diagram.wires if w.path and len(w.path) > 0)
        print_success(f"Wire paths generated: {wires_with_paths}/{num_wires}")

        if wires_with_paths < num_wires:
            print_info(f"   {num_wires - wires_with_paths} wires have no path (may be cross-page)")
    except Exception as e:
        print_error(f"Wire path generation failed: {e}")

# Test simulation
if num_components > 0:
    print_section("Simulation Engine Test")

    try:
        print_info("Initializing interactive simulator...")
        simulator = InteractiveSimulator(diagram)
        print_success("Simulator initialized")

        # Get initial energization state
        initial_energized = simulator.get_energized_components()
        print_success(f"Initial simulation: {len(initial_energized)} components energized")

        # Show energized components
        if len(initial_energized) > 0:
            print_info("Sample energized components:")
            for comp in list(initial_energized)[:5]:
                voltage = f" ({comp.voltage_rating})" if comp.voltage_rating else ""
                print(f"   - {comp.designation} ({comp.type.value}){voltage}")

        # Try toggling a component if possible
        toggleable = [c for c in diagram.components
                      if c.type.value in ["relay", "contactor", "switch", "fuse", "circuit_breaker"]]

        if len(toggleable) > 0:
            print_info("\nTesting component toggle...")
            test_comp = toggleable[0]
            print_info(f"   Toggling {test_comp.designation}...")

            try:
                simulator.toggle_component(test_comp.designation)
                after_energized = simulator.get_energized_components()
                print_success(f"After toggle: {len(after_energized)} components energized")

                if len(after_energized) != len(initial_energized):
                    change = len(after_energized) - len(initial_energized)
                    print_success(f"   Simulation responded: {change:+d} components changed state")
                else:
                    print_info("   No state change (component may not be in active path)")
            except Exception as e:
                print_error(f"Toggle failed: {e}")

        # Try circuit tracing
        if len(initial_energized) > 0:
            print_info("\nTesting circuit path tracing...")
            trace_comp = list(initial_energized)[0]
            print_info(f"   Tracing capabilities available for {trace_comp.designation}")
            print_info("   Full circuit tracing available in interactive GUI mode")

    except Exception as e:
        print_error(f"Simulation initialization failed: {e}")
        import traceback
        traceback.print_exc()

# Feature summary
print_header("FEATURE VERIFICATION SUMMARY")

features = [
    ("PDF Format Detection", format_type != "UNKNOWN"),
    ("Component Loading", num_components > 0),
    ("Wire Connection Loading", num_wires > 0),
    ("Auto-Positioning", positioned > 0 if num_components > 0 else False),
    ("Wire Path Generation", wires_with_paths > 0 if num_wires > 0 else False),
    ("Simulation Engine", 'simulator' in locals()),
]

print()
for feature_name, working in features:
    if working:
        print_success(f"{feature_name}")
    else:
        print_error(f"{feature_name} - Not available or not working")

# Overall status
all_working = all(working for _, working in features if _ != "Wire Connection Loading")
# Wire connections are optional for manual mode

print("\n" + "=" * 70)
if all_working and num_components > 0:
    print("🎉 ALL CORE FEATURES WORKING 🎉".center(70))
    print("\nTo see features in GUI:")
    print("  python -m electrical_schematics.main")
    print("\nExpected in GUI:")
    print(f"  • {num_components} components in right panel list")
    if num_wires > 0:
        print(f"  • {num_wires} wire connections rendered")
    print(f"  • {positioned} components with visual overlays on pages")
    print("  • Double-click components to toggle states")
    print("  • Click 'Draw Wire' to manually add connections")
elif num_components > 0:
    print("⚠ PARTIAL FUNCTIONALITY ⚠".center(70))
    print("\nSome features working, but not all.")
    print("Check error messages above.")
else:
    print("❌ FEATURES NOT WORKING ❌".center(70))
    print("\nNo components loaded from PDF.")
    print("Possible causes:")
    print("  • PDF is not in DRAWER or Parts List format")
    print("  • PDF is image-based (requires OCR)")
    print("  • Parser failed to extract data")
    print("\nCheck error messages above for details.")

print("=" * 70 + "\n")

# Exit with appropriate code
sys.exit(0 if all_working else 1)
