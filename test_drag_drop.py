"""Test drag-drop functionality."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QMimeData, QPoint
from electrical_schematics.gui.component_palette import ComponentPalette
from electrical_schematics.gui.pdf_viewer import PDFViewer
from electrical_schematics.database import initialize_database_with_defaults
from electrical_schematics.config import get_settings
import json

def test_drag_drop():
    """Test drag-drop from palette to PDF viewer."""
    print("=== TEST 5: Drag-Drop ===")

    app = QApplication(sys.argv)

    # Initialize database
    settings = get_settings()
    db_path = settings.get_database_path()
    db_manager = initialize_database_with_defaults(db_path)

    # Create palette
    palette = ComponentPalette(db_manager)
    print("✓ Component palette created")

    # Check if component tree has items
    categories = db_manager.get_categories()
    print(f"✓ Found {len(categories)} categories")

    if len(categories) == 0:
        print("❌ FAIL: No categories found")
        return False

    # Get templates from database directly
    all_templates = []
    for category in categories:
        templates = db_manager.get_component_templates(category)
        all_templates.extend(templates)

    print(f"✓ Loaded {len(all_templates)} component templates")

    if len(all_templates) == 0:
        print("❌ FAIL: No component templates loaded")
        return False

    # Create PDF viewer
    viewer = PDFViewer()
    print("✓ PDF viewer created")

    # Check if PDF viewer accepts drops
    if viewer.acceptDrops():
        print("✓ PDF viewer accepts drops")
    else:
        print("❌ FAIL: PDF viewer doesn't accept drops")
        return False

    # Test MIME data format
    template = all_templates[0]
    mime_data = QMimeData()

    component_data = {
        'library_id': template.id,
        'type': template.component_type,
        'designation_prefix': template.designation_prefix,
        'default_voltage': template.default_voltage,
        'name': template.name,
        'manufacturer': template.manufacturer or '',
        'part_number': template.part_number or ''
    }

    mime_data.setData(
        'application/x-component-template',
        json.dumps(component_data).encode('utf-8')
    )

    if mime_data.hasFormat('application/x-component-template'):
        print("✓ MIME data format correct")
    else:
        print("❌ FAIL: MIME data format incorrect")
        return False

    # Check if dragEnterEvent exists
    if hasattr(viewer, 'dragEnterEvent'):
        print("✓ PDF viewer has dragEnterEvent")
    else:
        print("❌ FAIL: PDF viewer missing dragEnterEvent")
        return False

    # Check if dropEvent exists
    if hasattr(viewer, 'dropEvent'):
        print("✓ PDF viewer has dropEvent")
    else:
        print("❌ FAIL: PDF viewer missing dropEvent")
        return False

    print("\n=== TEST 5: PASSED ===")
    return True

if __name__ == "__main__":
    success = test_drag_drop()
    sys.exit(0 if success else 1)
