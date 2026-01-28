"""Test component dialog functionality."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from electrical_schematics.gui.main_window import ComponentDialog
from electrical_schematics.database import initialize_database_with_defaults
from electrical_schematics.config import get_settings

def test_component_dialog():
    """Test component dialog features."""
    print("=== TEST 4: Component Dialog ===")

    app = QApplication(sys.argv)

    # Initialize database
    settings = get_settings()
    db_path = settings.get_database_path()
    db_manager = initialize_database_with_defaults(db_path)

    # Create dialog with db_manager and edit mode
    dialog = ComponentDialog(
        parent=None,
        template_data={'part_number': 'test123'},
        db_manager=db_manager,
        is_edit_mode=True
    )

    print("✓ Dialog created with edit mode")

    # Check if part number field exists
    if hasattr(dialog, 'part_number_edit'):
        print("✓ Part number field exists")
    else:
        print("❌ FAIL: Part number field missing")
        return False

    # Check if fetch button exists
    if hasattr(dialog, 'fetch_btn'):
        print("✓ Fetch button exists")
    else:
        print("❌ FAIL: Fetch button missing")
        return False

    # Check if Save to Library method exists
    if hasattr(dialog, '_save_to_library'):
        print("✓ Save to Library method exists")
    else:
        print("❌ FAIL: Save to Library method missing")
        return False

    # Check tabs
    print(f"✓ Dialog has {dialog.tabs.count()} tabs")

    print("\n=== TEST 4: PASSED ===")
    return True

if __name__ == "__main__":
    success = test_component_dialog()
    sys.exit(0 if success else 1)
