"""Test GUI functionality."""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from electrical_schematics.gui.main_window import MainWindow

def test_gui():
    """Test GUI startup and PDF loading."""
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    print("=== TEST 2: GUI Launch ===")
    print("✓ Window created and shown")

    # Test PDF loading
    pdf_path = Path('/home/liam-oreilly/claude.projects/electricalSchematics/AO.pdf')

    def load_pdf():
        try:
            print("\nLoading PDF...")
            window.pdf_viewer.load_pdf(str(pdf_path))

            print("Auto-loading diagram...")
            from electrical_schematics.pdf.auto_loader import DiagramAutoLoader
            window.diagram, format_type = DiagramAutoLoader.load_diagram(pdf_path)

            # Initialize simulators
            from electrical_schematics.simulation import VoltageSimulator
            from electrical_schematics.simulation.interactive_simulator import InteractiveSimulator
            from electrical_schematics.diagnostics import FaultAnalyzer

            window.simulator = VoltageSimulator(window.diagram)
            window.interactive_sim = InteractiveSimulator(window.diagram)
            window.analyzer = FaultAnalyzer(window.diagram)
            window.interactive_panel.set_diagram(window.diagram)

            print(f"✓ PDF loaded: {format_type}")
            print(f"✓ Components: {len(window.diagram.components)}")

            # Check if components appear on PDF
            window.pdf_viewer.set_component_overlays(window.diagram.components, [])

            print("✓ Overlays set")

            # Enable wire drawing mode
            window.wire_drawing_mode = True
            window.pdf_viewer.set_wire_drawing_mode(True)
            print("✓ Wire drawing mode enabled")

            print("\n=== TEST 2: PASSED ===")

            # Exit after 1 second
            QTimer.singleShot(1000, app.quit)

        except Exception as e:
            print(f"\n❌ TEST 2: FAILED - {e}")
            import traceback
            traceback.print_exc()
            app.quit()

    # Load PDF after event loop starts
    QTimer.singleShot(100, load_pdf)

    app.exec()

if __name__ == "__main__":
    test_gui()
