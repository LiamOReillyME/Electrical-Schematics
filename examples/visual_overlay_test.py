"""Test visual overlay functionality on PDF."""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from electrical_schematics.gui.main_window import MainWindow


def main():
    """Test visual overlay on PDF diagram."""
    print("=" * 80)
    print("VISUAL OVERLAY TEST")
    print("=" * 80)
    print()
    print("This test demonstrates the visual overlay system that highlights")
    print("energized components directly on the PDF diagram.")
    print()
    print("Instructions:")
    print("1. Click 'Open PDF' and select DRAWER.pdf")
    print("2. Wait for automatic analysis to complete")
    print("3. Navigate to pages with circuit diagrams (not just tables)")
    print("4. Observe color-coded overlays:")
    print("   - GREEN = Energized components (has voltage)")
    print("   - RED = De-energized components (no voltage)")
    print()
    print("5. In the Interactive Panel (middle):")
    print("   - Double-click components to toggle their state")
    print("   - Watch PDF overlays update in real-time")
    print("   - See voltage flow change dynamically")
    print()
    print("6. Use 'Show Overlays' button to toggle overlay visibility")
    print("7. Use zoom controls to see details")
    print()
    print("=" * 80)
    print()

    # Create Qt application
    app = QApplication(sys.argv)

    # Create and show main window
    window = MainWindow()
    window.show()

    # Auto-load DRAWER.pdf if it exists
    drawer_path = Path("DRAWER.pdf")
    if drawer_path.exists():
        print(f"Auto-loading {drawer_path}...")
        window.pdf_viewer.load_pdf(str(drawer_path))

        # Trigger automatic analysis
        try:
            from electrical_schematics.pdf.auto_loader import DiagramAutoLoader
            diagram, format_type = DiagramAutoLoader.load_diagram(drawer_path)

            if format_type == "drawer":
                window.diagram = diagram
                window.interactive_sim = None
                from electrical_schematics.simulation.interactive_simulator import InteractiveSimulator
                window.interactive_sim = InteractiveSimulator(diagram)
                window.interactive_panel.set_diagram(diagram)

                print(f"✓ Loaded {len(diagram.components)} components")
                print("✓ Interactive simulation ready")
                print("✓ Visual overlays enabled")
                print()
                print("Navigate to circuit diagram pages to see overlays!")
        except Exception as e:
            print(f"Error during auto-load: {e}")
            print("You can still manually open the PDF using the toolbar.")
    else:
        print("DRAWER.pdf not found in current directory.")
        print("Use the 'Open PDF' button to load a wiring diagram.")

    print()
    print("Close the window to exit.")

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
