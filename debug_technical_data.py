"""Debug technical data extraction."""

from pathlib import Path
from electrical_schematics.pdf.exact_parts_parser import parse_parts_list

def debug_technical_data():
    """Show raw technical data from parser."""
    pdf_path = Path('/home/liam-oreilly/claude.projects/electricalSchematics/AO.pdf')

    print("=" * 70)
    print("DEBUGGING TECHNICAL DATA EXTRACTION")
    print("=" * 70)

    parts = parse_parts_list(pdf_path)

    print(f"\nParts extracted: {len(parts)}")

    print("\n" + "=" * 70)
    for i, part in enumerate(parts, 1):
        print(f"\nPart {i}: {part.device_tag}")
        print(f"  Designation (description): {part.designation}")
        print(f"  Technical Data: '{part.technical_data}'")
        print(f"  Type Designation (part #): '{part.type_designation}'")

        # Test voltage extraction
        import re
        voltage_patterns = [
            r'(\d+\s*V\s*(?:DC|AC))',
            r'(\d+\s*V)',
            r'(DC\s*\d+\s*V)',
            r'(AC\s*\d+\s*V)',
        ]

        found_voltage = None
        for pattern in voltage_patterns:
            match = re.search(pattern, part.technical_data, re.IGNORECASE)
            if match:
                found_voltage = match.group(1)
                break

        if found_voltage:
            print(f"  Extracted voltage: {found_voltage}")
        else:
            print(f"  Extracted voltage: NONE")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    debug_technical_data()
