# DigiKey Parts Enrichment - Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### 1. Configure DigiKey API
Create `.env` file in project root:
```bash
DIGIKEY_CLIENT_ID=your_client_id
DIGIKEY_CLIENT_SECRET=your_client_secret
```

### 2. Clean Existing Library
```bash
python cleanup_library.py
# Removes generic templates and E-codes
# Creates backup automatically
```

### 3. Import Parts
```bash
# Import default DRAWER parts
python import_digikey_parts.py

# Or import specific parts
python import_digikey_parts.py --parts "3RT2026-1DB40-1AAO" "6ES7 511-1AK02-0AB0"

# Or from file
echo "3RT2026-1DB40-1AAO" > parts.txt
python import_digikey_parts.py --file parts.txt
```

### 4. Verify
```bash
# Run tests
pytest tests/test_asset_downloader.py -v
pytest tests/test_contact_parser.py -v
pytest tests/test_dynamic_icon_generator.py -v

# Run demo
python examples/test_parts_enrichment.py

# Check assets downloaded
ls electrical_schematics/assets/component_photos/
ls electrical_schematics/assets/datasheets/
```

## 📖 Common Tasks

### Parse Contact Configuration
```python
from electrical_schematics.services.contact_parser import ContactConfigParser

parser = ContactConfigParser()
config = parser.parse_description("Relay DPDT 5A 24VDC", "Relays")

print(f"Type: {config.component_type}")  # relay
print(f"NO: {config.no_contacts}")        # 2
print(f"NC: {config.nc_contacts}")        # 2
```

### Generate Icon
```python
from electrical_schematics.services.dynamic_icon_generator import DynamicIconGenerator

generator = DynamicIconGenerator()
svg = generator.generate_icon(config)

# Save to file
with open("icon.svg", "w") as f:
    f.write(svg)
```

### Download Assets
```python
from electrical_schematics.services.asset_downloader import AssetDownloader

downloader = AssetDownloader()
photo, datasheet = downloader.download_both(
    photo_url="https://example.com/photo.jpg",
    datasheet_url="https://example.com/datasheet.pdf",
    part_number="3RT2026-1DB40-1AAO"
)
```

### Lookup Part in DigiKey
```python
from electrical_schematics.api.digikey_client import DigiKeyClient
from electrical_schematics.config.settings import DigiKeyConfig

client = DigiKeyClient(DigiKeyConfig())

# With retry logic (tries with/without hyphens)
details = client.get_product_details_with_retry("3RT2026-1DB40-1AAO")

# Validate complete data
if client.validate_complete_data(details):
    print("All required fields present")
```

## 🔧 Troubleshooting

### DigiKey API Not Working
```bash
# Check credentials
python -c "from electrical_schematics.config.settings import DigiKeyConfig; c=DigiKeyConfig(); print(f'ID: {c.client_id[:10]}..., Secret: {bool(c.client_secret)}')"

# Test authentication
python -c "from electrical_schematics.api.digikey_client import DigiKeyClient; from electrical_schematics.config.settings import DigiKeyConfig; client=DigiKeyClient(DigiKeyConfig()); client.authenticate(); print('✓ Authenticated')"
```

### Assets Not Downloading
```bash
# Check network
curl -I https://www.digikey.com

# Enable debug logging
python -c "import logging; logging.basicConfig(level=logging.DEBUG); from electrical_schematics.services.asset_downloader import AssetDownloader; d=AssetDownloader(); d.download_photo('https://example.com/test.jpg', 'TEST')"
```

### Icon Not Generating
```python
# Test parser
from electrical_schematics.services.contact_parser import ContactConfigParser
parser = ContactConfigParser()
config = parser.parse_description("Your description", "Category")
print(config.to_dict())

# Test generator
from electrical_schematics.services.dynamic_icon_generator import DynamicIconGenerator
gen = DynamicIconGenerator()
svg = gen.generate_icon(config)
print(f"Generated: {len(svg)} chars")
```

## 📁 File Locations

```
electrical_schematics/
├── assets/
│   ├── component_photos/     ← Photos downloaded here
│   └── datasheets/            ← PDFs downloaded here
├── services/
│   ├── asset_downloader.py   ← Asset management
│   ├── contact_parser.py     ← Contact parsing
│   └── dynamic_icon_generator.py  ← Icon generation
├── api/
│   └── digikey_client.py     ← DigiKey API (enhanced)
└── config/
    └── default_library.json  ← Parts library

tests/
├── test_asset_downloader.py  ← 12 tests
├── test_contact_parser.py    ← 23 tests
└── test_dynamic_icon_generator.py  ← 17 tests

cleanup_library.py            ← Remove templates/E-codes
import_digikey_parts.py       ← Batch import
```

## 📊 What Gets Stored

For each part:
- ✅ Manufacturer part number
- ✅ DigiKey part number
- ✅ Description and category
- ✅ Photo URL and local path
- ✅ Datasheet URL and local path
- ✅ Unit price and stock
- ✅ Technical parameters
- ✅ Contact configuration (parsed)
- ✅ IEC 60617 icon SVG

## 🎯 IEC 60617 Numbering

```
Relay/Contactor:
- Coil: A1, A2
- NO contacts: 13-14, 23-24, 33-34, 43-44
- NC contacts: 11-12, 21-22, 31-32, 41-42
- Power (contactor): 1-2, 3-4, 5-6

Terminal Block:
- Positions: 1, 2, 3, 4, 5, ...
```

## 💡 Tips

1. **Hyphen Retry**: Client automatically retries without hyphens if lookup fails
2. **Complete Data**: Parts without all required fields are skipped
3. **Asset Reuse**: Existing assets aren't re-downloaded (use `force=True` to override)
4. **Error Handling**: Network failures return `None`, don't crash the app
5. **Batch Import**: Use files for large part lists

## 📚 Full Documentation

- **PARTS_ENRICHMENT.md** - Complete system documentation
- **DIGIKEY_ENRICHMENT_SUMMARY.md** - Implementation summary
- **examples/test_parts_enrichment.py** - Working examples

## ⚡ Performance

- Photo download: ~5s each (~500KB)
- Datasheet download: ~10s each (~2MB)
- Icon generation: <10ms
- Contact parsing: <1ms

## ✅ Verification Checklist

- [ ] DigiKey API configured
- [ ] Library cleaned (generics removed)
- [ ] Parts imported successfully
- [ ] Assets downloaded (check directories)
- [ ] All 52 tests passing
- [ ] Demo script runs without errors
- [ ] Icons generated correctly
- [ ] Library JSON updated

---

**Ready to use! All systems operational.**
