#!/usr/bin/env python3
"""Debug script to examine PDF structure and identify language patterns."""

import fitz
from pathlib import Path
from collections import defaultdict

pdf_path = Path("/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf")
pdf = fitz.open(pdf_path)
page = pdf[25]  # Page 26 (0-indexed: 25)

# Column boundaries (from OCR extractor)
COL_DEVICE_TAG = (35, 190)
COL_DESIGNATION = (190, 375)
COL_TECH_DATA = (375, 615)
COL_TYPE_DESIGNATION = (615, 840)

print("=" * 80)
print("PDF TEXT STRUCTURE ANALYSIS - Page 26")
print("=" * 80)

text_dict = page.get_text('dict')

# Collect all text spans with positions
all_spans = []
for block in text_dict.get('blocks', []):
    if block.get('type') == 0:  # Text block
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                text = span.get('text', '').strip()
                if not text:
                    continue
                bbox = span.get('bbox', [0, 0, 0, 0])
                x, y = bbox[0], bbox[1]

                # Determine column
                column = 'OTHER'
                if COL_DEVICE_TAG[0] <= x < COL_DEVICE_TAG[1]:
                    column = 'DEVICE_TAG'
                elif COL_DESIGNATION[0] <= x < COL_DESIGNATION[1]:
                    column = 'DESIGNATION'
                elif COL_TECH_DATA[0] <= x < COL_TECH_DATA[1]:
                    column = 'TECH_DATA'
                elif COL_TYPE_DESIGNATION[0] <= x < COL_TYPE_DESIGNATION[1]:
                    column = 'TYPE_DESIG'

                all_spans.append({
                    'text': text,
                    'x': x,
                    'y': y,
                    'column': column,
                    'bbox': bbox
                })

# Group by row (y-coordinate)
rows = defaultdict(list)
for span in all_spans:
    if span['column'] in ['DEVICE_TAG', 'DESIGNATION', 'TECH_DATA', 'TYPE_DESIG']:
        y_key = round(span['y'] / 10) * 10
        rows[y_key].append(span)

# Show first 10 rows in designation column
print("\nFirst 10 rows in DESIGNATION column:")
print("-" * 80)

designation_rows = {}
for y_key in sorted(rows.keys()):
    row_spans = rows[y_key]
    designation_texts = [s['text'] for s in row_spans if s['column'] == 'DESIGNATION']
    if designation_texts:
        designation_rows[y_key] = designation_texts

count = 0
for y_key in sorted(designation_rows.keys()):
    texts = designation_rows[y_key]
    print(f"y={y_key:5.0f}: {' '.join(texts)}")
    count += 1
    if count >= 10:
        break

# Look for patterns - are German and English in separate spans?
print("\n" + "=" * 80)
print("LANGUAGE PATTERN ANALYSIS")
print("=" * 80)

german_words = ['Steuerung', 'Sicherungsautomat', 'Schütz', 'Hilfsblock',
                'Lüfter', 'Stromversorgung', 'Kontakterweiterung', 'EMV-Filter',
                'Frequenzumrichter']

english_words = ['Controller', 'Circuit breaker', 'Contactor', 'Auxiliary block',
                 'Fan', 'Power supply', 'Contact expansion', 'EMI-Filter',
                 'Frequency converter']

# Check first few rows for language separation
print("\nChecking if German and English are in separate spans...")
for y_key in sorted(list(designation_rows.keys())[:5]):
    row_data = rows[y_key]
    designation_spans = [s for s in row_data if s['column'] == 'DESIGNATION']

    if designation_spans:
        print(f"\ny={y_key}:")
        for span in designation_spans:
            has_german = any(gw in span['text'] for gw in german_words)
            has_english = any(ew in span['text'] for ew in english_words)
            lang = 'GERMAN' if has_german else ('ENGLISH' if has_english else 'UNKNOWN')
            print(f"  [{lang:8s}] x={span['x']:6.1f} | {span['text']}")

pdf.close()
