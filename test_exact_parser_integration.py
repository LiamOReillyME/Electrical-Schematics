"""Test exact parts parser integration with auto_loader."""

from pathlib import Path
from electrical_schematics.pdf.auto_loader import DiagramAutoLoader

def test_exact_parser():
    """Test that exact parser is integrated and working."""
    pdf_path = Path('/home/liam-oreilly/claude.projects/electricalSchematics/AO.pdf')

    if not pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}")
        return

    print("=" * 70)
    print("TESTING EXACT PARTS PARSER INTEGRATION")
    print("=" * 70)

    print("\n1. Loading diagram with auto_loader...")
    diagram, format_type = DiagramAutoLoader.load_diagram(pdf_path)

    print(f"\n2. Format detected: {format_type}")
    print(f"   Components loaded: {len(diagram.components)}")

    if len(diagram.components) == 0:
        print("\n❌ FAIL: No components loaded!")
        return

    print("\n3. Checking component data quality...")
    print("-" * 70)

    # Sample first 10 components
    for i, comp in enumerate(diagram.components[:10]):
        print(f"\nComponent {i+1}:")
        print(f"  Designation:     {comp.designation}")
        print(f"  Description:     {comp.description[:60] if comp.description else 'N/A'}")
        print(f"  Voltage Rating:  {comp.voltage_rating if comp.voltage_rating else 'N/A'}")
        print(f"  Type:            {comp.type.value}")

        # Check for metadata (technical_data, part_number)
        if hasattr(comp, 'metadata') and comp.metadata:
            tech_data = comp.metadata.get('technical_data', '')
            part_num = comp.metadata.get('part_number', '')
            if tech_data:
                print(f"  Technical Data:  {tech_data[:60]}")
            if part_num:
                print(f"  Part Number:     {part_num}")

    print("\n" + "-" * 70)
    print(f"\n4. Summary Statistics:")

    # Count components with complete data
    with_description = sum(1 for c in diagram.components if c.description)
    with_voltage = sum(1 for c in diagram.components if c.voltage_rating)
    with_metadata = sum(1 for c in diagram.components if hasattr(c, 'metadata') and c.metadata)

    print(f"   Total components:          {len(diagram.components)}")
    print(f"   With description:          {with_description} ({100*with_description/len(diagram.components):.1f}%)")
    print(f"   With voltage rating:       {with_voltage} ({100*with_voltage/len(diagram.components):.1f}%)")
    print(f"   With metadata:             {with_metadata} ({100*with_metadata/len(diagram.components):.1f}%)")

    print("\n5. Verification:")
    if with_description > len(diagram.components) * 0.5:
        print("   ✓ Descriptions extracted successfully")
    else:
        print("   ❌ Most components missing descriptions")

    if with_voltage > len(diagram.components) * 0.3:
        print("   ✓ Voltage ratings extracted")
    else:
        print("   ⚠ Many components missing voltage ratings")

    if with_metadata > len(diagram.components) * 0.5:
        print("   ✓ Technical data and part numbers stored")
    else:
        print("   ⚠ Metadata not being stored")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    test_exact_parser()
