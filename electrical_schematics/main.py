"""Main entry point for the Electrical Schematics application."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from electrical_schematics.gui.main_window import MainWindow
from electrical_schematics.gui.styles import apply_theme


def main() -> int:
    """Launch the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Industrial Wiring Diagram Analyzer")
    app.setOrganizationName("ElectricalSchematics")

    # Set default font
    font = QFont("Segoe UI", 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    # Apply modern theme
    apply_theme(app)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
