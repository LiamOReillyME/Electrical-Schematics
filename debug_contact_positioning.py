"""Debug script to diagnose contact positioning issues.

This script analyzes how contacts are detected and positioned on PDF schematics.
"""

from pathlib import Path
from electrical_schematics.pdf.auto_loader import DiagramAutoLoader
from electrical_schematics.pdf.component_position_finder import ComponentPositionFinder

def debug_contact_positions():
    """Investigate contact positioning for relay/contactor components."""
    
    pdf_path = Path("DRAWER.pdf")
    if not pdf_path.exists():
        print(f"ERROR: {pdf_path} not found")
        return
    
    print("=" * 80)
    print("CONTACT POSITIONING DIAGNOSTIC")
    print("=" * 80)
    
    # Load diagram
    print("\n1. Loading diagram with auto-loader...")
    diagram, _ = DiagramAutoLoader.load_diagram(pdf_path)
    
    print(f"   Found {len(diagram.components)} components")
    
    # Find relays and contactors
    relays_contactors = [c for c in diagram.components 
                        if c.designation.startswith('-K')]
    
    print(f"   Found {len(relays_contactors)} relays/contactors (tags starting with -K)")
    
    # Analyze each relay/contactor
    print("\n2. Analyzing relay/contactor components:")
    print("-" * 80)
    
    for component in relays_contactors[:5]:  # First 5 for brevity
        print(f"\nComponent: {component.designation}")
        print(f"  Type: {component.type.value}")
        print(f"  Primary page: {component.page + 1}")
        print(f"  Primary position: ({component.x:.1f}, {component.y:.1f})")
        print(f"  Size: {component.width:.1f} x {component.height:.1f}")
        
        # Check multi-page positions
        if component.page_positions:
            print(f"  Multi-page positions: {len(component.page_positions)}")
            for page, pos in sorted(component.page_positions.items()):
                print(f"    Page {page + 1}: ({pos.x:.1f}, {pos.y:.1f}) "
                      f"size={pos.width:.1f}x{pos.height:.1f} "
                      f"confidence={pos.confidence:.2f}")
        else:
            print(f"  Multi-page positions: NONE")
        
        # Check contact blocks
        if component.contact_blocks:
            print(f"  Contact blocks: {len(component.contact_blocks)}")
            for cb in component.contact_blocks:
                print(f"    {cb.terminal_from}-{cb.terminal_to} "
                      f"({cb.contact_type.value}) "
                      f"closed={cb.is_closed}")
        else:
            print(f"  Contact blocks: NONE")
        
        # Check legacy contacts list
        if component.contacts:
            print(f"  Legacy contacts: {component.contacts}")
    
    # Search for contact references in PDF
    print("\n3. Searching PDF for contact terminal references:")
    print("-" * 80)
    
    with ComponentPositionFinder(pdf_path) as finder:
        # Look for K1 contact references
        sample_tag = "-K1"
        
        print(f"\nSearching for references to {sample_tag}...")
        
        # Find all device tags
        all_tags = finder.find_all_device_tags(page_range=(0, 25))
        
        # Filter for K1 related references
        k1_refs = [tag for tag in all_tags 
                  if sample_tag in tag.device_tag]
        
        print(f"Found {len(k1_refs)} references containing '{sample_tag}':")
        
        for ref in k1_refs:
            print(f"  {ref.device_tag:20s} "
                  f"Page {ref.page + 1:2d} "
                  f"({ref.x:6.1f}, {ref.y:6.1f}) "
                  f"conf={ref.confidence:.2f} "
                  f"type={ref.match_type}")
    
    print("\n4. Checking for terminal reference pattern:")
    print("-" * 80)
    
    # Check if contacts are stored as separate components or references
    contact_refs = [c for c in diagram.components 
                   if ':' in c.designation]
    
    print(f"Found {len(contact_refs)} components with ':' in designation")
    if contact_refs:
        for ref in contact_refs[:10]:
            print(f"  {ref.designation:20s} "
                  f"Page {ref.page + 1} "
                  f"({ref.x:.1f}, {ref.y:.1f})")
    
    print("\n5. ANALYSIS:")
    print("-" * 80)
    
    # Determine the issue
    if not relays_contactors:
        print("❌ No relays/contactors found in diagram")
    else:
        print(f"✓ Found {len(relays_contactors)} relay/contactor components")
    
    multi_page_count = sum(1 for c in relays_contactors 
                          if c.page_positions)
    
    if multi_page_count == 0:
        print("❌ No multi-page positions tracked for relays/contactors")
        print("   Contacts on different pages won't be positioned correctly")
    else:
        print(f"✓ {multi_page_count} relays have multi-page position data")
    
    contact_block_count = sum(len(c.contact_blocks) for c in relays_contactors)
    
    if contact_block_count == 0:
        print("⚠ No contact blocks defined")
        print("   Contacts may need to be generated from description or parsed data")
    else:
        print(f"✓ Found {contact_block_count} contact blocks across all relays")
    
    # Check if contacts are rendered
    print("\n6. EXPECTED BEHAVIOR:")
    print("-" * 80)
    print("For proper contact positioning:")
    print("  1. Each relay/contactor should have contact_blocks defined")
    print("  2. Contact references (e.g., K1:13-14) should be in page_positions")
    print("  3. OR contacts should be separate components with ':' in designation")
    print("  4. pdf_viewer.py should render contacts at their page_positions")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    debug_contact_positions()
