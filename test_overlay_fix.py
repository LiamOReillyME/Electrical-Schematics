"""Test overlay fixes."""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from electrical_schematics.gui.main_window import MainWindow

def test_overlay():
    """Test that overlays appear after drag-drop."""
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    pdf_path = Path('/home/liam-oreilly/claude.projects/electricalSchematics/AO.pdf')

    def run_test():
        try:
            print("\n=== TEST: Overlay Fix ===")

            # Load PDF
            print("1. Loading PDF...")
            window.pdf_viewer.load_pdf(str(pdf_path))
            window.pdf_viewer.current_page = 18  # Go to parts list page

            # Auto-load diagram
            print("2. Auto-loading diagram...")
            from electrical_schematics.pdf.auto_loader import DiagramAutoLoader
            window.diagram, format_type = DiagramAutoLoader.load_diagram(pdf_path)

            print(f"   Format: {format_type}")
            print(f"   Components loaded: {len(window.diagram.components)}")

            # Initialize simulator
            from electrical_schematics.simulation import VoltageSimulator
            from electrical_schematics.simulation.interactive_simulator import InteractiveSimulator
            from electrical_schematics.diagnostics import FaultAnalyzer

            window.simulator = VoltageSimulator(window.diagram)
            window.interactive_sim = InteractiveSimulator(window.diagram)
            window.analyzer = FaultAnalyzer(window.diagram)
            window.interactive_panel.set_diagram(window.diagram)

            # Set overlays - this should filter out components with x=0, y=0
            print("\n3. Setting overlays (should filter parts list components)...")
            window.pdf_viewer.set_component_overlays(window.diagram.components, [])

            # Simulate drag-drop: add a component at position (100, 100)
            print("\n4. Simulating drag-drop of component...")
            from electrical_schematics.models import IndustrialComponent, IndustrialComponentType
            import uuid

            test_component = IndustrialComponent(
                id=f"test_{uuid.uuid4().hex[:8]}",
                type=IndustrialComponentType.CONTACTOR,
                designation="K-TEST",
                description="Test component",
                voltage_rating="24VDC",
                x=100.0,
                y=100.0,
                width=40.0,
                height=30.0
            )

            window.diagram.components.append(test_component)
            print(f"   Added component: {test_component.designation} at ({test_component.x}, {test_component.y})")

            # Update overlays
            print("\n5. Updating overlays...")
            window.pdf_viewer.set_component_overlays(window.diagram.components, [])

            print("\n6. Checking overlays...")
            print(f"   Total components in diagram: {len(window.diagram.components)}")
            print(f"   Overlays created: {len(window.pdf_viewer.component_overlays)}")
            print(f"   Current page: {window.pdf_viewer.current_page}")
            print(f"   Show overlays: {window.pdf_viewer.show_overlays}")

            if len(window.pdf_viewer.component_overlays) > 0:
                print("\n✓ SUCCESS: Overlays created!")
                for overlay in window.pdf_viewer.component_overlays:
                    print(f"   - {overlay.component.designation} on page {overlay.page} at ({overlay.rect.x()}, {overlay.rect.y()})")
            else:
                print("\n❌ FAIL: No overlays created")

            # Trigger display update
            window.pdf_viewer._update_display()

            print("\n=== Test Complete ===")
            print("Check terminal output above for DEBUG messages about overlay drawing")

            # Exit after 2 seconds
            QTimer.singleShot(2000, app.quit)

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            app.quit()

    QTimer.singleShot(100, run_test)
    app.exec()

if __name__ == "__main__":
    test_overlay()
