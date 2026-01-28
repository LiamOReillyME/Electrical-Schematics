#!/usr/bin/env python3
"""Debug script to investigate parts with empty designations."""

import fitz
from pathlib import Path

pdf_path = Path("/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf")
pdf = fitz.open(pdf_path)

# Column boundaries
COL_DEVICE_TAG = (35, 190)
COL_DESIGNATION = (190, 375)
COL_TECH_DATA = (375, 615)
COL_TYPE_DESIGNATION = (615, 840)

# Parts with empty designations from test output
empty_parts = ['-A1', '-F5', '-K1', '-K1.3', '-K2', '-K3', '-U1']

print("=" * 80)
print("INVESTIGATING PARTS WITH EMPTY DESIGNATIONS")
print("=" * 80)

for page_idx in [25, 26]:  # Pages 26-27
    page = pdf[page_idx]
    text_dict = page.get_text('dict')

    # Collect all text with positions
    all_text = []
    for block in text_dict.get('blocks', []):
        if block.get('type') == 0:
            for line in block.get('lines', []):
                for span in line.get('spans', []):
                    text = span.get('text', '').strip()
                    if not text:
                        continue
                    bbox = span.get('bbox', [0, 0, 0, 0])
                    x, y = bbox[0], bbox[1]
                    all_text.append({'text': text, 'x': x, 'y': y})

    # Find rows with target device tags
    for target_tag in empty_parts:
        matching_rows = []
        for item in all_text:
            if item['text'] == target_tag and COL_DEVICE_TAG[0] <= item['x'] < COL_DEVICE_TAG[1]:
                matching_rows.append(item['y'])

        for y_pos in matching_rows:
            print(f"\n{target_tag} at y={y_pos:.1f} (Page {page_idx+1}):")
            print("-" * 80)

            # Show all text near this y-position (within ±20)
            nearby_text = [t for t in all_text if abs(t['y'] - y_pos) < 20]
            nearby_text.sort(key=lambda t: (t['y'], t['x']))

            for item in nearby_text:
                col = 'OTHER'
                if COL_DEVICE_TAG[0] <= item['x'] < COL_DEVICE_TAG[1]:
                    col = 'DEV_TAG'
                elif COL_DESIGNATION[0] <= item['x'] < COL_DESIGNATION[1]:
                    col = 'DESIGNAT'
                elif COL_TECH_DATA[0] <= item['x'] < COL_TECH_DATA[1]:
                    col = 'TECH'
                elif COL_TYPE_DESIGNATION[0] <= item['x'] < COL_TYPE_DESIGNATION[1]:
                    col = 'TYPE'

                print(f"  [{col:8s}] x={item['x']:6.1f} y={item['y']:6.1f} | {item['text']}")

pdf.close()
