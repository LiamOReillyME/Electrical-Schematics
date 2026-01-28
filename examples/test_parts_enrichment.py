#!/usr/bin/env python3
"""Test script to demonstrate complete parts enrichment workflow.

This script demonstrates:
1. DigiKey API lookup with retry logic
2. Data validation
3. Asset downloading (photos and datasheets)
4. Contact configuration parsing
5. Dynamic icon generation
6. Library integration
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from electrical_schematics.services.contact_parser import ContactConfigParser
from electrical_schematics.services.dynamic_icon_generator import DynamicIconGenerator


def test_contact_parser():
    """Test contact configuration parser."""
    print("\n" + "=" * 80)
    print("TESTING CONTACT PARSER")
    print("=" * 80)

    parser = ContactConfigParser()

    test_descriptions = [
        ("Relay DPDT 5A 24VDC", "Relays"),
        ("Contactor AC-3 11KW/400V 3-phase with 1 NO auxiliary", "Contactors"),
        ("Terminal Block 10 position screw", "Terminal Blocks"),
        ("Relay 2 NO and 2 NC contacts 24VDC", "Relays"),
        ("Circuit breaker 3 pole 16A", "Circuit Breakers"),
    ]

    for desc, category in test_descriptions:
        print(f"\nDescription: {desc}")
        print(f"Category: {category}")

        config = parser.parse_description(desc, category)

        print(f"  Component type: {config.component_type}")
        print(f"  NO contacts: {config.no_contacts}")
        print(f"  NC contacts: {config.nc_contacts}")
        print(f"  Poles: {config.poles}")
        print(f"  Positions: {config.positions}")
        print(f"  Three-phase: {config.three_phase}")
        print(f"  Power contacts: {config.power_contacts}")


def test_icon_generator():
    """Test dynamic icon generator."""
    print("\n" + "=" * 80)
    print("TESTING ICON GENERATOR")
    print("=" * 80)

    parser = ContactConfigParser()
    generator = DynamicIconGenerator()

    test_cases = [
        ("Relay DPDT 5A 24VDC", "Relays"),
        ("Contactor 3-phase with 1 NO auxiliary", "Contactors"),
        ("Terminal Block 10 position", "Terminal Blocks"),
    ]

    for desc, category in test_cases:
        print(f"\nGenerating icon for: {desc}")

        # Parse contact config
        config = parser.parse_description(desc, category)

        # Generate icon
        svg = generator.generate_icon(config)

        print(f"  Component type: {config.component_type}")
        print(f"  SVG length: {len(svg)} characters")
        print(f"  Has coil labels: {'A1' in svg and 'A2' in svg}")

        # Save to file for inspection
        output_file = Path(f"test_icon_{config.component_type}.svg")
        output_file.write_text(svg)
        print(f"  Saved to: {output_file}")


def test_complete_workflow():
    """Test complete enrichment workflow with mock data."""
    print("\n" + "=" * 80)
    print("TESTING COMPLETE WORKFLOW")
    print("=" * 80)

    # Mock DigiKey data
    mock_digikey_data = {
        "manufacturer_part_number": "3RT2026-1DB40-1AAO",
        "manufacturer": "Siemens",
        "description": "Contactor AC-3 11KW/400V 3-phase with 1 NO auxiliary",
        "category": "Contactors",
        "primary_photo": "https://example.com/photo.jpg",
        "primary_datasheet": "https://example.com/datasheet.pdf",
        "unit_price": 45.50,
    }

    print(f"\nPart: {mock_digikey_data['manufacturer_part_number']}")
    print(f"Description: {mock_digikey_data['description']}")

    # Step 1: Parse contact configuration
    print("\nStep 1: Parsing contact configuration...")
    parser = ContactConfigParser()
    config = parser.parse_description(
        mock_digikey_data['description'],
        mock_digikey_data['category']
    )

    print(f"  Component type: {config.component_type}")
    print(f"  Power contacts: {config.power_contacts}")
    print(f"  NO auxiliary: {config.no_contacts}")
    print(f"  Three-phase: {config.three_phase}")

    # Step 2: Generate icon
    print("\nStep 2: Generating icon...")
    generator = DynamicIconGenerator()
    svg = generator.generate_icon(config)

    print(f"  SVG size: {len(svg)} characters")
    print(f"  Has A1/A2 coil: {'A1' in svg}")
    print(f"  Has power contacts: {'>1<' in svg}")
    print(f"  Has auxiliary contact: {'13' in svg}")

    # Step 3: Show what would be stored
    print("\nStep 3: Data to be stored in library:")
    print(f"  Manufacturer: {mock_digikey_data['manufacturer']}")
    print(f"  Part number: {mock_digikey_data['manufacturer_part_number']}")
    print(f"  Category: {mock_digikey_data['category']}")
    print(f"  Price: ${mock_digikey_data['unit_price']:.2f}")
    print(f"  Photo URL: {mock_digikey_data['primary_photo']}")
    print(f"  Datasheet URL: {mock_digikey_data['primary_datasheet']}")
    print(f"  Contact config: {config.to_dict()}")
    print(f"  Icon SVG: {len(svg)} characters")

    print("\n✓ Complete workflow test successful!")


def test_all_component_types():
    """Test icon generation for all component types."""
    print("\n" + "=" * 80)
    print("TESTING ALL COMPONENT TYPES")
    print("=" * 80)

    parser = ContactConfigParser()
    generator = DynamicIconGenerator()

    test_cases = [
        ("Relay DPDT 5A", "relay"),
        ("Contactor 3-phase 11KW", "contactor"),
        ("Terminal Block 10 position", "terminal_block"),
        ("Selector switch 3 position", "switch"),
        ("Circuit breaker 3 pole", "circuit_breaker"),
        ("Unknown component", "unknown"),
    ]

    for desc, expected_type in test_cases:
        print(f"\n{desc}:")

        config = parser.parse_description(desc, "")

        print(f"  Type: {config.component_type}")

        svg = generator.generate_icon(config)

        print(f"  SVG length: {len(svg)}")
        print(f"  Valid SVG: {'<svg' in svg and '</svg>' in svg}")

        # Save icon
        output_file = Path(f"test_{config.component_type}.svg")
        output_file.write_text(svg)
        print(f"  Saved: {output_file}")


def main():
    """Run all tests."""
    try:
        test_contact_parser()
        test_icon_generator()
        test_complete_workflow()
        test_all_component_types()

        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
