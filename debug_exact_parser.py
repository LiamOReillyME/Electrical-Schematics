"""Debug the exact parts parser to see raw extraction."""

from pathlib import Path
from electrical_schematics.pdf.exact_parts_parser import parse_parts_list, find_parts_list_page
import fitz

def debug_parser():
    """Debug exact parser extraction."""
    pdf_path = Path('/home/liam-oreilly/claude.projects/electricalSchematics/AO.pdf')

    print("=" * 70)
    print("DEBUGGING EXACT PARTS PARSER")
    print("=" * 70)

    # Step 1: Find parts list page
    print("\n1. Finding parts list page...")
    page_num = find_parts_list_page(pdf_path)

    if page_num is None:
        print("   ❌ Parts list page NOT found!")
        return
    else:
        print(f"   ✓ Parts list found on page {page_num}")

    # Step 2: Show some raw text from the page
    print("\n2. Extracting raw text from parts list page...")
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    text_dict = page.get_text("dict")

    print(f"   Page dimensions: {page.rect.width} x {page.rect.height}")

    # Collect text items with positions
    text_items = []
    for block in text_dict.get("blocks", []):
        if block.get("type") == 0:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if text:
                        bbox = span.get("bbox", [0, 0, 0, 0])
                        text_items.append({
                            'text': text,
                            'x': bbox[0],
                            'y': bbox[1]
                        })

    print(f"   Total text items found: {len(text_items)}")

    # Show items in data region (Y 55-737)
    data_items = [item for item in text_items if 55 <= item['y'] <= 737]
    print(f"   Items in data region (Y 55-737): {len(data_items)}")

    # Show first 30 items
    print("\n3. First 30 text items in data region:")
    print("   " + "-" * 66)
    for i, item in enumerate(data_items[:30]):
        print(f"   {i+1:2d}. X:{item['x']:6.1f} Y:{item['y']:6.1f} | {item['text'][:40]}")

    doc.close()

    # Step 3: Run parser
    print("\n4. Running parser...")
    parts = parse_parts_list(pdf_path)

    print(f"   Parts extracted: {len(parts)}")

    # Show first 10 parts
    print("\n5. First 10 parsed parts:")
    print("   " + "-" * 66)
    for i, part in enumerate(parts[:10]):
        print(f"\n   Part {i+1}: {part.device_tag}")
        print(f"     Designation:     {part.designation[:50] if part.designation else 'EMPTY'}")
        print(f"     Technical Data:  {part.technical_data[:50] if part.technical_data else 'EMPTY'}")
        print(f"     Type Designation: {part.type_designation[:50] if part.type_designation else 'EMPTY'}")

    # Step 4: Analyze column boundaries
    print("\n6. Checking column boundaries...")
    print("   Column definitions from parser:")
    print("     Device tag:       X 35-110")
    print("     Designation:      X 90-370")
    print("     Technical Data:   X 370-610")
    print("     Type Designation: X 610-835")

    # Count items in each column
    device_col = [item for item in data_items if 35 <= item['x'] < 110]
    desig_col = [item for item in data_items if 90 <= item['x'] < 370]
    tech_col = [item for item in data_items if 370 <= item['x'] < 610]
    type_col = [item for item in data_items if 610 <= item['x'] < 835]

    print(f"\n   Items found in each column:")
    print(f"     Device tag column:       {len(device_col)} items")
    print(f"     Designation column:      {len(desig_col)} items")
    print(f"     Technical Data column:   {len(tech_col)} items")
    print(f"     Type Designation column: {len(type_col)} items")

    # Show sample from each column
    print("\n7. Sample items from each column:")
    print("   Device tag column (X 35-110):")
    for item in device_col[:5]:
        print(f"     X:{item['x']:6.1f} | {item['text']}")

    print("   Designation column (X 90-370):")
    for item in desig_col[:5]:
        print(f"     X:{item['x']:6.1f} | {item['text']}")

    print("   Technical Data column (X 370-610):")
    for item in tech_col[:5]:
        print(f"     X:{item['x']:6.1f} | {item['text']}")

    print("   Type Designation column (X 610-835):")
    for item in type_col[:5]:
        print(f"     X:{item['x']:6.1f} | {item['text']}")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    debug_parser()
