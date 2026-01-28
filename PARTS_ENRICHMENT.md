# Parts Enrichment System

Comprehensive DigiKey integration with dynamic icon generation and asset management.

## Overview

The parts enrichment system provides:

1. **DigiKey Integration** - Automatic part lookup with retry logic
2. **Data Validation** - Ensures all required fields are present
3. **Asset Management** - Downloads and stores photos and datasheets locally
4. **Contact Parsing** - Extracts contact configuration from descriptions
5. **Dynamic Icons** - Generates IEC 60617 compliant schematic symbols
6. **Library Integration** - Seamless integration with component library

## Architecture

### Services

#### AssetDownloader
Downloads and manages component photos and datasheets from DigiKey.

```python
from electrical_schematics.services.asset_downloader import AssetDownloader

downloader = AssetDownloader()

# Download both photo and datasheet
photo_path, datasheet_path = downloader.download_both(
    photo_url="https://example.com/photo.jpg",
    datasheet_url="https://example.com/datasheet.pdf",
    part_number="3RT2026-1DB40-1AAO"
)

# Check if assets exist locally
photo = downloader.get_photo_path("3RT2026-1DB40-1AAO")
datasheet = downloader.get_datasheet_path("3RT2026-1DB40-1AAO")
```

**Features:**
- Automatic filename sanitization
- Skip existing files (force=True to override)
- Validates file integrity
- Supports cleanup of orphaned assets

**Assets Directory:**
```
electrical_schematics/assets/
├── component_photos/
│   ├── 3RT2026-1DB40-1AAO.jpg
│   └── 6ES7_511-1AK02-0AB0.jpg
└── datasheets/
    ├── 3RT2026-1DB40-1AAO.pdf
    └── 6ES7_511-1AK02-0AB0.pdf
```

#### ContactConfigParser
Parses component descriptions to extract contact configuration.

```python
from electrical_schematics.services.contact_parser import ContactConfigParser

parser = ContactConfigParser()

config = parser.parse_description(
    "Contactor AC-3 11KW/400V 3-phase with 1 NO auxiliary",
    category="Contactors"
)

print(f"Type: {config.component_type}")  # "contactor"
print(f"Power contacts: {config.power_contacts}")  # 3
print(f"NO auxiliary: {config.no_contacts}")  # 1
print(f"Three-phase: {config.three_phase}")  # True
```

**Supported Patterns:**
- NO/NC contacts: "2 NO", "1 NC", "2 NO and 1 NC"
- Pole configurations: "SPDT", "DPDT", "3PDT", "4PDT"
- Terminal positions: "10 position", "12-way"
- Three-phase indicators: "3-phase", "400V", "480V"

**Component Types:**
- `relay` - Control relays with auxiliary contacts
- `contactor` - Power contactors with main and auxiliary contacts
- `terminal_block` - Terminal blocks with numbered positions
- `switch` - Switches and selectors
- `circuit_breaker` - Circuit breakers
- `motor` - Motor starters
- `unknown` - Unrecognized types

#### DynamicIconGenerator
Generates IEC 60617 compliant SVG schematic symbols.

```python
from electrical_schematics.services.dynamic_icon_generator import DynamicIconGenerator

generator = DynamicIconGenerator()

# Generate icon from contact configuration
svg = generator.generate_icon(contact_config)

# Save to file
Path("icon.svg").write_text(svg)
```

**IEC 60617 Numbering:**
- NO contacts: 13-14, 23-24, 33-34, 43-44, ...
- NC contacts: 11-12, 21-22, 31-32, 41-42, ...
- Coil terminals: A1, A2
- Power contacts: 1-2, 3-4, 5-6 (for contactors)

**Icon Types:**
- Relay: Coil + auxiliary contacts
- Contactor: Coil + power contacts + auxiliary contacts
- Terminal block: Numbered terminal positions
- Switch: Contact arrangement
- Circuit breaker: Breaker symbol with poles

### Enhanced DigiKey Client

The DigiKey client now includes:

#### Retry Logic
Automatically retries failed lookups without hyphens:

```python
from electrical_schematics.api.digikey_client import DigiKeyClient
from electrical_schematics.config.settings import DigiKeyConfig

client = DigiKeyClient(DigiKeyConfig())

# Tries "3RT2026-1DB40-1AAO" first
# If fails, retries "3RT20261DB401AAO" (no hyphens)
details = client.get_product_details_with_retry("3RT2026-1DB40-1AAO")
```

#### Data Validation
Validates that all required fields are present:

```python
# Check if response is complete
is_complete = client.validate_complete_data(details)

# Required fields:
# - Manufacturer part number
# - DigiKey part number
# - Description
# - Category
# - Photo URL
# - Datasheet URL
# - Unit price (from pricing array)
```

### Enhanced LibraryPart Model

The `LibraryPart` model now includes:

```python
from electrical_schematics.models.library_part import LibraryPart

part = LibraryPart(
    manufacturer_part_number="3RT2026-1DB40-1AAO",
    manufacturer="Siemens",
    description="Contactor AC-3 11KW/400V",
    category="Contactors",

    # DigiKey data
    digikey_part_number="1234-ND",
    image_url="https://...",
    datasheet_url="https://...",
    unit_price=45.50,

    # Local assets
    photo_path="/path/to/photo.jpg",
    datasheet_path="/path/to/datasheet.pdf",

    # Contact configuration
    contact_config={
        "component_type": "contactor",
        "power_contacts": 3,
        "no_contacts": 1,
        ...
    },

    # Dynamic icon
    icon_svg="<svg>...</svg>"
)

# Check completeness
if part.has_complete_digikey_data():
    print("All required DigiKey data present")

if part.has_local_assets():
    print("Assets downloaded locally")
```

## Usage

### 1. Cleanup Existing Library

Remove generic templates and E-codes:

```bash
python cleanup_library.py
```

This will:
- Remove all "generic template" components
- Remove all E-code components (part numbers starting with 'E')
- Create backup at `default_library.json.backup`
- Preserve real DigiKey parts with complete data

### 2. Import Parts from DigiKey

Import individual parts:

```bash
python import_digikey_parts.py --parts "3RT2026-1DB40-1AAO" "6ES7 511-1AK02-0AB0"
```

Import from file:

```bash
# Create parts.txt with one part number per line
echo "3RT2026-1DB40-1AAO" > parts.txt
echo "6ES7 511-1AK02-0AB0" >> parts.txt

python import_digikey_parts.py --file parts.txt
```

Import default DRAWER parts:

```bash
python import_digikey_parts.py
```

### 3. Test Enrichment System

Run test script to verify functionality:

```bash
python examples/test_parts_enrichment.py
```

This will:
- Test contact configuration parser
- Test icon generator
- Test complete workflow
- Generate sample icons for all component types

## Workflow

The complete enrichment workflow for each part:

1. **DigiKey Lookup**
   - Try original part number
   - If fails, retry without hyphens
   - Parse response into `DigiKeyProductDetails`

2. **Data Validation**
   - Verify all required fields present
   - Check pricing data available
   - Skip incomplete parts

3. **Asset Download**
   - Download photo from `primary_photo` URL
   - Download datasheet from `primary_datasheet` URL
   - Save with sanitized filenames
   - Store local paths

4. **Contact Parsing**
   - Extract contact configuration from description
   - Classify component type
   - Parse NO/NC counts, poles, positions

5. **Icon Generation**
   - Generate IEC 60617 compliant SVG
   - Include correct contact numbering
   - Size based on contact configuration

6. **Library Integration**
   - Create `LibraryPart` with all data
   - Add to component library
   - Save to `default_library.json`

## Data Requirements

For a part to be added to the library, it MUST have:

### From DigiKey API
- Manufacturer part number
- DigiKey part number
- Description
- Category
- Photo URL
- Datasheet URL
- Unit price (from pricing array)

### Generated Locally
- Photo downloaded to `assets/component_photos/`
- Datasheet downloaded to `assets/datasheets/`
- Contact configuration parsed from description
- Dynamic icon SVG generated

## File Structure

```
electrical_schematics/
├── api/
│   └── digikey_client.py         # Enhanced with retry and validation
├── models/
│   └── library_part.py           # Enhanced with new fields
├── services/
│   ├── asset_downloader.py       # NEW - Asset management
│   ├── contact_parser.py         # NEW - Contact configuration parsing
│   └── dynamic_icon_generator.py # NEW - IEC 60617 icon generation
├── assets/
│   ├── component_photos/         # NEW - Downloaded photos
│   └── datasheets/              # NEW - Downloaded datasheets
└── config/
    └── default_library.json      # Enhanced with new fields

tests/
├── test_asset_downloader.py      # NEW
├── test_contact_parser.py        # NEW
└── test_dynamic_icon_generator.py # NEW

examples/
└── test_parts_enrichment.py      # NEW - Workflow demonstration

scripts/
├── cleanup_library.py            # NEW - Library cleanup
└── import_digikey_parts.py       # NEW - Batch import
```

## Testing

Run all tests:

```bash
pytest tests/test_asset_downloader.py -v
pytest tests/test_contact_parser.py -v
pytest tests/test_dynamic_icon_generator.py -v
```

Run workflow test:

```bash
python examples/test_parts_enrichment.py
```

## Integration with GUI

The enriched data can be used in the GUI:

```python
from electrical_schematics.services.component_library import ComponentLibrary

library = ComponentLibrary()
library.load()

# Get part
part = library.get_part("3RT2026-1DB40-1AAO")

# Display photo in component dialog
if part.photo_path:
    pixmap = QPixmap(part.photo_path)
    photo_label.setPixmap(pixmap)

# Open datasheet on double-click
if part.datasheet_path:
    QDesktopServices.openUrl(QUrl.fromLocalFile(part.datasheet_path))

# Show dynamic icon in palette
if part.icon_svg:
    svg_renderer = QSvgRenderer(QByteArray(part.icon_svg.encode()))
    pixmap = QPixmap(60, 60)
    painter = QPainter(pixmap)
    svg_renderer.render(painter)
    painter.end()
```

## Contact Configuration Examples

### Relay DPDT
```
Description: "Relay DPDT 5A 24VDC"
Config:
  component_type: relay
  poles: 2
  no_contacts: 2
  nc_contacts: 2

Icon: Coil (A1-A2) + 4 contacts (13-14, 23-24, 11-12, 21-22)
```

### Contactor 3-Phase
```
Description: "Contactor AC-3 11KW/400V 3-phase with 1 NO auxiliary"
Config:
  component_type: contactor
  three_phase: True
  power_contacts: 3
  no_contacts: 1

Icon: Coil (A1-A2) + Power (1-2, 3-4, 5-6) + Auxiliary (13-14)
```

### Terminal Block
```
Description: "Terminal Block 10 position screw"
Config:
  component_type: terminal_block
  positions: 10

Icon: 10 numbered terminals (1-10)
```

## Troubleshooting

### DigiKey API Issues

```python
# Test authentication
from electrical_schematics.config.settings import DigiKeyConfig
config = DigiKeyConfig()
print(f"Client ID: {config.client_id}")
print(f"Has secret: {bool(config.client_secret)}")
```

### Asset Download Failures

Check network connectivity and URL validity:

```python
from electrical_schematics.services.asset_downloader import AssetDownloader
downloader = AssetDownloader()

# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Try download
photo_path = downloader.download_photo(url, part_number)
```

### Icon Generation Issues

Verify contact configuration parsing:

```python
from electrical_schematics.services.contact_parser import ContactConfigParser
parser = ContactConfigParser()

config = parser.parse_description("Your description here", "Category")
print(config.to_dict())
```

## Future Enhancements

Potential improvements:
- Wire path highlighting from contact configuration
- Animation of contact operation
- Multi-language description parsing
- OCR for PDF schematics
- Integration with other parts databases (Mouser, Farnell)
- 3D model support
- Parametric icon generation
- Custom symbol libraries

## References

- **IEC 60617**: Graphical symbols for diagrams
- **DigiKey API**: https://developer.digikey.com/
- **SVG Specification**: https://www.w3.org/TR/SVG/

## License

Same as parent project.
