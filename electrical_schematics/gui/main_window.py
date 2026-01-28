"""Main application window."""

from pathlib import Path
from typing import Optional
import uuid
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QSplitter, QTextEdit,
    QComboBox, QLineEdit, QFormLayout, QGroupBox, QDoubleSpinBox,
    QDialog, QDialogButtonBox, QMessageBox, QInputDialog, QListWidget,
    QTabWidget, QTableWidget, QTableWidgetItem, QCheckBox, QSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from electrical_schematics.models import WiringDiagram, IndustrialComponent, IndustrialComponentType, SensorState, Wire
from electrical_schematics.simulation import VoltageSimulator
from electrical_schematics.simulation.interactive_simulator import InteractiveSimulator
from electrical_schematics.diagnostics import FaultAnalyzer, FaultCondition
from electrical_schematics.gui.pdf_viewer import PDFViewer
from electrical_schematics.gui.interactive_panel import InteractivePanel
from electrical_schematics.gui.component_palette import ComponentPalette
from electrical_schematics.gui.wire_tool import WireType
from electrical_schematics.pdf.auto_loader import DiagramAutoLoader
from electrical_schematics.database import DatabaseManager, initialize_database_with_defaults
from electrical_schematics.config import get_settings, DigiKeyConfig
from electrical_schematics.persistence import ProjectManager, ProjectInfo
from electrical_schematics.api.digikey_client import DigiKeyClient, DigiKeyAPIError
from electrical_schematics.gui.parts_import_dialog import PartsImportDialog


class ComponentDialog(QDialog):
    """Enhanced dialog for adding/editing a component."""

    def __init__(self, parent: Optional[QWidget] = None, template_data: dict = None, db_manager: DatabaseManager = None, is_edit_mode: bool = False):
        """Initialize the component dialog.

        Args:
            parent: Parent widget
            template_data: Optional component template data from library
            db_manager: Database manager for saving to library
            is_edit_mode: True if editing existing component (enables Save to Library)
        """
        super().__init__(parent)
        self.setWindowTitle("Component Properties")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self.template_data = template_data or {}
        self.db_manager = db_manager
        self.is_edit_mode = is_edit_mode

        # Main layout
        main_layout = QVBoxLayout(self)

        # Tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Basic Info tab
        self._create_basic_tab()

        # DigiKey Info tab (if template has DigiKey data)
        if self.template_data.get('manufacturer') or self.template_data.get('part_number'):
            self._create_digikey_tab()

        # Advanced tab (state, terminals)
        self._create_advanced_tab()

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # Add "Save to Library" button if in edit mode and db_manager available
        if self.is_edit_mode and self.db_manager:
            save_to_lib_btn = buttons.addButton("Save to Library", QDialogButtonBox.ActionRole)
            save_to_lib_btn.setToolTip("Save this component to the library for reuse")
            save_to_lib_btn.clicked.connect(self._save_to_library)

        main_layout.addWidget(buttons)

    def _create_basic_tab(self) -> None:
        """Create basic information tab."""
        widget = QWidget()
        layout = QFormLayout(widget)

        # Designation
        self.designation_edit = QLineEdit()
        self.designation_edit.setPlaceholderText("e.g., K1, S1, M1")
        layout.addRow("Designation:", self.designation_edit)

        # Type
        self.type_combo = QComboBox()
        for comp_type in IndustrialComponentType:
            self.type_combo.addItem(comp_type.value, comp_type)
        layout.addRow("Type:", self.type_combo)

        # Description
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Brief description of component")
        layout.addRow("Description:", self.description_edit)

        # Voltage Rating
        self.voltage_edit = QLineEdit()
        self.voltage_edit.setPlaceholderText("e.g., 24VDC, 400VAC")
        layout.addRow("Voltage Rating:", self.voltage_edit)

        # DigiKey section
        layout.addRow(QLabel(""))  # Separator
        digikey_label = QLabel("DigiKey Integration")
        digikey_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        layout.addRow(digikey_label)

        # Part number field with fetch button
        digikey_layout = QHBoxLayout()
        self.part_number_edit = QLineEdit()
        self.part_number_edit.setPlaceholderText("Enter DigiKey or manufacturer part number")
        if self.template_data.get('part_number'):
            self.part_number_edit.setText(self.template_data['part_number'])
        digikey_layout.addWidget(self.part_number_edit)

        self.fetch_btn = QPushButton("Fetch from DigiKey")
        self.fetch_btn.setToolTip("Query DigiKey API to populate component data")
        self.fetch_btn.clicked.connect(self._fetch_from_digikey)
        digikey_layout.addWidget(self.fetch_btn)

        layout.addRow("Part Number:", digikey_layout)

        # Position (read-only, shown after placement)
        position_layout = QHBoxLayout()
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(0, 10000)
        self.x_spin.setDecimals(1)
        self.x_spin.setEnabled(False)
        position_layout.addWidget(QLabel("X:"))
        position_layout.addWidget(self.x_spin)

        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(0, 10000)
        self.y_spin.setDecimals(1)
        self.y_spin.setEnabled(False)
        position_layout.addWidget(QLabel("Y:"))
        position_layout.addWidget(self.y_spin)

        layout.addRow("Position:", position_layout)

        # Size
        size_layout = QHBoxLayout()
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(10, 500)
        self.width_spin.setValue(40)
        self.width_spin.setDecimals(0)
        size_layout.addWidget(QLabel("Width:"))
        size_layout.addWidget(self.width_spin)

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(10, 500)
        self.height_spin.setValue(30)
        self.height_spin.setDecimals(0)
        size_layout.addWidget(QLabel("Height:"))
        size_layout.addWidget(self.height_spin)

        layout.addRow("Size:", size_layout)

        self.tabs.addTab(widget, "Basic Info")

    def _create_digikey_tab(self) -> None:
        """Create DigiKey information tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Manufacturer info
        info_group = QGroupBox("Product Information")
        info_layout = QFormLayout(info_group)

        self.manufacturer_label = QLabel(self.template_data.get('manufacturer', 'N/A'))
        info_layout.addRow("Manufacturer:", self.manufacturer_label)

        self.part_number_label = QLabel(self.template_data.get('part_number', 'N/A'))
        info_layout.addRow("Part Number:", self.part_number_label)

        # Datasheet link (if available)
        datasheet_url = self.template_data.get('datasheet_url')
        if datasheet_url:
            datasheet_link = QLabel(f'<a href="{datasheet_url}">View Datasheet</a>')
            datasheet_link.setOpenExternalLinks(True)
            info_layout.addRow("Datasheet:", datasheet_link)

        layout.addWidget(info_group)

        # Image preview (if available)
        image_path = self.template_data.get('image_path')
        if image_path and Path(image_path).exists():
            image_group = QGroupBox("Component Image")
            image_layout = QVBoxLayout(image_group)

            image_label = QLabel()
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                image_label.setPixmap(scaled_pixmap)
                image_label.setAlignment(Qt.AlignCenter)

            image_layout.addWidget(image_label)
            layout.addWidget(image_group)

        # Technical specifications (placeholder)
        specs_group = QGroupBox("Technical Specifications")
        specs_layout = QVBoxLayout(specs_group)

        self.specs_table = QTableWidget(0, 2)
        self.specs_table.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.specs_table.horizontalHeader().setStretchLastSection(True)
        specs_layout.addWidget(self.specs_table)

        # Add some placeholder specs if available
        if self.template_data.get('default_voltage'):
            row = self.specs_table.rowCount()
            self.specs_table.insertRow(row)
            self.specs_table.setItem(row, 0, QTableWidgetItem("Rated Voltage"))
            self.specs_table.setItem(row, 1, QTableWidgetItem(self.template_data['default_voltage']))

        layout.addWidget(specs_group)
        layout.addStretch()

        self.tabs.addTab(widget, "DigiKey Info")

    def _create_advanced_tab(self) -> None:
        """Create advanced settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # State section (for sensors/switches)
        state_group = QGroupBox("Sensor/Switch State")
        state_layout = QFormLayout(state_group)

        self.state_combo = QComboBox()
        for state in SensorState:
            self.state_combo.addItem(state.value, state)
        state_layout.addRow("Current State:", self.state_combo)

        self.normally_open_check = QCheckBox("Normally Open (NO)")
        self.normally_open_check.setChecked(True)
        state_layout.addRow("Contact Type:", self.normally_open_check)

        layout.addWidget(state_group)

        # Terminal count (for reference)
        terminal_group = QGroupBox("Terminal Information")
        terminal_layout = QFormLayout(terminal_group)

        terminal_info = QLabel("Terminals are automatically positioned based on component type.\n"
                               "Contactors: 4 terminals (2 coil, 2 contact)\n"
                               "Sensors: 3 terminals (2 power, 1 output)\n"
                               "Power Supplies: 2 terminals (top/bottom)\n"
                               "Motors: 3 terminals (three-phase)\n"
                               "PLCs: 8 terminals (along edge)")
        terminal_info.setWordWrap(True)
        terminal_info.setStyleSheet("color: gray; font-size: 10px;")
        terminal_layout.addRow(terminal_info)

        layout.addWidget(terminal_group)

        layout.addStretch()

        self.tabs.addTab(widget, "Advanced")

    def _fetch_from_digikey(self) -> None:
        """Fetch component data from DigiKey API."""
        part_number = self.part_number_edit.text().strip()

        if not part_number:
            QMessageBox.warning(self, "Missing Part Number", "Please enter a part number to fetch from DigiKey.")
            return

        # Disable fetch button during query
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("Fetching...")

        try:
            # Get DigiKey configuration
            settings = get_settings()
            digikey_config = settings.get_digikey_config()

            if not digikey_config.client_id or not digikey_config.client_secret:
                QMessageBox.warning(
                    self,
                    "DigiKey Not Configured",
                    "DigiKey API credentials are not configured.\n\n"
                    "Please configure your Client ID and Client Secret in the settings."
                )
                return

            # Create DigiKey client and fetch product details
            client = DigiKeyClient(digikey_config)
            product = client.get_product_details(part_number)

            if not product:
                QMessageBox.information(
                    self,
                    "Product Not Found",
                    f"No product found for part number: {part_number}"
                )
                return

            # Populate basic fields
            if product.description:
                self.description_edit.setText(product.description)

            # Extract voltage rating from parameters
            voltage = None
            if 'Voltage - Rated' in product.parameters:
                voltage = product.parameters['Voltage - Rated']
            elif 'Voltage Rating' in product.parameters:
                voltage = product.parameters['Voltage Rating']
            elif 'Voltage - Supply' in product.parameters:
                voltage = product.parameters['Voltage - Supply']

            if voltage:
                self.voltage_edit.setText(voltage)

            # Store fetched data in template_data for DigiKey tab
            self.template_data['manufacturer'] = product.manufacturer
            self.template_data['part_number'] = product.part_number
            self.template_data['manufacturer_part_number'] = product.manufacturer_part_number
            self.template_data['datasheet_url'] = product.primary_datasheet
            self.template_data['description'] = product.description
            self.template_data['detailed_description'] = product.detailed_description
            self.template_data['parameters'] = product.parameters
            self.template_data['category'] = product.category
            self.template_data['family'] = product.family

            # Download product image if available
            if product.primary_photo:
                try:
                    image_data = client.download_product_image(product.primary_photo)
                    if image_data:
                        # Save to temporary file
                        import tempfile
                        import os
                        temp_dir = tempfile.gettempdir()
                        image_path = os.path.join(temp_dir, f"{product.part_number}.jpg")
                        with open(image_path, 'wb') as f:
                            f.write(image_data)
                        self.template_data['image_path'] = image_path
                except Exception as e:
                    print(f"Failed to download image: {e}")

            # Remove existing DigiKey tab if present
            for i in range(self.tabs.count()):
                if self.tabs.tabText(i) == "DigiKey Info":
                    self.tabs.removeTab(i)
                    break

            # Create new DigiKey tab at index 1 (after Basic Info)
            self._create_digikey_tab_with_data(product)

            QMessageBox.information(
                self,
                "Data Fetched Successfully",
                f"Successfully fetched data for:\n\n"
                f"Manufacturer: {product.manufacturer}\n"
                f"Part Number: {product.manufacturer_part_number}\n"
                f"Description: {product.description[:100]}..."
            )

        except DigiKeyAPIError as e:
            QMessageBox.critical(
                self,
                "DigiKey API Error",
                f"Failed to fetch data from DigiKey:\n\n{str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An unexpected error occurred:\n\n{str(e)}"
            )
        finally:
            # Re-enable fetch button
            self.fetch_btn.setEnabled(True)
            self.fetch_btn.setText("Fetch from DigiKey")

    def _create_digikey_tab_with_data(self, product) -> None:
        """Create DigiKey information tab with fetched product data.

        Args:
            product: DigiKeyProductDetails object
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Manufacturer info
        info_group = QGroupBox("Product Information")
        info_layout = QFormLayout(info_group)

        info_layout.addRow("Manufacturer:", QLabel(product.manufacturer))
        info_layout.addRow("Part Number:", QLabel(product.manufacturer_part_number))
        info_layout.addRow("DigiKey PN:", QLabel(product.part_number))

        if product.category:
            info_layout.addRow("Category:", QLabel(product.category))
        if product.family:
            info_layout.addRow("Family:", QLabel(product.family))

        # Datasheet link
        if product.primary_datasheet:
            datasheet_link = QLabel(f'<a href="{product.primary_datasheet}">View Datasheet</a>')
            datasheet_link.setOpenExternalLinks(True)
            info_layout.addRow("Datasheet:", datasheet_link)

        # Product URL
        if product.product_url:
            product_link = QLabel(f'<a href="{product.product_url}">View on DigiKey</a>')
            product_link.setOpenExternalLinks(True)
            info_layout.addRow("Product Page:", product_link)

        layout.addWidget(info_group)

        # Image preview
        image_path = self.template_data.get('image_path')
        if image_path and Path(image_path).exists():
            image_group = QGroupBox("Component Image")
            image_layout = QVBoxLayout(image_group)

            image_label = QLabel()
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                image_label.setPixmap(scaled_pixmap)
                image_label.setAlignment(Qt.AlignCenter)

            image_layout.addWidget(image_label)
            layout.addWidget(image_group)

        # Technical specifications
        if product.parameters:
            specs_group = QGroupBox("Technical Specifications")
            specs_layout = QVBoxLayout(specs_group)

            specs_table = QTableWidget(0, 2)
            specs_table.setHorizontalHeaderLabels(["Parameter", "Value"])
            specs_table.horizontalHeader().setStretchLastSection(True)

            for param_name, param_value in product.parameters.items():
                row = specs_table.rowCount()
                specs_table.insertRow(row)
                specs_table.setItem(row, 0, QTableWidgetItem(param_name))
                specs_table.setItem(row, 1, QTableWidgetItem(str(param_value)))

            specs_layout.addWidget(specs_table)
            layout.addWidget(specs_group)

        # Availability and pricing
        if product.quantity_available or product.standard_pricing:
            avail_group = QGroupBox("Availability & Pricing")
            avail_layout = QFormLayout(avail_group)

            if product.quantity_available:
                avail_layout.addRow("In Stock:", QLabel(str(product.quantity_available)))
            if product.minimum_order_quantity:
                avail_layout.addRow("Min Order Qty:", QLabel(str(product.minimum_order_quantity)))

            layout.addWidget(avail_group)

        layout.addStretch()

        # Insert tab at index 1 (after Basic Info, before Advanced)
        self.tabs.insertTab(1, widget, "DigiKey Info")
        # Switch to the new tab
        self.tabs.setCurrentIndex(1)

    def _save_to_library(self) -> None:
        """Save current component to library."""
        if not self.db_manager:
            QMessageBox.warning(self, "Error", "Database manager not available.")
            return

        # Get current values from dialog
        designation_prefix = ''.join([c for c in self.designation_edit.text() if not c.isdigit()])
        comp_type = self.type_combo.currentData()
        description = self.description_edit.text()
        voltage = self.voltage_edit.text()
        part_number = self.part_number_edit.text() if hasattr(self, 'part_number_edit') else ""

        # Ask for category and name
        category, ok = QInputDialog.getText(
            self,
            "Save to Library",
            "Enter category (e.g., Contactors, Sensors, Motors):"
        )

        if not ok or not category:
            return

        name, ok = QInputDialog.getText(
            self,
            "Save to Library",
            "Enter component name:",
            text=description[:50] if description else f"{comp_type.value} {voltage}"
        )

        if not ok or not name:
            return

        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()

            # Insert into component_library
            cursor.execute("""
                INSERT INTO component_library (
                    category, subcategory, name, designation_prefix,
                    component_type, default_voltage, manufacturer,
                    part_number, datasheet_url, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                category,
                "",  # subcategory
                name,
                designation_prefix,
                comp_type.value,
                voltage,
                self.template_data.get('manufacturer', ''),
                part_number,
                self.template_data.get('datasheet_url', ''),
                description
            ))

            # Save specs if available
            component_id = cursor.lastrowid

            if self.template_data.get('parameters'):
                for param_name, param_value in self.template_data['parameters'].items():
                    cursor.execute("""
                        INSERT INTO component_specs (component_id, spec_name, spec_value)
                        VALUES (?, ?, ?)
                    """, (component_id, param_name, str(param_value)))

            conn.commit()

            QMessageBox.information(
                self,
                "Success",
                f"Component '{name}' saved to library under category '{category}'!"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save component to library:\n\n{str(e)}"
            )

    def set_position(self, x: float, y: float) -> None:
        """Set the position fields.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        self.x_spin.setValue(x)
        self.y_spin.setValue(y)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.diagram: Optional[WiringDiagram] = None
        self.simulator: Optional[VoltageSimulator] = None
        self.interactive_sim: Optional[InteractiveSimulator] = None
        self.analyzer: Optional[FaultAnalyzer] = None
        self.project_modified = False
        self.current_project_id: Optional[int] = None
        self.wire_drawing_mode = False

        # Initialize database and project manager
        settings = get_settings()
        db_path = settings.get_database_path()
        self.db_manager = initialize_database_with_defaults(db_path)
        self.project_manager = ProjectManager(self.db_manager)

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Industrial Wiring Diagram Analyzer")
        self.setGeometry(100, 100, 1600, 900)

        # Menu bar
        self._create_menu_bar()

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)

        # Toolbar
        toolbar = self._create_toolbar()
        main_layout.addLayout(toolbar)

        # Main splitter: PDF viewer | Interactive Panel | Analysis
        main_splitter = QSplitter(Qt.Horizontal)

        # Left: PDF viewer
        self.pdf_viewer = PDFViewer()
        self.pdf_viewer.component_dropped.connect(self._on_component_dropped)
        self.pdf_viewer.component_double_clicked.connect(self._on_component_double_clicked)
        self.pdf_viewer.component_selected.connect(self._on_component_selected)
        self.pdf_viewer.wire_completed.connect(self._on_wire_completed)
        self.pdf_viewer.wire_drawing_state_changed.connect(self._on_wire_state_changed)
        self.pdf_viewer.component_edit_requested.connect(self._on_component_double_clicked)  # Reuse edit handler
        self.pdf_viewer.component_delete_requested.connect(self._on_context_menu_delete)
        self.pdf_viewer.component_toggle_requested.connect(self._on_context_menu_toggle)
        self.pdf_viewer.component_moved.connect(self._on_component_moved)
        self.pdf_viewer.page_changed.connect(self._on_page_changed)
        main_splitter.addWidget(self.pdf_viewer)

        # Middle: Interactive simulation panel
        self.interactive_panel = InteractivePanel()
        self.interactive_panel.component_toggled.connect(self._on_component_toggled)
        self.interactive_panel.simulation_updated.connect(self._on_simulation_updated)
        self.interactive_panel.go_to_page.connect(self._on_goto_page)
        self.interactive_panel.component_selected.connect(self._on_panel_component_selected)
        main_splitter.addWidget(self.interactive_panel)

        # Right: Analysis panel
        self.analysis_panel = QTextEdit()
        self.analysis_panel.setReadOnly(True)
        self.analysis_panel.setPlaceholderText("Simulation and diagnostic results will appear here...")
        main_splitter.addWidget(self.analysis_panel)

        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 2)
        main_splitter.setStretchFactor(2, 2)

        main_layout.addWidget(main_splitter)

        # Component palette dock widget
        self.component_palette = ComponentPalette(self.db_manager)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.component_palette)

        # Status bar with component count label
        self.component_count_label = QLabel("")
        self.statusBar().addPermanentWidget(self.component_count_label)
        self.statusBar().showMessage("Ready - Load a PDF wiring diagram to begin")

    def _create_menu_bar(self) -> None:
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        # New Project
        new_action = file_menu.addAction("&New Project")
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_project)

        # Open PDF
        open_pdf_action = file_menu.addAction("&Open PDF...")
        open_pdf_action.setShortcut("Ctrl+O")
        open_pdf_action.triggered.connect(self._open_pdf)

        file_menu.addSeparator()

        # Save
        self.save_action = file_menu.addAction("&Save Project")
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.setEnabled(False)
        self.save_action.triggered.connect(self._save_project)

        # Save As
        self.save_as_action = file_menu.addAction("Save Project &As...")
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.setEnabled(False)
        self.save_as_action.triggered.connect(self._save_project_as)

        file_menu.addSeparator()

        # Load Project
        load_action = file_menu.addAction("&Load Project...")
        load_action.setShortcut("Ctrl+L")
        load_action.triggered.connect(self._load_project_dialog)

        file_menu.addSeparator()

        # Export
        self.export_action = file_menu.addAction("&Export to JSON...")
        self.export_action.setEnabled(False)
        self.export_action.triggered.connect(self._export_project)

        # Import
        import_action = file_menu.addAction("&Import from JSON...")
        import_action.triggered.connect(self._import_project)

        # Import Parts from PDF (OCR)
        import_parts_action = file_menu.addAction("Import Parts from &PDF...")
        import_parts_action.setToolTip("Scan PDF parts list with OCR and import to component library")
        import_parts_action.triggered.connect(self._import_parts_from_pdf)

        file_menu.addSeparator()

        # Exit
        exit_action = file_menu.addAction("E&xit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        delete_comp_action = edit_menu.addAction("Delete Component")
        delete_comp_action.setShortcut("Delete")
        delete_comp_action.triggered.connect(self._delete_selected_component)

        # View menu
        view_menu = menubar.addMenu("&View")

        toggle_palette_action = view_menu.addAction("Toggle Component &Palette")
        toggle_palette_action.setCheckable(True)
        toggle_palette_action.setChecked(True)
        toggle_palette_action.triggered.connect(
            lambda: self.component_palette.setVisible(toggle_palette_action.isChecked())
        )

    def _create_toolbar(self) -> QHBoxLayout:
        """Create the toolbar."""
        toolbar = QHBoxLayout()

        open_btn = QPushButton("Open PDF")
        open_btn.setToolTip("Open a PDF wiring diagram (Ctrl+O)")
        open_btn.clicked.connect(self._open_pdf)
        toolbar.addWidget(open_btn)

        prev_btn = QPushButton("< Prev")
        prev_btn.setToolTip("Go to the previous page")
        prev_btn.clicked.connect(self._go_prev_page)
        toolbar.addWidget(prev_btn)

        next_btn = QPushButton("Next >")
        next_btn.setToolTip("Go to the next page")
        next_btn.clicked.connect(self._go_next_page)
        toolbar.addWidget(next_btn)

        # Page indicator
        self.page_label = QLabel("Page: 0/0")
        self.page_label.setToolTip("Current page / Total pages")
        self.page_label.setMinimumWidth(100)
        toolbar.addWidget(self.page_label)

        zoom_label = QLabel("Zoom:")
        toolbar.addWidget(zoom_label)

        zoom_spin = QDoubleSpinBox()
        zoom_spin.setRange(0.1, 5.0)
        zoom_spin.setSingleStep(0.1)
        zoom_spin.setValue(1.0)
        zoom_spin.setSuffix("x")
        zoom_spin.valueChanged.connect(lambda v: self.pdf_viewer.set_zoom(v))
        toolbar.addWidget(zoom_spin)

        # Overlay toggle button
        self.overlay_btn = QPushButton("Overlays")
        self.overlay_btn.setToolTip("Toggle component overlay visibility")
        self.overlay_btn.setCheckable(True)
        self.overlay_btn.setChecked(True)
        self.overlay_btn.clicked.connect(self._toggle_overlays)
        toolbar.addWidget(self.overlay_btn)

        # Wire drawing mode button
        self.wire_mode_btn = QPushButton("Draw Wire")
        self.wire_mode_btn.setToolTip("Toggle wire drawing mode - click on terminals to connect them")
        self.wire_mode_btn.setCheckable(True)
        self.wire_mode_btn.setChecked(False)
        self.wire_mode_btn.setStyleSheet("""
            QPushButton:checked {
                background-color: #90EE90;
                border: 2px solid #228B22;
                font-weight: bold;
            }
        """)
        self.wire_mode_btn.clicked.connect(self._toggle_wire_mode)
        toolbar.addWidget(self.wire_mode_btn)

        # Wire type selector buttons
        wire_label = QLabel("  Type:")
        toolbar.addWidget(wire_label)

        self.wire_24v_btn = QPushButton("24VDC")
        self.wire_24v_btn.setToolTip("Draw 24VDC power wire (red)")
        self.wire_24v_btn.setCheckable(True)
        self.wire_24v_btn.setChecked(True)
        self.wire_24v_btn.setStyleSheet("QPushButton:checked { background-color: #E74C3C; color: white; font-weight: bold; }")
        self.wire_24v_btn.clicked.connect(lambda: self._set_wire_type(WireType.DC_24V))
        toolbar.addWidget(self.wire_24v_btn)

        self.wire_0v_btn = QPushButton("0V")
        self.wire_0v_btn.setToolTip("Draw 0V ground wire (blue)")
        self.wire_0v_btn.setCheckable(True)
        self.wire_0v_btn.setStyleSheet("QPushButton:checked { background-color: #3498DB; color: white; font-weight: bold; }")
        self.wire_0v_btn.clicked.connect(lambda: self._set_wire_type(WireType.DC_0V))
        toolbar.addWidget(self.wire_0v_btn)

        self.wire_ac_btn = QPushButton("AC")
        self.wire_ac_btn.setToolTip("Draw AC power wire (gray)")
        self.wire_ac_btn.setCheckable(True)
        self.wire_ac_btn.setStyleSheet("QPushButton:checked { background-color: #2C3E50; color: white; font-weight: bold; }")
        self.wire_ac_btn.clicked.connect(lambda: self._set_wire_type(WireType.AC_POWER))
        toolbar.addWidget(self.wire_ac_btn)

        toolbar.addStretch()

        # Delete component button
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setToolTip("Delete selected component (Delete key)")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._delete_selected_component)
        toolbar.addWidget(self.delete_btn)

        return toolbar

    def _create_control_panel(self) -> QWidget:
        """Create the control panel for simulation and diagnostics."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Simulation section
        sim_group = QGroupBox("Voltage Flow Simulation")
        sim_layout = QVBoxLayout(sim_group)

        sim_btn = QPushButton("Run Simulation")
        sim_btn.clicked.connect(self._run_simulation)
        sim_layout.addWidget(sim_btn)

        reset_btn = QPushButton("Reset All Sensors")
        reset_btn.clicked.connect(self._reset_sensors)
        sim_layout.addWidget(reset_btn)

        sim_layout.addStretch()
        layout.addWidget(sim_group)

        # Diagnostics section
        diag_group = QGroupBox("Fault Diagnostics")
        diag_layout = QVBoxLayout(diag_group)

        form = QFormLayout()

        self.fault_component_edit = QLineEdit()
        self.fault_component_edit.setPlaceholderText("e.g., M1, K1")
        form.addRow("Component:", self.fault_component_edit)

        self.fault_state_combo = QComboBox()
        self.fault_state_combo.addItems(["Energized", "De-energized"])
        form.addRow("Expected State:", self.fault_state_combo)

        self.fault_symptom_edit = QLineEdit()
        self.fault_symptom_edit.setPlaceholderText("e.g., Motor won't start")
        form.addRow("Symptom:", self.fault_symptom_edit)

        diag_layout.addLayout(form)

        diagnose_btn = QPushButton("Diagnose Fault")
        diagnose_btn.clicked.connect(self._diagnose_fault)
        diag_layout.addWidget(diagnose_btn)

        diag_layout.addStretch()
        layout.addWidget(diag_group)

        layout.addStretch()

        return panel

    def _open_pdf(self) -> None:
        """Open a PDF wiring diagram with automatic analysis."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Wiring Diagram PDF",
            "",
            "PDF Files (*.pdf);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Load PDF in viewer

            # Update page indicator after load
            self.pdf_viewer.load_pdf(file_path)

            # Auto-detect format and load diagram
            self.statusBar().showMessage("Analyzing PDF format...")
            self.diagram, format_type = DiagramAutoLoader.load_diagram(Path(file_path))

            # Initialize simulators and analyzer
            self.simulator = VoltageSimulator(self.diagram)
            self.interactive_sim = InteractiveSimulator(self.diagram)
            self.analyzer = FaultAnalyzer(self.diagram)

            # Set diagram in interactive panel
            self.interactive_panel.set_diagram(self.diagram)

            # Set current page in interactive panel
            self.interactive_panel.set_current_page(self.pdf_viewer.current_page)

            # Sync wires to PDF viewer
            if self.diagram.wires:
                self.pdf_viewer.set_wires(self.diagram.wires)

            # Update component count
            self._update_component_count()

            # Show appropriate message based on format
            if format_type == "parts_list":
                self.statusBar().showMessage(f"Loaded with parts list: {file_path}")

                # Show automatic analysis
                summary = DiagramAutoLoader.create_summary(self.diagram)
                info = "PARTS LIST DETECTED - Components auto-loaded!\n"
                info += "=" * 60 + "\n\n"
                info += summary
                info += "\n" + "=" * 60 + "\n"
                info += "Components extracted from parts list.\n"
                info += "You can now:\n"
                info += "  - Edit component properties (double-click)\n"
                info += "  - Drag components from library onto the PDF\n"
                info += "  - Draw wires between components\n"
                info += "  - Save components to library for reuse\n\n"

                self.analysis_panel.setText(info)

                # Show component list
                self._display_component_list()

                # Update overlays with auto-detected components
                self.pdf_viewer.set_component_overlays(self.diagram.components, [])

            elif format_type == "drawer":
                self.statusBar().showMessage(f"Loaded DRAWER format: {file_path}")

                # Show automatic analysis
                summary = DiagramAutoLoader.create_summary(self.diagram)
                info = "DRAWER FORMAT DETECTED - Auto-loaded!\n"
                info += "=" * 60 + "\n\n"
                info += summary
                info += "\n" + "=" * 60 + "\n"
                info += "Ready for simulation and diagnostics!\n\n"
                info += "Wire Color Coding:\n"
                info += "  - RED lines = 24VDC (control voltage)\n"
                info += "  - BLUE lines = 0V (reference)\n"
                info += "  - GREEN lines = PE (protective earth/ground)\n"

                self.analysis_panel.setText(info)

                # Show component list
                self._display_component_list()

            else:
                self.statusBar().showMessage(f"Loaded (manual mode): {file_path}")

                info = "PDF loaded in MANUAL MODE\n"
                info += "=" * 60 + "\n\n"
                info += "This PDF does not appear to be in DRAWER format.\n"
                info += "Click and drag on the diagram to manually annotate components.\n\n"
                info += "Instructions:\n"
                info += "1. Select an area to create a component\n"
                info += "2. Enter component details (designation, type, voltage)\n"
                info += "3. Run simulation to trace voltage flow\n"
                info += "4. Use diagnostics to troubleshoot faults\n"

                self.analysis_panel.setText(info)

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            QMessageBox.critical(self, "Error", f"Error loading PDF: {e}\n\n{error_detail}")
            self.statusBar().showMessage(f"Error loading file: {e}")

    def _run_simulation(self) -> None:
        """Run voltage flow simulation."""
        if not self.simulator or not self.diagram:
            QMessageBox.warning(self, "Warning", "No diagram loaded")
            return

        energized = self.simulator.simulate()

        result = "Voltage Flow Simulation\n"
        result += "=" * 50 + "\n\n"

        result += "Power Sources:\n"
        for ps in self.diagram.get_power_sources():
            result += f"  {ps.designation}: {ps.voltage_rating}\n"
        result += "\n"

        result += "Energized Components:\n"
        for comp_id, is_energized in energized.items():
            comp = self.diagram.get_component(comp_id)
            if comp and is_energized:
                result += f"  [OK] {comp.designation} - {comp.description or comp.type.value}\n"

        result += "\n\nDe-energized Components:\n"
        for comp in self.diagram.components:
            if not energized.get(comp.id, False) and not comp.is_power_source():
                result += f"  [X] {comp.designation} - {comp.description or comp.type.value}\n"

        self.analysis_panel.setText(result)
        self.statusBar().showMessage("Simulation complete")

    def _reset_sensors(self) -> None:
        """Reset all sensor states."""
        if self.diagram:
            self.diagram.reset_all_sensor_states()
            self.statusBar().showMessage("All sensors reset to UNKNOWN state")

    def _diagnose_fault(self) -> None:
        """Run fault diagnostics."""
        if not self.analyzer or not self.diagram:
            QMessageBox.warning(self, "Warning", "No diagram loaded")
            return

        component = self.fault_component_edit.text().strip()
        if not component:
            QMessageBox.warning(self, "Warning", "Please enter a component designation")
            return

        fault = FaultCondition(
            symptom=self.fault_symptom_edit.text(),
            expected_component=component,
            expected_state=self.fault_state_combo.currentText()
        )

        result = self.analyzer.diagnose(fault)

        output = "Fault Diagnostic Report\n"
        output += "=" * 50 + "\n\n"
        output += f"Component: {fault.expected_component}\n"
        output += f"Expected State: {fault.expected_state}\n"
        output += f"Symptom: {fault.symptom}\n\n"

        output += "Possible Causes:\n"
        for i, cause in enumerate(result.possible_causes, 1):
            output += f"  {i}. {cause}\n"

        output += "\n"
        output += "Suggested Checks:\n"
        for i, check in enumerate(result.suggested_checks, 1):
            output += f"  {i}. {check}\n"

        if result.affected_components:
            output += "\n"
            output += "Affected Components:\n"
            for comp in result.affected_components:
                output += f"  - {comp}\n"

        self.analysis_panel.setText(output)
        self.statusBar().showMessage("Diagnostic complete")

    def _display_component_list(self) -> None:
        """Display a list of loaded components (for DRAWER format)."""
        if not self.diagram or not self.diagram.components:
            return

        # This would ideally go in a separate widget, but for now append to analysis panel
        current_text = self.analysis_panel.toPlainText()

        # Group components by voltage
        from collections import defaultdict
        by_voltage = defaultdict(list)
        for comp in self.diagram.components:
            by_voltage[comp.voltage_rating].append(comp)

        component_list = "\n\nCOMPONENT LIST:\n"
        component_list += "=" * 60 + "\n"

        for voltage in ['24VDC', '5VDC', '230VAC', '400VAC', 'UNKNOWN']:
            if voltage not in by_voltage:
                continue

            comps = sorted(by_voltage[voltage], key=lambda c: c.designation)
            component_list += f"\n{voltage} ({len(comps)} devices):\n"

            for comp in comps[:10]:  # Show first 10
                desc = comp.get_display_description(40) if hasattr(comp, 'get_display_description') else (comp.description or '')[:40]
                component_list += f"  {comp.designation:10s} - {desc}\n"

            if len(comps) > 10:
                component_list += f"  ... and {len(comps) - 10} more\n"

        self.analysis_panel.setText(current_text + component_list)

    def _on_component_toggled(self, designation: str) -> None:
        """Handle component toggle from interactive panel.

        Args:
            designation: Component designation that was toggled
        """
        # Update status message
        if self.diagram:
            component = self.diagram.get_component_by_designation(designation)
            if component:
                state = "ENERGIZED" if component.state == SensorState.ON else "DE-ENERGIZED"
                self.statusBar().showMessage(f"Toggled {designation} -> {state}")

    def _on_simulation_updated(self) -> None:
        """Handle simulation update."""
        if not self.interactive_sim or not self.diagram:
            return

        # Get energized components
        energized = self.interactive_sim.get_energized_components()
        energized_ids = [comp.id for comp in energized]

        # Update PDF overlays
        self.pdf_viewer.set_component_overlays(self.diagram.components, energized_ids)

        # Update wires
        if self.diagram.wires:
            self.pdf_viewer.set_wires(self.diagram.wires)

        # Update analysis panel with current state
        result = "INTERACTIVE SIMULATION - Current State\n"
        result += "=" * 60 + "\n\n"

        result += "24VDC Control Circuit:\n"
        for comp in energized:
            if comp.voltage_rating == "24VDC":
                desc = comp.get_display_description(40) if hasattr(comp, 'get_display_description') else (comp.description or '')[:40]
                result += f"  [OK] {comp.designation:10s} - {desc}\n"

        result += "\n400VAC Power Circuit:\n"
        for comp in energized:
            if comp.voltage_rating == "400VAC":
                desc = comp.get_display_description(40) if hasattr(comp, 'get_display_description') else (comp.description or '')[:40]
                result += f"  [OK] {comp.designation:10s} - {desc}\n"

        self.analysis_panel.setText(result)

    def _on_page_changed(self, page: int) -> None:
        """Handle page change from PDF viewer.

        Args:
            page: New page number (0-indexed)
        """
        # Update page label
        self._update_page_label()

        # Update interactive panel with current page
        self.interactive_panel.set_current_page(page)

        # Update component count
        self._update_component_count()

    def _on_goto_page(self, page: int) -> None:
        """Handle go to page request from interactive panel.

        Args:
            page: Page number to navigate to (0-indexed)
        """
        self.pdf_viewer.go_to_page(page)
        self._update_page_label()

    def _on_panel_component_selected(self, component_id: str) -> None:
        """Handle component selection from interactive panel.

        Args:
            component_id: ID of selected component
        """
        if component_id:
            # Select the component in PDF viewer
            self.pdf_viewer.select_component(component_id)

    def _update_page_label(self) -> None:
        """Update the page indicator label."""
        if self.pdf_viewer.renderer:
            current = self.pdf_viewer.current_page + 1
            total = self.pdf_viewer.renderer.get_page_count()
            self.page_label.setText(f"Page: {current}/{total}")
        else:
            self.page_label.setText("Page: 0/0")

    def _update_component_count(self) -> None:
        """Update the component count label in status bar."""
        if not self.diagram:
            self.component_count_label.setText("")
            return

        total = len(self.diagram.components)
        current_page = self.pdf_viewer.current_page

        # Count components on current page
        on_page = sum(1 for c in self.diagram.components if c.page == current_page)

        if on_page > 0:
            self.component_count_label.setText(f"Components: {on_page} on this page / {total} total")
        else:
            self.component_count_label.setText(f"Components: {total} total")

    def _go_prev_page(self) -> None:
        """Go to previous page and update label."""
        self.pdf_viewer.previous_page()
        self._update_page_label()

    def _go_next_page(self) -> None:
        """Go to next page and update label."""
        self.pdf_viewer.next_page()
        self._update_page_label()

    def _toggle_overlays(self) -> None:
        """Toggle visibility of component overlays."""
        show = self.overlay_btn.isChecked()
        self.pdf_viewer.toggle_overlays(show)

        if show:
            self.overlay_btn.setText("Show Overlays")
        else:
            self.overlay_btn.setText("Hide Overlays")

    def _on_component_dropped(self, x: float, y: float, component_data: dict) -> None:
        """Handle component drop from palette.

        Args:
            x: X coordinate in PDF coordinates
            y: Y coordinate in PDF coordinates
            component_data: Component template data
        """
        if not self.diagram:
            # Create new diagram if none exists
            self.diagram = WiringDiagram(
                name="Untitled",
                pdf_path=None,
                page_number=self.pdf_viewer.current_page
            )

        # Auto-generate designation
        prefix = component_data.get('designation_prefix', 'X')
        designation = self._generate_next_designation(prefix)

        # Show component properties dialog with template data
        dialog = ComponentDialog(self, template_data=component_data)
        dialog.designation_edit.setText(designation)
        dialog.set_position(x, y)

        # Pre-fill from template
        comp_type_str = component_data.get('type', 'OTHER')
        try:
            comp_type = IndustrialComponentType[comp_type_str]
            # Find and select type in combo
            for i in range(dialog.type_combo.count()):
                if dialog.type_combo.itemData(i) == comp_type:
                    dialog.type_combo.setCurrentIndex(i)
                    break
        except KeyError:
            comp_type = IndustrialComponentType.OTHER

        dialog.voltage_edit.setText(component_data.get('voltage', ''))
        dialog.description_edit.setText(component_data.get('description', ''))

        if dialog.exec() == QDialog.Accepted:
            # Create component with dialog values
            component = IndustrialComponent(
                id=f"comp_{uuid.uuid4().hex[:8]}",
                type=dialog.type_combo.currentData(),
                designation=dialog.designation_edit.text(),
                description=dialog.description_edit.text(),
                voltage_rating=dialog.voltage_edit.text(),
                x=x,
                y=y,
                width=dialog.width_spin.value(),
                height=dialog.height_spin.value(),
                page=self.pdf_viewer.current_page,
                state=dialog.state_combo.currentData(),
                normally_open=dialog.normally_open_check.isChecked()
            )

            # Add to diagram
            self.diagram.components.append(component)

            # Update PDF overlays immediately
            self.pdf_viewer.set_component_overlays(self.diagram.components, [])

            # Refresh display
            if self.interactive_sim:
                self._on_simulation_updated()
            else:
                # No simulator yet - create one
                self.simulator = VoltageSimulator(self.diagram)
                self.interactive_sim = InteractiveSimulator(self.diagram)
                self.analyzer = FaultAnalyzer(self.diagram)
                self.interactive_panel.set_diagram(self.diagram)

            # Update component count
            self._update_component_count()

            # Mark as modified and enable save
            self.project_modified = True
            self.save_action.setEnabled(True)
            self.save_as_action.setEnabled(True)
            self.export_action.setEnabled(True)

            self.statusBar().showMessage(f"Added component {component.designation} at ({x:.1f}, {y:.1f})")

    def _on_component_double_clicked(self, component: IndustrialComponent) -> None:
        """Handle component double-click for editing.

        Args:
            component: Component that was double-clicked
        """
        dialog = ComponentDialog(self, db_manager=self.db_manager, is_edit_mode=True)
        dialog.setWindowTitle("Edit Component")

        # Pre-fill with current values
        dialog.designation_edit.setText(component.designation)
        dialog.description_edit.setText(component.description or "")
        dialog.voltage_edit.setText(component.voltage_rating or "")
        dialog.set_position(component.x, component.y)
        dialog.width_spin.setValue(component.width)
        dialog.height_spin.setValue(component.height)

        # Select type
        for i in range(dialog.type_combo.count()):
            if dialog.type_combo.itemData(i) == component.type:
                dialog.type_combo.setCurrentIndex(i)
                break

        # Select state
        for i in range(dialog.state_combo.count()):
            if dialog.state_combo.itemData(i) == component.state:
                dialog.state_combo.setCurrentIndex(i)
                break

        dialog.normally_open_check.setChecked(component.normally_open)

        if dialog.exec() == QDialog.Accepted:
            # Update component
            component.designation = dialog.designation_edit.text()
            component.description = dialog.description_edit.text()
            component.voltage_rating = dialog.voltage_edit.text()
            component.type = dialog.type_combo.currentData()
            component.width = dialog.width_spin.value()
            component.height = dialog.height_spin.value()
            component.state = dialog.state_combo.currentData()
            component.normally_open = dialog.normally_open_check.isChecked()

            # Update PDF overlays
            self.pdf_viewer.set_component_overlays(self.diagram.components, [])

            # Refresh display
            if self.interactive_sim:
                self._on_simulation_updated()

            self.statusBar().showMessage(f"Updated component {component.designation}")

    def _on_component_selected(self, component_id: str) -> None:
        """Handle component selection.

        Args:
            component_id: ID of selected component (empty string if cleared)
        """
        if component_id and self.diagram:
            # Find and display component info
            component = self.diagram.get_component(component_id)
            if component:
                self.statusBar().showMessage(
                    f"Selected: {component.designation} - {component.type.value} "
                    f"({component.voltage_rating or 'No voltage rating'}) Page {component.page + 1}"
                )
                self.delete_btn.setEnabled(True)

                # Sync selection to interactive panel
                self.interactive_panel.select_component_by_id(component_id)
            else:
                self.statusBar().showMessage("Ready")
                self.delete_btn.setEnabled(False)
        else:
            # Selection cleared
            self.statusBar().showMessage("Ready")
            self.delete_btn.setEnabled(False)

    def _delete_selected_component(self) -> None:
        """Delete the currently selected component."""
        if not self.diagram:
            return

        selected = self.pdf_viewer.get_selected_component()
        if not selected:
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Component",
            f"Delete component {selected.designation}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Remove from diagram
            self.diagram.components = [c for c in self.diagram.components if c.id != selected.id]

            # Clear selection
            self.pdf_viewer.clear_selection()

            # Rebuild simulator/analyzer
            if self.diagram.components:
                self.simulator = VoltageSimulator(self.diagram)
                self.analyzer = FaultAnalyzer(self.diagram)
            else:
                self.simulator = None
                self.analyzer = None

            # Refresh display
            if self.interactive_sim:
                self._on_simulation_updated()

            # Update component count
            self._update_component_count()

            self.statusBar().showMessage(f"Deleted component {selected.designation}")
            self.project_modified = True


    def _on_context_menu_delete(self, component: IndustrialComponent) -> None:
        """Handle delete request from context menu.

        Args:
            component: Component to delete
        """
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Component",
            f"Delete component {component.designation}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Remove from diagram
            self.diagram.components = [c for c in self.diagram.components if c.id != component.id]

            # Clear selection
            self.pdf_viewer.clear_selection()

            # Rebuild simulator/analyzer
            if self.diagram.components:
                self.simulator = VoltageSimulator(self.diagram)
                self.analyzer = FaultAnalyzer(self.diagram)
            else:
                self.simulator = None
                self.analyzer = None

            # Refresh display
            if self.interactive_sim:
                self._on_simulation_updated()

            # Update component count
            self._update_component_count()

            self.statusBar().showMessage(f"Deleted component {component.designation}")
            self.project_modified = True

    def _on_context_menu_toggle(self, component: IndustrialComponent) -> None:
        """Handle toggle request from context menu.

        Args:
            component: Component to toggle
        """
        if self.interactive_sim:
            self.interactive_sim.toggle_component(component.designation)
            self._on_simulation_updated()
            self.statusBar().showMessage(f"Toggled component {component.designation}")


    def _on_component_moved(self, component, new_x: float, new_y: float) -> None:
        """Handle component move completion."""
        self.project_modified = True
        self.statusBar().showMessage(f"Moved {component.designation} to ({new_x:.1f}, {new_y:.1f})")

    def _toggle_wire_mode(self) -> None:
        """Toggle wire drawing mode."""
        self.wire_drawing_mode = self.wire_mode_btn.isChecked()
        self.pdf_viewer.set_wire_drawing_mode(self.wire_drawing_mode)

        if self.wire_drawing_mode:
            self.statusBar().showMessage("Wire drawing mode enabled - Click on a terminal to start drawing")
        else:
            self.statusBar().showMessage("Wire drawing mode disabled")

    def _set_wire_type(self, wire_type: WireType) -> None:
        """Set the wire type for drawing.

        Args:
            wire_type: Wire type to use
        """
        # Update button states
        self.wire_24v_btn.setChecked(wire_type == WireType.DC_24V)
        self.wire_0v_btn.setChecked(wire_type == WireType.DC_0V)
        self.wire_ac_btn.setChecked(wire_type == WireType.AC_POWER)

        # Set in PDF viewer
        self.pdf_viewer.set_wire_type(wire_type)

        # Update status
        wire_name = wire_type.value[2]
        if self.wire_drawing_mode:
            self.statusBar().showMessage(f"Wire type set to {wire_name} - Click terminal to start drawing")
        else:
            self.statusBar().showMessage(f"Wire type set to {wire_name}")

    def _on_wire_completed(self, wire: Wire) -> None:
        """Handle wire completion.

        Args:
            wire: Completed wire
        """
        if not self.diagram:
            # Create diagram if it doesn't exist
            self.diagram = WiringDiagram(
                name="Untitled",
                pdf_path=None,
                page_number=self.pdf_viewer.current_page
            )

        # Add wire to diagram
        self.diagram.wires.append(wire)

        # Mark as modified and enable save
        self.project_modified = True
        self.save_action.setEnabled(True)
        self.save_as_action.setEnabled(True)
        self.export_action.setEnabled(True)

        # Update status
        self.statusBar().showMessage(
            f"Wire completed: {wire.voltage_level} from {wire.from_component_id} to {wire.to_component_id}"
        )

        # Rebuild simulator if needed
        if self.diagram.components:
            self.simulator = VoltageSimulator(self.diagram)
            self.analyzer = FaultAnalyzer(self.diagram)

            # Re-run simulation if interactive sim is active
            if self.interactive_sim:
                self._on_simulation_updated()

    def _on_wire_state_changed(self, message: str) -> None:
        """Handle wire drawing state change.

        Args:
            message: State message
        """
        self.statusBar().showMessage(message)

    def _generate_next_designation(self, prefix: str) -> str:
        """Generate next available designation with given prefix.

        Args:
            prefix: Designation prefix (e.g., 'K', 'S', 'M')

        Returns:
            Next available designation (e.g., 'K1', 'K2', etc.)
        """
        if not self.diagram or not self.diagram.components:
            return f"{prefix}1"

        # Find all existing designations with this prefix
        existing = []
        for comp in self.diagram.components:
            if comp.designation.startswith(prefix):
                try:
                    num = int(comp.designation[len(prefix):])
                    existing.append(num)
                except ValueError:
                    continue

        # Return next number
        if existing:
            return f"{prefix}{max(existing) + 1}"
        else:
            return f"{prefix}1"

    def _new_project(self) -> None:
        """Create a new project."""
        if self.project_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Save current project before creating new one?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel
            )

            if reply == QMessageBox.Yes:
                self._save_project()
            elif reply == QMessageBox.Cancel:
                return

        # Clear current diagram
        self.diagram = None
        self.simulator = None
        self.interactive_sim = None
        self.analyzer = None
        self.current_project_id = None
        self.project_modified = False

        # Clear displays
        self.pdf_viewer.clear_overlays()
        self.pdf_viewer.clear_wires()
        self.interactive_panel.set_diagram(None)
        self.analysis_panel.clear()

        # Disable save/export
        self.save_action.setEnabled(False)
        self.save_as_action.setEnabled(False)
        self.export_action.setEnabled(False)

        # Update component count
        self._update_component_count()

        self.statusBar().showMessage("New project created - Open a PDF to begin")

    def _save_project(self) -> None:
        """Save current project."""
        if not self.diagram:
            QMessageBox.warning(self, "Warning", "No diagram to save")
            return

        if self.current_project_id:
            # Update existing project
            try:
                self.project_manager.update_project(
                    self.current_project_id,
                    self.diagram
                )
                self.project_modified = False
                self.statusBar().showMessage(f"Project saved (ID: {self.current_project_id})")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project: {e}")
        else:
            # New project - prompt for name
            self._save_project_as()

    def _save_project_as(self) -> None:
        """Save project with new name."""
        if not self.diagram:
            QMessageBox.warning(self, "Warning", "No diagram to save")
            return

        # Prompt for project name
        name, ok = QInputDialog.getText(
            self,
            "Save Project",
            "Enter project name:",
            text=self.diagram.name if self.diagram.name else "Untitled"
        )

        if not ok or not name:
            return

        # Prompt for description
        description, ok = QInputDialog.getText(
            self,
            "Save Project",
            "Enter project description (optional):"
        )

        if not ok:
            description = None

        try:
            project_id = self.project_manager.save_project(
                self.diagram,
                name,
                description
            )
            self.current_project_id = project_id
            self.project_modified = False

            # Enable save/export
            self.save_action.setEnabled(True)
            self.save_as_action.setEnabled(True)
            self.export_action.setEnabled(True)

            self.statusBar().showMessage(f"Project saved as '{name}' (ID: {project_id})")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save project: {e}")

    def _load_project_dialog(self) -> None:
        """Show dialog to select and load a project."""
        if self.project_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Save current project before loading?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel
            )

            if reply == QMessageBox.Yes:
                self._save_project()
            elif reply == QMessageBox.Cancel:
                return

        # Get list of projects
        projects = self.project_manager.list_projects()

        if not projects:
            QMessageBox.information(self, "No Projects", "No saved projects found")
            return

        # Create selection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Load Project")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)

        layout = QVBoxLayout(dialog)

        # Project list
        project_list = QListWidget()
        for project in projects:
            item_text = f"{project.name} ({project.component_count} components, {project.wire_count} wires)"
            item_text += f"\n  Modified: {project.modified_at.strftime('%Y-%m-%d %H:%M')}"
            if project.description:
                item_text += f"\n  {project.description}"

            project_list.addItem(item_text)
            project_list.item(project_list.count() - 1).setData(Qt.UserRole, project.id)

        layout.addWidget(QLabel("Select a project to load:"))
        layout.addWidget(project_list)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Open | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.Accepted:
            if project_list.currentItem():
                project_id = project_list.currentItem().data(Qt.UserRole)
                self._load_project(project_id)

    def _load_project(self, project_id: int) -> None:
        """Load a project by ID.

        Args:
            project_id: Project ID to load
        """
        try:
            # Load project
            diagram = self.project_manager.load_project(project_id)

            # Set as current diagram
            self.diagram = diagram
            self.current_project_id = project_id
            self.project_modified = False

            # Initialize simulators
            self.simulator = VoltageSimulator(self.diagram)
            self.interactive_sim = InteractiveSimulator(self.diagram)
            self.analyzer = FaultAnalyzer(self.diagram)

            # Load PDF if available
            if diagram.pdf_path and diagram.pdf_path.exists():
                self.pdf_viewer.load_pdf(str(diagram.pdf_path), diagram.page_number)

            # Update displays
            self.interactive_panel.set_diagram(self.diagram)
            self.interactive_panel.set_current_page(self.pdf_viewer.current_page)
            self.pdf_viewer.set_component_overlays(self.diagram.components, [])
            self.pdf_viewer.set_wires(self.diagram.wires)

            # Enable save/export
            self.save_action.setEnabled(True)
            self.save_as_action.setEnabled(True)
            self.export_action.setEnabled(True)

            # Update component count
            self._update_component_count()

            # Run initial simulation
            if self.interactive_sim:
                self._on_simulation_updated()

            self.statusBar().showMessage(f"Project '{diagram.name}' loaded (ID: {project_id})")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load project: {e}")

    def _export_project(self) -> None:
        """Export current project to JSON."""
        if not self.diagram or not self.current_project_id:
            QMessageBox.warning(self, "Warning", "No project to export")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Project",
            "",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                self.project_manager.export_project(self.current_project_id, Path(file_path))
                self.statusBar().showMessage(f"Project exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export project: {e}")

    def _import_project(self) -> None:
        """Import project from JSON."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Project",
            "",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                # Prompt for project name
                name, ok = QInputDialog.getText(
                    self,
                    "Import Project",
                    "Enter project name:",
                    text=Path(file_path).stem
                )

                if not ok or not name:
                    return

                project_id = self.project_manager.import_project(Path(file_path), name)
                self.statusBar().showMessage(f"Project imported (ID: {project_id})")

                # Ask if user wants to load it now
                reply = QMessageBox.question(
                    self,
                    "Load Project",
                    "Load the imported project now?",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    self._load_project(project_id)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import project: {e}")

    def _import_parts_from_pdf(self) -> None:
        """Import parts from PDF using OCR and DigiKey lookup."""
        # Get DigiKey config
        digikey_config = None
        settings = get_settings()
        if settings.digikey_client_id and settings.digikey_client_secret:
            digikey_config = DigiKeyConfig(
                client_id=settings.digikey_client_id,
                client_secret=settings.digikey_client_secret
            )

        # Use current PDF if loaded, otherwise let user browse
        pdf_path = self.pdf_viewer.pdf_path if hasattr(self.pdf_viewer, 'pdf_path') else None

        # Show import dialog
        dialog = PartsImportDialog(
            parent=self,
            db_manager=self.db_manager,
            pdf_path=pdf_path,
            digikey_config=digikey_config
        )

        if dialog.exec() == QDialog.Accepted:
            # Refresh component palette if import was successful
            if dialog.import_result and (dialog.import_result.parts_added > 0 or dialog.import_result.parts_updated > 0):
                self.component_palette.load_components()
                self.statusBar().showMessage(
                    f"Parts import complete: {dialog.import_result.parts_added} added, "
                    f"{dialog.import_result.parts_updated} updated"
                )
