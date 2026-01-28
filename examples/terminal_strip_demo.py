"""Demo script for terminal strip functionality.

This script demonstrates:
1. Loading terminal strips from library
2. Creating custom terminal strips
3. Generating SVG icons
4. Exporting preview HTML
"""

import json
from pathlib import Path

from electrical_schematics.models.terminal_strip import (
    TerminalStrip,
    TerminalStripType,
    TerminalColor
)
from electrical_schematics.gui.terminal_strip_icon import (
    TerminalStripIconGenerator,
    generate_preview_grid
)


def load_library_terminals():
    """Load terminal strips from the library JSON."""
    config_dir = Path(__file__).parent.parent / "electrical_schematics" / "config"
    library_file = config_dir / "terminal_strips_library.json"

    if not library_file.exists():
        print(f"Error: Library file not found at {library_file}")
        return []

    with open(library_file, 'r') as f:
        data = json.load(f)

    print(f"Loaded library version {data['version']}")
    print(f"Found {len(data['terminal_strips'])} terminal strips\n")

    terminal_strips = []
    for ts_data in data['terminal_strips']:
        # Convert dict to TerminalStrip
        strip = TerminalStrip(
            designation=ts_data['designation'],
            terminal_type=TerminalStripType(ts_data['terminal_type']),
            position_count=ts_data['position_count'],
            level_count=ts_data.get('level_count', 1),
            manufacturer=ts_data.get('manufacturer', ''),
            part_number=ts_data.get('part_number', ''),
            series=ts_data.get('series', ''),
            description=ts_data.get('description', ''),
            wire_gauge_min=ts_data.get('wire_gauge_min', '24 AWG'),
            wire_gauge_max=ts_data.get('wire_gauge_max', '12 AWG'),
            wire_size_min_mm2=ts_data.get('wire_size_min_mm2', 0.5),
            wire_size_max_mm2=ts_data.get('wire_size_max_mm2', 2.5),
            voltage_rating=ts_data.get('voltage_rating', '300V'),
            current_rating=ts_data.get('current_rating', '24A'),
            color=TerminalColor(ts_data.get('color', 'gray')),
            has_fuse=ts_data.get('has_fuse', False),
            fuse_type=ts_data.get('fuse_type'),
            has_disconnect=ts_data.get('has_disconnect', False),
            has_led=ts_data.get('has_led', False),
            led_voltage=ts_data.get('led_voltage'),
            digikey_part_number=ts_data.get('digikey_part_number'),
            digikey_url=ts_data.get('digikey_url'),
            unit_price=ts_data.get('unit_price'),
            stock_quantity=ts_data.get('stock_quantity'),
            din_rail_width_mm=ts_data.get('din_rail_width_mm', 5.2),
            height_mm=ts_data.get('height_mm', 41.0),
            depth_mm=ts_data.get('depth_mm', 32.0)
        )
        terminal_strips.append(strip)

    return terminal_strips


def demonstrate_terminal_strip_features():
    """Demonstrate terminal strip features."""
    print("=" * 70)
    print("TERMINAL STRIP DEMONSTRATION")
    print("=" * 70)
    print()

    # Load from library
    print("1. Loading Terminal Strips from Library")
    print("-" * 70)
    strips = load_library_terminals()

    if not strips:
        print("No terminal strips loaded. Exiting.")
        return

    # Display summary
    print(f"\nTotal terminal strips: {len(strips)}")
    print("\nTypes available:")
    type_counts = {}
    for strip in strips:
        type_name = strip.terminal_type.value
        type_counts[type_name] = type_counts.get(type_name, 0) + 1

    for type_name, count in sorted(type_counts.items()):
        print(f"  - {type_name.replace('_', ' ').title()}: {count}")

    print("\n" + "=" * 70)
    print("2. Sample Terminal Strips")
    print("-" * 70)

    # Show details for a few representative strips
    sample_types = [
        TerminalStripType.FEED_THROUGH,
        TerminalStripType.GROUND,
        TerminalStripType.FUSE,
        TerminalStripType.MULTI_LEVEL,
        TerminalStripType.LED_INDICATOR
    ]

    for strip_type in sample_types:
        matching = [s for s in strips if s.terminal_type == strip_type]
        if matching:
            strip = matching[0]
            print(f"\n{strip}")
            print(f"  Manufacturer: {strip.manufacturer}")
            print(f"  Part Number: {strip.part_number}")
            print(f"  DigiKey SKU: {strip.digikey_part_number}")
            print(f"  Price: ${strip.unit_price:.2f}" if strip.unit_price else "  Price: N/A")
            print(f"  Terminals: {strip.get_terminal_count()}")
            print(f"  Wire Range: {strip.wire_gauge_min} to {strip.wire_gauge_max}")

            # Show terminal numbering
            if strip.get_terminal_count() <= 6:
                terminal_numbers = [t.terminal_number for t in strip.terminals]
                print(f"  Terminal Numbers: {', '.join(terminal_numbers)}")

    print("\n" + "=" * 70)
    print("3. Creating Custom Terminal Strips")
    print("-" * 70)

    # Create a custom 10-position feed-through
    custom_strip = TerminalStrip(
        designation="X100",
        terminal_type=TerminalStripType.FEED_THROUGH,
        position_count=10,
        manufacturer="Custom",
        part_number="CUSTOM-10POS",
        description="Custom 10-position terminal strip"
    )

    print(f"\nCreated custom strip: {custom_strip}")
    print(f"Total terminals: {custom_strip.get_terminal_count()}")
    print(f"Terminal numbers: {', '.join([t.terminal_number for t in custom_strip.terminals[:5]])}...")

    print("\n" + "=" * 70)
    print("4. Terminal Numbering Examples")
    print("-" * 70)

    # Single-level
    single = TerminalStrip("X1", TerminalStripType.FEED_THROUGH, position_count=4)
    print(f"\nSingle-level (4-pos): {[t.terminal_number for t in single.terminals]}")

    # Multi-level
    multi = TerminalStrip("X20", TerminalStripType.MULTI_LEVEL, position_count=2, level_count=3)
    print(f"Multi-level (2-pos, 3-level): {[t.terminal_number for t in multi.terminals]}")

    print("\n" + "=" * 70)
    print("5. SVG Icon Generation")
    print("-" * 70)

    # Generate SVG for a sample terminal
    feed_through = strips[0]
    svg = TerminalStripIconGenerator.generate_svg(feed_through, width=200, height=80)
    print(f"\nGenerated SVG for {feed_through.designation}:")
    print(f"  SVG length: {len(svg)} characters")
    print(f"  Contains DIN rail: {'din-rail' in svg}")
    print(f"  Contains terminal positions: {'position-' in svg}")
    print(f"  Contains designation label: {feed_through.designation in svg}")

    # Save individual SVG
    output_dir = Path(__file__).parent.parent / "examples" / "output"
    output_dir.mkdir(exist_ok=True)

    svg_file = output_dir / f"terminal_strip_{feed_through.designation}.svg"
    with open(svg_file, 'w') as f:
        f.write(svg)
    print(f"  Saved to: {svg_file}")

    print("\n" + "=" * 70)
    print("6. Generating HTML Preview Grid")
    print("-" * 70)

    # Generate HTML preview for all strips
    html = generate_preview_grid(strips[:15])  # First 15 strips
    html_file = output_dir / "terminal_strips_preview.html"

    with open(html_file, 'w') as f:
        f.write(html)

    print(f"\nGenerated HTML preview with {min(15, len(strips))} terminal strips")
    print(f"Saved to: {html_file}")
    print(f"\nOpen this file in a web browser to view the terminal strip library.")

    print("\n" + "=" * 70)
    print("7. DigiKey Integration Summary")
    print("-" * 70)

    with_digikey = [s for s in strips if s.digikey_part_number]
    print(f"\nTotal strips: {len(strips)}")
    print(f"With DigiKey SKU: {len(with_digikey)}")

    if with_digikey:
        total_value = sum(s.unit_price for s in with_digikey if s.unit_price)
        avg_price = total_value / len(with_digikey) if with_digikey else 0
        print(f"Average price: ${avg_price:.2f}")

        # Show price range
        prices = [s.unit_price for s in with_digikey if s.unit_price]
        if prices:
            print(f"Price range: ${min(prices):.2f} - ${max(prices):.2f}")

    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)


def main():
    """Run the demonstration."""
    try:
        demonstrate_terminal_strip_features()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
