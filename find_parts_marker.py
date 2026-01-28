"""Find where 'Parts list' marker actually appears in the PDF."""

from pathlib import Path
import fitz

def find_marker():
    """Search for parts list marker in all pages."""
    pdf_path = Path('/home/liam-oreilly/claude.projects/electricalSchematics/AO.pdf')

    print("=" * 70)
    print("SEARCHING FOR PARTS LIST MARKER")
    print("=" * 70)

    doc = fitz.open(pdf_path)
    print(f"\nTotal pages: {len(doc)}")

    markers = [
        "Parts list",
        "parts list",
        "PARTS LIST",
        "Artikelstückliste",
        "Artikelstuckliste",
        "parts",
        "list",
        "Parts",
        "List"
    ]

    print(f"\nSearching for markers: {markers[:5]}...")

    for page_num in range(len(doc)):
        page = doc[page_num]
        text_dict = page.get_text("dict")

        # Track if we found anything on this page
        page_matches = []

        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "")
                        bbox = span.get("bbox", [0, 0, 0, 0])

                        # Check for any marker
                        for marker in markers:
                            if marker.lower() in text.lower():
                                page_matches.append({
                                    'text': text,
                                    'marker': marker,
                                    'bbox': bbox,
                                    'x': bbox[0],
                                    'y': bbox[1]
                                })

        if page_matches:
            print(f"\n{'='*70}")
            print(f"PAGE {page_num}:")
            print(f"{'='*70}")
            for match in page_matches:
                print(f"  Text: '{match['text']}'")
                print(f"  Marker: '{match['marker']}'")
                print(f"  Position: X={match['x']:.1f}, Y={match['y']:.1f}")
                print(f"  BBox: {[round(c, 1) for c in match['bbox']]}")
                print()

                # Check if in expected region (X40-90, Y23-35)
                if 40 <= match['x'] <= 90 and 23 <= match['y'] <= 35:
                    print("  ✓ IN EXPECTED REGION (X40-90, Y23-35)")
                else:
                    print(f"  ✗ NOT in expected region")
                    if match['x'] < 40 or match['x'] > 90:
                        print(f"    X is {match['x']:.1f} (expected 40-90)")
                    if match['y'] < 23 or match['y'] > 35:
                        print(f"    Y is {match['y']:.1f} (expected 23-35)")

                print()

    doc.close()

    print("=" * 70)
    print("SEARCH COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    find_marker()
