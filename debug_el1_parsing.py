#!/usr/bin/env python3
"""Debug -EL1 part number extraction."""

import fitz
from pathlib import Path

pdf_path = Path("DRAWER.pdf")
pdf = fitz.open(pdf_path)
page = pdf[25]  # Page 26

text_dict = page.get_text('dict')

# Column boundaries
COL_DEVICE_TAG = (35, 190)
COL_DESIGNATION = (190, 375)
COL_TECH_DATA = (375, 615)
COL_TYPE_DESIGNATION = (615, 840)

# Collect all text items
all_items = []
for block in text_dict.get('blocks', []):
    if block.get('type') == 0:
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                text = span.get('text', '').strip()
                if not text:
                    continue
                bbox = span.get('bbox', [0, 0, 0, 0])
                x, y = bbox[0], bbox[1]
                all_items.append({'text': text, 'x': x, 'y': y})

# Group by row
rows = {}
for item in all_items:
    y_key = round(item['y'] / 10) * 10
    if y_key not in rows:
        rows[y_key] = []
    rows[y_key].append(item)

# Find -EL1
print("=" * 80)
print("TRACING -EL1 EXTRACTION")
print("=" * 80)

sorted_y = sorted(rows.keys())
for i, y in enumerate(sorted_y):
    row_items = rows[y]

    # Check if this row has -EL1
    device_tags = [item for item in row_items
                   if COL_DEVICE_TAG[0] <= item['x'] < COL_DEVICE_TAG[1]
                   and (item['text'].startswith('-') or item['text'].startswith('+'))]

    if not any(tag['text'] == '-EL1' for tag in device_tags):
        continue

    print(f"\nFound -EL1 at y={y}")
    print("-" * 80)

    # Show current row
    print("Current row:")
    for item in row_items:
        col = 'OTHER'
        if COL_DEVICE_TAG[0] <= item['x'] < COL_DEVICE_TAG[1]:
            col = 'DEV_TAG'
        elif COL_DESIGNATION[0] <= item['x'] < COL_DESIGNATION[1]:
            col = 'DESIGNAT'
        elif COL_TECH_DATA[0] <= item['x'] < COL_TECH_DATA[1]:
            col = 'TECH'
        elif COL_TYPE_DESIGNATION[0] <= item['x'] < COL_TYPE_DESIGNATION[1]:
            col = 'TYPE'

        print(f"  [{col:8s}] x={item['x']:6.1f} | {item['text']}")

    # Show previous row
    if i > 0:
        prev_y = sorted_y[i - 1]
        prev_items = rows[prev_y]
        print(f"\nPrevious row (y={prev_y}):")
        for item in prev_items:
            col = 'OTHER'
            if COL_DEVICE_TAG[0] <= item['x'] < COL_DEVICE_TAG[1]:
                col = 'DEV_TAG'
            elif COL_DESIGNATION[0] <= item['x'] < COL_DESIGNATION[1]:
                col = 'DESIGNAT'
            elif COL_TECH_DATA[0] <= item['x'] < COL_TECH_DATA[1]:
                col = 'TECH'
            elif COL_TYPE_DESIGNATION[0] <= item['x'] < COL_TYPE_DESIGNATION[1]:
                col = 'TYPE'

            print(f"  [{col:8s}] x={item['x']:6.1f} | {item['text']}")

    # Show next row
    if i + 1 < len(sorted_y):
        next_y = sorted_y[i + 1]
        next_items = rows[next_y]
        print(f"\nNext row (y={next_y}):")
        for item in next_items:
            col = 'OTHER'
            if COL_DEVICE_TAG[0] <= item['x'] < COL_DEVICE_TAG[1]:
                col = 'DEV_TAG'
            elif COL_DESIGNATION[0] <= item['x'] < COL_DESIGNATION[1]:
                col = 'DESIGNAT'
            elif COL_TECH_DATA[0] <= item['x'] < COL_TECH_DATA[1]:
                col = 'TECH'
            elif COL_TYPE_DESIGNATION[0] <= item['x'] < COL_TYPE_DESIGNATION[1]:
                col = 'TYPE'

            print(f"  [{col:8s}] x={item['x']:6.1f} | {item['text']}")

pdf.close()
