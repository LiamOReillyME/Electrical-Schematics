"""Component palette widget for drag-and-drop component placement.

Modern UI with electrical schematic symbols following IEC/ANSI standards.
"""

import json
import re
from typing import Optional, List
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QPushButton, QLineEdit,
    QLabel, QMessageBox, QDialog, QFormLayout, QComboBox,
    QDialogButtonBox, QTextEdit, QFrame, QSizePolicy, QScrollArea,
    QListWidget, QListWidgetItem, QStackedWidget, QToolButton, QSpinBox
)
from PySide6.QtCore import Qt, Signal, QPoint, QMimeData, QSize, QByteArray
from PySide6.QtGui import QDrag, QPixmap, QPainter, QColor, QFont, QIcon, QPen, QBrush
from PySide6.QtSvg import QSvgRenderer

from electrical_schematics.database.manager import DatabaseManager, ComponentTemplate
from electrical_schematics.config.settings import get_settings
from electrical_schematics.api.digikey_proxy_client import get_digikey_client, DigiKeyProxyError
from electrical_schematics.gui.electrical_symbols import (
    get_component_symbol, ContactConfig, ContactType,
    create_relay_symbol, create_motor_symbol, create_sensor_symbol,
    create_power_supply_symbol, create_fuse_symbol, create_circuit_breaker_symbol,
    create_switch_symbol, create_emergency_stop_symbol, create_plc_io_symbol,
    create_indicator_light_symbol, COLORS as SYMBOL_COLORS
)
from electrical_schematics.gui.styles import COLORS


# Regex pattern to match internal E-codes (inventory codes, not manufacturer part numbers)
# Examples: E160970, E65138, E89520
_ECODE_PATTERN = re.compile(r'\bE\d{5,6}\b')


def strip_ecodes(text: str) -> str:
    """Remove internal E-codes from a text string.

    Strips patterns like E160970, E65138, E89520 from names and part numbers.

    Args:
        text: Input text possibly containing E-codes

    Returns:
        Cleaned text with E-codes removed and extra whitespace collapsed
    """
    if not text:
        return text
    cleaned = _ECODE_PATTERN.sub('', text)
    # Collapse multiple spaces and strip
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def clean_template_display(template: ComponentTemplate) -> ComponentTemplate:
    """Return a display-cleaned copy of a template with E-codes stripped.

    Does NOT modify the original template - only adjusts display fields.

    Args:
        template: Original component template

    Returns:
        Template with cleaned name and part_number for display purposes
    """
    # We modify the display name and part number only
    cleaned_name = strip_ecodes(template.name) if template.name else template.name
    cleaned_part = strip_ecodes(template.part_number) if template.part_number else template.part_number

    # If the entire name was an E-code, fall back to component type or original
    if not cleaned_name:
        cleaned_name = (template.component_type or "Component").replace('_', ' ').title()

    return ComponentTemplate(
        id=template.id,
        category=template.category,
        subcategory=template.subcategory,
        name=cleaned_name,
        designation_prefix=template.designation_prefix,
        component_type=template.component_type,
        default_voltage=template.default_voltage,
        description=strip_ecodes(template.description) if template.description else template.description,
        manufacturer=template.manufacturer,
        part_number=cleaned_part,
        datasheet_url=template.datasheet_url,
        image_path=template.image_path,
        symbol_svg=template.symbol_svg
    )


def svg_to_pixmap(svg_string: str, width: int = 80, height: int = 60) -> QPixmap:
    """Convert SVG string to QPixmap.

    Args:
        svg_string: SVG content as string
        width: Desired width
        height: Desired height

    Returns:
        QPixmap rendered from SVG
    """
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.transparent)

    svg_data = QByteArray(svg_string.encode('utf-8'))
    renderer = QSvgRenderer(svg_data)

    if renderer.isValid():
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        renderer.render(painter)
        painter.end()

    return pixmap


class DigiKeySearchDialog(QDialog):
    """Dialog for searching and importing components from DigiKey."""

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize DigiKey search dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Add Component from DigiKey")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        self.selected_part = None
        self.selected_category = None
        self.selected_subcategory = None
        self.selected_prefix = None
        self.selected_type = None

        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Search section
        search_frame = QFrame()
        search_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        search_layout = QHBoxLayout(search_frame)

        search_label = QLabel("Part Number:")
        search_label.setStyleSheet("font-weight: bold;")
        search_layout.addWidget(search_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Enter DigiKey or manufacturer part number")
        self.search_edit.returnPressed.connect(self._search_digikey)
        search_layout.addWidget(self.search_edit)

        self.search_btn = QPushButton("Search")
        self.search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
        """)
        self.search_btn.clicked.connect(self._search_digikey)
        search_layout.addWidget(self.search_btn)

        layout.addWidget(search_frame)

        # Results
        self.results_label = QLabel("Enter a part number and click Search")
        self.results_label.setWordWrap(True)
        self.results_label.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['surface_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 12px;
                color: {COLORS['text_secondary']};
            }}
        """)
        self.results_label.setMinimumHeight(100)
        layout.addWidget(self.results_label)

        # Category configuration
        form_frame = QFrame()
        form_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        form = QFormLayout(form_frame)
        form.setSpacing(8)

        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Contactors/Relays",
            "Sensors",
            "Motors",
            "Drives",
            "PLCs",
            "Power Supplies",
            "Protection"
        ])
        form.addRow("Category:", self.category_combo)

        self.subcategory_edit = QLineEdit()
        form.addRow("Subcategory:", self.subcategory_edit)

        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("e.g., K, S, M, B, F, U")
        form.addRow("Designation Prefix:", self.prefix_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "CONTACTOR", "RELAY", "PROXIMITY_SENSOR", "PHOTOELECTRIC_SENSOR",
            "LIMIT_SWITCH", "MOTOR", "VFD", "PLC_INPUT", "PLC_OUTPUT",
            "POWER_24VDC", "POWER_400VAC", "FUSE", "CIRCUIT_BREAKER"
        ])
        form.addRow("Component Type:", self.type_combo)

        layout.addWidget(form_frame)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _search_digikey(self):
        """Search DigiKey for part number via local proxy server."""
        part_number = self.search_edit.text().strip()

        if not part_number:
            self.results_label.setText("Please enter a part number")
            return

        self.results_label.setText(f"Starting proxy server and searching for {part_number}...")

        # Store selected values
        self.selected_part = part_number
        self.selected_category = self.category_combo.currentText()
        self.selected_subcategory = self.subcategory_edit.text()
        self.selected_prefix = self.prefix_edit.text()
        self.selected_type = self.type_combo.currentText()

        try:
            # Get proxy client (automatically starts server if needed)
            client = get_digikey_client()

            # Authenticate with DigiKey via proxy
            client.authenticate()

            # Search for product via proxy
            response = client.search_products(part_number, limit=5)

            if response.products:
                result_text = f"Found {response.products_count} results for '{part_number}':\n\n"

                for i, product in enumerate(response.products[:5], 1):
                    result_text += f"{i}. {product.manufacturer_part_number}\n"
                    result_text += f"   Manufacturer: {product.manufacturer}\n"
                    desc = product.description or ""
                    result_text += f"   {desc[:60]}{'...' if len(desc) > 60 else ''}\n"
                    if product.quantity_available:
                        result_text += f"   In Stock: {product.quantity_available}\n"
                    result_text += "\n"

                self.results_label.setText(result_text)
                self.results_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: {COLORS['surface']};
                        border: 1px solid {COLORS['success']};
                        border-radius: 6px;
                        padding: 12px;
                        color: {COLORS['text']};
                    }}
                """)

                # Auto-populate subcategory if available
                if response.products[0].family and not self.subcategory_edit.text():
                    self.subcategory_edit.setText(response.products[0].family)

            else:
                self.results_label.setText(
                    f"No products found for '{part_number}'.\n\n"
                    "Try a different part number or manufacturer name."
                )

        except DigiKeyProxyError as e:
            self.results_label.setText(
                f"DigiKey API Error:\n{str(e)}\n\n"
                "The local proxy server handles API requests.\n"
                "Check your network connection.\n"
                "You can still add this component manually."
            )
        except Exception as e:
            self.results_label.setText(
                f"Error:\n{str(e)}\n\n"
                "You can still add this component manually."
            )

    def get_result(self):
        """Get search result data.

        Returns:
            Dictionary with part info
        """
        return {
            'part_number': self.selected_part,
            'category': self.selected_category,
            'subcategory': self.selected_subcategory,
            'designation_prefix': self.selected_prefix,
            'component_type': self.selected_type
        }


class ContactConfigDialog(QDialog):
    """Dialog for configuring relay/contactor contacts."""

    def __init__(self, parent: Optional[QWidget] = None, existing_contacts: List[ContactConfig] = None):
        """Initialize contact configuration dialog.

        Args:
            parent: Parent widget
            existing_contacts: Existing contact configurations
        """
        super().__init__(parent)
        self.setWindowTitle("Configure Contacts")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        self.contacts = existing_contacts or []
        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Configure contact blocks for this relay/contactor")
        header.setStyleSheet(f"color: {COLORS['text_secondary']}; margin-bottom: 8px;")
        layout.addWidget(header)

        # Contact list
        self.contact_list = QListWidget()
        self._refresh_contact_list()
        layout.addWidget(self.contact_list)

        # Add contact form
        add_frame = QFrame()
        add_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        add_layout = QHBoxLayout(add_frame)

        add_layout.addWidget(QLabel("Terminal:"))
        self.terminal_from = QLineEdit()
        self.terminal_from.setPlaceholderText("13")
        self.terminal_from.setMaximumWidth(50)
        add_layout.addWidget(self.terminal_from)

        add_layout.addWidget(QLabel("-"))

        self.terminal_to = QLineEdit()
        self.terminal_to.setPlaceholderText("14")
        self.terminal_to.setMaximumWidth(50)
        add_layout.addWidget(self.terminal_to)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["NO", "NC"])
        add_layout.addWidget(self.type_combo)

        add_btn = QPushButton("Add")
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }}
        """)
        add_btn.clicked.connect(self._add_contact)
        add_layout.addWidget(add_btn)

        layout.addWidget(add_frame)

        # Remove button
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_contact)
        layout.addWidget(remove_btn)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _refresh_contact_list(self):
        """Refresh the contact list display."""
        self.contact_list.clear()
        for contact in self.contacts:
            type_str = "NO" if contact.contact_type == ContactType.NO else "NC"
            item_text = f"{contact.terminal_from}-{contact.terminal_to} ({type_str})"
            self.contact_list.addItem(item_text)

    def _add_contact(self):
        """Add a new contact."""
        from_term = self.terminal_from.text().strip()
        to_term = self.terminal_to.text().strip()

        if not from_term or not to_term:
            return

        contact_type = ContactType.NO if self.type_combo.currentText() == "NO" else ContactType.NC

        self.contacts.append(ContactConfig(
            terminal_from=from_term,
            terminal_to=to_term,
            contact_type=contact_type
        ))

        self._refresh_contact_list()

        # Clear inputs
        self.terminal_from.clear()
        self.terminal_to.clear()

    def _remove_contact(self):
        """Remove selected contact."""
        current_row = self.contact_list.currentRow()
        if current_row >= 0 and current_row < len(self.contacts):
            self.contacts.pop(current_row)
            self._refresh_contact_list()

    def get_contacts(self) -> List[ContactConfig]:
        """Get configured contacts."""
        return self.contacts


class LibraryComponentEditDialog(QDialog):
    """Dialog for editing a library component."""

    def __init__(self, parent: Optional[QWidget], template: ComponentTemplate, db_manager: DatabaseManager):
        """Initialize edit dialog.

        Args:
            parent: Parent widget
            template: Component template to edit
            db_manager: Database manager
        """
        super().__init__(parent)
        self.setWindowTitle(f"Edit Component: {template.name}")
        self.setMinimumWidth(550)
        self.setMinimumHeight(500)

        self.template = template
        self.db_manager = db_manager
        self.contacts: List[ContactConfig] = []

        self._init_ui()
        self._populate_fields()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Symbol preview
        preview_frame = QFrame()
        preview_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        preview_layout = QHBoxLayout(preview_frame)

        self.symbol_label = QLabel()
        self.symbol_label.setAlignment(Qt.AlignCenter)
        self.symbol_label.setMinimumSize(120, 80)
        preview_layout.addWidget(self.symbol_label)

        preview_info = QVBoxLayout()
        self.preview_name = QLabel()
        self.preview_name.setStyleSheet("font-weight: bold; font-size: 14px;")
        preview_info.addWidget(self.preview_name)

        self.preview_type = QLabel()
        self.preview_type.setStyleSheet(f"color: {COLORS['text_secondary']};")
        preview_info.addWidget(self.preview_type)

        preview_info.addStretch()
        preview_layout.addLayout(preview_info)
        preview_layout.addStretch()

        layout.addWidget(preview_frame)

        # Form
        form_frame = QFrame()
        form_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        form = QFormLayout(form_frame)
        form.setSpacing(8)

        # Name
        self.name_edit = QLineEdit()
        form.addRow("Name:", self.name_edit)

        # Category
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        categories = self.db_manager.get_categories() or [
            "Relays & Contactors", "Sensors", "Motors", "Drives",
            "Protection", "Control", "Power", "Other"
        ]
        self.category_combo.addItems(categories)
        form.addRow("Category:", self.category_combo)

        # Subcategory
        self.subcategory_edit = QLineEdit()
        form.addRow("Subcategory:", self.subcategory_edit)

        # Component Type
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "contactor", "relay", "proximity_sensor", "photoelectric_sensor",
            "limit_switch", "pressure_switch", "push_button", "emergency_stop",
            "motor", "vfd", "indicator_light", "solenoid_valve", "buzzer",
            "plc_input", "plc_output", "timer", "counter",
            "fuse", "circuit_breaker", "terminal_block", "connector",
            "power_24vdc", "power_400vac", "power_230vac", "ground", "other"
        ])
        self.type_combo.currentTextChanged.connect(self._update_preview)
        form.addRow("Component Type:", self.type_combo)

        # Designation Prefix
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("e.g., K, S, M, B, F, U")
        self.prefix_edit.textChanged.connect(self._update_preview)
        form.addRow("Designation Prefix:", self.prefix_edit)

        # Voltage
        self.voltage_edit = QLineEdit()
        self.voltage_edit.setPlaceholderText("e.g., 24VDC, 230VAC")
        form.addRow("Default Voltage:", self.voltage_edit)

        # Description
        self.description_edit = QLineEdit()
        form.addRow("Description:", self.description_edit)

        # Manufacturer
        self.manufacturer_edit = QLineEdit()
        form.addRow("Manufacturer:", self.manufacturer_edit)

        # Part Number
        self.part_number_edit = QLineEdit()
        form.addRow("Part Number:", self.part_number_edit)

        # Datasheet URL
        self.datasheet_edit = QLineEdit()
        self.datasheet_edit.setPlaceholderText("https://...")
        form.addRow("Datasheet URL:", self.datasheet_edit)

        layout.addWidget(form_frame)

        # Contact configuration button (for relays/contactors)
        self.contacts_btn = QPushButton("Configure Contacts...")
        self.contacts_btn.clicked.connect(self._configure_contacts)
        self.contacts_btn.setVisible(False)  # Show only for relay/contactor types
        layout.addWidget(self.contacts_btn)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # Add Delete button
        delete_btn = buttons.addButton("Delete", QDialogButtonBox.DestructiveRole)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
            }}
        """)
        delete_btn.clicked.connect(self._delete_component)

        layout.addWidget(buttons)

    def _populate_fields(self):
        """Populate fields with template data."""
        self.name_edit.setText(self.template.name or "")
        self.subcategory_edit.setText(self.template.subcategory or "")
        self.prefix_edit.setText(self.template.designation_prefix or "")
        self.voltage_edit.setText(self.template.default_voltage or "")
        self.description_edit.setText(self.template.description or "")
        self.manufacturer_edit.setText(self.template.manufacturer or "")
        self.part_number_edit.setText(self.template.part_number or "")
        self.datasheet_edit.setText(self.template.datasheet_url or "")

        # Set category
        if self.template.category:
            idx = self.category_combo.findText(self.template.category)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
            else:
                self.category_combo.setEditText(self.template.category)

        # Set component type
        if self.template.component_type:
            idx = self.type_combo.findText(self.template.component_type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)

        self._update_preview()

    def _update_preview(self):
        """Update the symbol preview."""
        comp_type = self.type_combo.currentText()
        prefix = self.prefix_edit.text() or "X"
        designation = f"{prefix}1"

        # Show/hide contacts button
        self.contacts_btn.setVisible(comp_type in ['relay', 'contactor'])

        # Generate SVG symbol
        try:
            svg = get_component_symbol(
                comp_type,
                designation=designation,
                contacts=self.contacts if self.contacts else None
            )
            pixmap = svg_to_pixmap(svg, 120, 80)
            self.symbol_label.setPixmap(pixmap)
        except Exception as e:
            self.symbol_label.setText("Preview\nUnavailable")

        self.preview_name.setText(self.name_edit.text() or "Component")
        self.preview_type.setText(comp_type.replace('_', ' ').title())

    def _configure_contacts(self):
        """Open contact configuration dialog."""
        dialog = ContactConfigDialog(self, self.contacts)
        if dialog.exec() == QDialog.Accepted:
            self.contacts = dialog.get_contacts()
            self._update_preview()

    def get_updated_template(self) -> ComponentTemplate:
        """Get updated template from form fields.

        Returns:
            Updated ComponentTemplate
        """
        return ComponentTemplate(
            id=self.template.id,
            category=self.category_combo.currentText(),
            subcategory=self.subcategory_edit.text() or None,
            name=self.name_edit.text(),
            designation_prefix=self.prefix_edit.text() or None,
            component_type=self.type_combo.currentText(),
            default_voltage=self.voltage_edit.text() or None,
            description=self.description_edit.text() or None,
            manufacturer=self.manufacturer_edit.text() or None,
            part_number=self.part_number_edit.text() or None,
            datasheet_url=self.datasheet_edit.text() or None,
            image_path=self.template.image_path,
            symbol_svg=self.template.symbol_svg
        )

    def _delete_component(self):
        """Delete the component from library."""
        reply = QMessageBox.question(
            self,
            "Delete Component",
            f"Are you sure you want to delete '{self.template.name}' from the library?\n\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.db_manager.delete_template(self.template.id)
            self.reject()  # Close dialog without saving


class ComponentCard(QFrame):
    """Modern card widget for displaying a component with its symbol."""

    clicked = Signal(object)  # ComponentTemplate
    double_clicked = Signal(object)  # ComponentTemplate

    def __init__(self, template: ComponentTemplate, parent: Optional[QWidget] = None):
        """Initialize component card.

        Args:
            template: Component template
            parent: Parent widget
        """
        super().__init__(parent)
        self.template = template
        self._display = clean_template_display(template)
        self._selected = False

        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        self.setFixedSize(160, 100)
        self.setCursor(Qt.OpenHandCursor)
        self._update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Symbol
        self.symbol_label = QLabel()
        self.symbol_label.setAlignment(Qt.AlignCenter)
        self.symbol_label.setFixedHeight(50)

        # Generate symbol
        try:
            svg = get_component_symbol(
                self.template.component_type or 'other',
                designation=self.template.designation_prefix or 'X'
            )
            pixmap = svg_to_pixmap(svg, 70, 45)
            self.symbol_label.setPixmap(pixmap)
        except Exception:
            self.symbol_label.setText(self.template.designation_prefix or "?")

        layout.addWidget(self.symbol_label)

        # Name (truncated, E-codes stripped)
        display_name = self._display.name
        name_label = QLabel(display_name[:18] + "..." if len(display_name) > 18 else display_name)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet(f"font-size: 11px; color: {COLORS['text']};")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        # Voltage badge
        if self.template.default_voltage:
            voltage_label = QLabel(self.template.default_voltage)
            voltage_label.setAlignment(Qt.AlignCenter)
            voltage_label.setStyleSheet(f"""
                font-size: 9px;
                color: white;
                background-color: {COLORS['accent']};
                border-radius: 3px;
                padding: 2px 4px;
            """)
            voltage_label.setFixedHeight(16)
            layout.addWidget(voltage_label, alignment=Qt.AlignCenter)

        # Tooltip
        tooltip = f"{self._display.name}"
        if self._display.description:
            tooltip += f"\n{self._display.description}"
        if self.template.manufacturer:
            tooltip += f"\nManufacturer: {self.template.manufacturer}"
        self.setToolTip(tooltip)

    def _update_style(self):
        """Update card styling."""
        if self._selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['accent']};
                    border: 2px solid {COLORS['accent_hover']};
                    border-radius: 8px;
                }}
                QLabel {{
                    color: white;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['surface']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                }}
                QFrame:hover {{
                    background-color: {COLORS['surface_dark']};
                    border-color: {COLORS['accent']};
                }}
            """)

    def set_selected(self, selected: bool):
        """Set selection state."""
        self._selected = selected
        self._update_style()

    def mousePressEvent(self, event):
        """Handle mouse press."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.template)

    def mouseDoubleClickEvent(self, event):
        """Handle double-click."""
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.template)

    def mouseMoveEvent(self, event):
        """Handle mouse move for drag-and-drop."""
        if not (event.buttons() & Qt.LeftButton):
            return

        # Create drag operation
        drag = QDrag(self)
        mime_data = QMimeData()

        # Encode component template as JSON
        component_data = {
            'library_id': self.template.id,
            'type': self.template.component_type,
            'designation_prefix': self.template.designation_prefix,
            'voltage': self.template.default_voltage,
            'name': self._display.name,
            'description': self._display.description,
            'manufacturer': self.template.manufacturer,
            'part_number': self._display.part_number
        }

        mime_data.setData(
            'application/x-component-template',
            json.dumps(component_data).encode('utf-8')
        )

        # Create drag pixmap with electrical symbol
        pixmap = self._create_drag_pixmap()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        drag.setMimeData(mime_data)
        drag.exec_(Qt.CopyAction)

    def _create_drag_pixmap(self) -> QPixmap:
        """Create pixmap for drag cursor with electrical symbol.

        Returns:
            Pixmap for drag cursor
        """
        width, height = 120, 80
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(255, 255, 255, 230))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw border
        painter.setPen(QPen(QColor(COLORS['accent']), 2))
        painter.drawRoundedRect(1, 1, width - 2, height - 2, 8, 8)

        # Draw symbol
        try:
            svg = get_component_symbol(
                self.template.component_type or 'other',
                designation=self.template.designation_prefix or 'X'
            )
            svg_pixmap = svg_to_pixmap(svg, 80, 50)
            painter.drawPixmap((width - 80) // 2, 5, svg_pixmap)
        except Exception:
            painter.drawText(10, 35, self.template.designation_prefix or "?")

        # Draw name (E-codes stripped)
        painter.setPen(QColor(COLORS['text']))
        painter.setFont(QFont("Arial", 9))
        name = self._display.name
        name = name[:15] + "..." if len(name) > 15 else name
        painter.drawText(pixmap.rect().adjusted(5, 55, -5, -5), Qt.AlignCenter, name)

        painter.end()
        return pixmap


class ComponentListItem(QTreeWidgetItem):
    """Tree widget item representing a component template."""

    def __init__(self, template: ComponentTemplate, parent: Optional[QTreeWidgetItem] = None):
        """Initialize component list item.

        Args:
            template: Component template
            parent: Parent tree item
        """
        super().__init__(parent)
        self.template = template
        self._display = clean_template_display(template)
        self.setText(0, self._display.name)
        tooltip = self._display.name
        if self._display.description:
            tooltip += f"\n{self._display.description}"
        if self.template.default_voltage:
            tooltip += f"\nVoltage: {self.template.default_voltage}"
        self.setToolTip(0, tooltip)


class ComponentTreeWidget(QTreeWidget):
    """Tree widget with drag support for component templates."""

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize component tree widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setHeaderLabel("Component Library")
        self.setDragEnabled(True)
        self.setAnimated(True)
        self.setIndentation(20)
        self.setRootIsDecorated(True)
        self.drag_start_position = None

    def mousePressEvent(self, event):
        """Handle mouse press event.

        Args:
            event: Mouse event
        """
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move event for drag-and-drop.

        Args:
            event: Mouse event
        """
        if not (event.buttons() & Qt.LeftButton):
            return

        if not self.drag_start_position:
            return

        # Check if drag distance is sufficient
        if (event.pos() - self.drag_start_position).manhattanLength() < 10:
            return

        # Get current item
        current = self.currentItem()
        if not isinstance(current, ComponentListItem):
            return

        # Create drag operation
        drag = QDrag(self)
        mime_data = QMimeData()

        # Encode component template as JSON
        template = current.template
        display = current._display
        component_data = {
            'library_id': template.id,
            'type': template.component_type,
            'designation_prefix': template.designation_prefix,
            'voltage': template.default_voltage,
            'name': display.name,
            'description': display.description,
            'manufacturer': template.manufacturer,
            'part_number': display.part_number
        }

        mime_data.setData(
            'application/x-component-template',
            json.dumps(component_data).encode('utf-8')
        )

        # Create drag pixmap with symbol
        pixmap = self._create_drag_pixmap(template)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        drag.setMimeData(mime_data)
        drag.exec_(Qt.CopyAction)

    def _create_drag_pixmap(self, template: ComponentTemplate) -> QPixmap:
        """Create pixmap for drag cursor with electrical symbol.

        Args:
            template: Component template

        Returns:
            Pixmap for drag cursor
        """
        display = clean_template_display(template)
        width, height = 120, 80
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(255, 255, 255, 230))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw border
        painter.setPen(QPen(QColor(COLORS['accent']), 2))
        painter.drawRoundedRect(1, 1, width - 2, height - 2, 8, 8)

        # Draw symbol
        try:
            svg = get_component_symbol(
                template.component_type or 'other',
                designation=template.designation_prefix or 'X'
            )
            svg_pixmap = svg_to_pixmap(svg, 80, 50)
            painter.drawPixmap((width - 80) // 2, 5, svg_pixmap)
        except Exception:
            painter.drawText(10, 35, template.designation_prefix or "?")

        # Draw name (E-codes stripped)
        painter.setPen(QColor(COLORS['text']))
        painter.setFont(QFont("Arial", 9))
        name = display.name[:15] + "..." if len(display.name) > 15 else display.name
        painter.drawText(pixmap.rect().adjusted(5, 55, -5, -5), Qt.AlignCenter, name)

        painter.end()
        return pixmap


class ComponentPalette(QDockWidget):
    """Dockable widget showing component library for drag-and-drop.

    Modern design with electrical schematic symbols.
    """

    # Signals
    component_added = Signal(int)  # component_library_id

    def __init__(self, db_manager: DatabaseManager, parent: Optional[QWidget] = None):
        """Initialize component palette.

        Args:
            db_manager: Database manager
            parent: Parent widget
        """
        super().__init__("Component Library", parent)
        self.db_manager = db_manager
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setMinimumWidth(200)

        # Remove the title bar extra space - use a flat title bar widget
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(8, 2, 8, 2)
        title_label = QLabel("Component Library")
        title_label.setStyleSheet(f"""
            font-weight: bold;
            font-size: 13px;
            color: white;
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_widget.setStyleSheet(f"background-color: {COLORS['primary']};")
        title_widget.setFixedHeight(28)
        self.setTitleBarWidget(title_widget)

        self.view_mode = "grid"  # "grid" or "tree"
        self.selected_card: Optional[ComponentCard] = None
        self.component_cards: List[ComponentCard] = []

        self._init_ui()
        self._populate_components()

    def _init_ui(self):
        """Initialize UI."""
        # Main widget
        widget = QWidget()
        widget.setStyleSheet(f"background-color: {COLORS['background']};")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Search bar
        search_frame = QFrame()
        search_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(8, 4, 8, 4)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search components...")
        self.search_edit.setStyleSheet("border: none; background: transparent;")
        self.search_edit.textChanged.connect(self._filter_components)
        search_layout.addWidget(self.search_edit)

        # View toggle buttons
        self.grid_btn = QToolButton()
        self.grid_btn.setText("Grid")
        self.grid_btn.setCheckable(True)
        self.grid_btn.setChecked(True)
        self.grid_btn.clicked.connect(lambda: self._set_view_mode("grid"))
        search_layout.addWidget(self.grid_btn)

        self.tree_btn = QToolButton()
        self.tree_btn.setText("List")
        self.tree_btn.setCheckable(True)
        self.tree_btn.clicked.connect(lambda: self._set_view_mode("tree"))
        search_layout.addWidget(self.tree_btn)

        layout.addWidget(search_frame)

        # Category filter
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories")
        self.category_combo.currentTextChanged.connect(self._filter_components)
        layout.addWidget(self.category_combo)

        # Stacked widget for view modes
        self.view_stack = QStackedWidget()

        # Grid view
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.grid_scroll.setStyleSheet("border: none;")

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(8)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.grid_scroll.setWidget(self.grid_widget)

        self.view_stack.addWidget(self.grid_scroll)

        # Tree view - standard tree with +/- expand/collapse
        self.tree = ComponentTreeWidget()
        self.tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                font-size: 13px;
                outline: none;
            }}
            QTreeWidget::item {{
                padding: 4px 4px;
                border-radius: 3px;
            }}
            QTreeWidget::item:hover {{
                background-color: {COLORS['surface_dark']};
            }}
            QTreeWidget::item:selected {{
                background-color: {COLORS['accent']};
                color: white;
            }}
            QTreeWidget::branch {{
                background-color: transparent;
            }}
            QTreeWidget::branch:has-siblings:!adjoins-item {{
                border-image: none;
            }}
            QTreeWidget::branch:has-siblings:adjoins-item {{
                border-image: none;
            }}
            QTreeWidget::branch:!has-children:!has-siblings:adjoins-item {{
                border-image: none;
            }}
        """)
        self.view_stack.addWidget(self.tree)

        layout.addWidget(self.view_stack)

        # Action buttons
        button_layout = QHBoxLayout()

        self.add_digikey_btn = QPushButton("+ DigiKey")
        self.add_digikey_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_light']};
            }}
        """)
        self.add_digikey_btn.clicked.connect(self._add_from_digikey)
        button_layout.addWidget(self.add_digikey_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
        """)
        self.refresh_btn.clicked.connect(self.load_components)
        button_layout.addWidget(self.refresh_btn)

        layout.addLayout(button_layout)

        # Usage hint
        hint = QLabel("Drag components to the PDF to place them")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; padding: 4px;")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        self.setWidget(widget)

    def _set_view_mode(self, mode: str):
        """Set the view mode.

        Args:
            mode: "grid" or "tree"
        """
        self.view_mode = mode
        self.grid_btn.setChecked(mode == "grid")
        self.tree_btn.setChecked(mode == "tree")

        if mode == "grid":
            self.view_stack.setCurrentIndex(0)
        else:
            self.view_stack.setCurrentIndex(1)

    def _populate_components(self):
        """Populate components in both views."""
        self.load_components()

    def load_components(self):
        """Load/reload components from database."""
        # Clear existing
        self.component_cards.clear()

        # Clear grid layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear tree
        self.tree.clear()

        # Update category filter
        categories = self.db_manager.get_categories()
        self.category_combo.clear()
        self.category_combo.addItem("All Categories")
        self.category_combo.addItems(categories)

        # Get all templates
        templates = self.db_manager.get_component_templates()

        # Populate grid view
        row, col = 0, 0
        cols = 2  # Number of columns

        for template in templates:
            card = ComponentCard(template)
            card.clicked.connect(self._on_card_clicked)
            card.double_clicked.connect(self._on_card_double_clicked)
            self.component_cards.append(card)
            self.grid_layout.addWidget(card, row, col)

            col += 1
            if col >= cols:
                col = 0
                row += 1

        # Populate tree view - nested by category > subcategory > components
        for category in categories:
            category_item = QTreeWidgetItem(self.tree)
            category_item.setText(0, category)
            category_item.setExpanded(False)
            # Bold font for category items
            font = category_item.font(0)
            font.setBold(True)
            category_item.setFont(0, font)

            cat_templates = self.db_manager.get_component_templates(category)

            # Group by subcategory
            subcategories = {}
            for template in cat_templates:
                subcat = template.subcategory or "General"
                if subcat not in subcategories:
                    subcategories[subcat] = []
                subcategories[subcat].append(template)

            for subcat, subcat_templates in sorted(subcategories.items()):
                if len(subcategories) > 1:
                    subcat_item = QTreeWidgetItem(category_item)
                    subcat_item.setText(0, subcat)
                    subcat_item.setExpanded(False)
                    # Italic font for subcategory
                    sfont = subcat_item.font(0)
                    sfont.setItalic(True)
                    subcat_item.setFont(0, sfont)
                    parent_item = subcat_item
                else:
                    parent_item = category_item

                for template in sorted(subcat_templates, key=lambda t: t.name):
                    ComponentListItem(template, parent_item)

    def _filter_components(self):
        """Filter components based on search and category."""
        query = self.search_edit.text().lower()
        category = self.category_combo.currentText()
        has_filter = bool(query) or category != "All Categories"

        # Filter grid view
        for card in self.component_cards:
            template = card.template

            # Category filter
            if category != "All Categories" and template.category != category:
                card.hide()
                continue

            # Search filter
            if query:
                matches = (
                    query in template.name.lower() or
                    (template.description and query in template.description.lower()) or
                    (template.manufacturer and query in template.manufacturer.lower()) or
                    (template.part_number and query in template.part_number.lower())
                )
                card.setVisible(matches)
            else:
                card.show()

        # Filter tree view
        if not has_filter:
            # No filter active - show everything, collapse to default state
            iterator = QTreeWidgetItemIterator(self.tree)
            while iterator.value():
                item = iterator.value()
                item.setHidden(False)
                iterator += 1
            return

        # Filter is active - first hide all parent nodes, then show matching leaves
        # and reveal their parents
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            if isinstance(item, ComponentListItem):
                template = item.template

                # Category filter
                if category != "All Categories" and template.category != category:
                    item.setHidden(True)
                elif query:
                    matches = (
                        query in template.name.lower() or
                        (template.description and query in template.description.lower()) or
                        (template.manufacturer and query in template.manufacturer.lower()) or
                        (template.part_number and query in template.part_number.lower())
                    )
                    item.setHidden(not matches)
                else:
                    item.setHidden(False)
            else:
                # Category/subcategory nodes - hide initially, will be shown
                # if any child matches
                item.setHidden(True)

            iterator += 1

        # Second pass: show parents of visible leaf items
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            if isinstance(item, ComponentListItem) and not item.isHidden():
                parent = item.parent()
                while parent:
                    parent.setHidden(False)
                    parent.setExpanded(True)
                    parent = parent.parent()
            iterator += 1

    def _on_card_clicked(self, template: ComponentTemplate):
        """Handle card click for selection.

        Args:
            template: Clicked component template
        """
        # Deselect previous
        if self.selected_card:
            self.selected_card.set_selected(False)

        # Find and select new card
        for card in self.component_cards:
            if card.template.id == template.id:
                card.set_selected(True)
                self.selected_card = card
                break

    def _on_card_double_clicked(self, template: ComponentTemplate):
        """Handle card double-click for editing.

        Args:
            template: Double-clicked component template
        """
        self._edit_library_component(template)

    def _on_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle tree item double-click.

        Args:
            item: Clicked item
            column: Column index
        """
        if isinstance(item, ComponentListItem):
            self._edit_library_component(item.template)

    def _edit_library_component(self, template: ComponentTemplate):
        """Open dialog to edit a library component.

        Args:
            template: Component template to edit
        """
        dialog = LibraryComponentEditDialog(self, template, self.db_manager)

        if dialog.exec() == QDialog.Accepted:
            updated_template = dialog.get_updated_template()
            self.db_manager.update_template(template.id, updated_template)
            self.load_components()

    def _add_from_digikey(self):
        """Open DigiKey search dialog to add component."""
        dialog = DigiKeySearchDialog(self)

        if dialog.exec() == QDialog.Accepted:
            result = dialog.get_result()

            if result['part_number']:
                try:
                    name = f"DigiKey {result['part_number']}"
                    description = f"Imported from DigiKey: {result['part_number']}"
                    manufacturer = None
                    datasheet_url = None
                    default_voltage = None

                    try:
                        client = get_digikey_client()
                        client.authenticate()
                        details = client.get_product_details(result['part_number'])

                        if details:
                            name = details.description or name
                            manufacturer = details.manufacturer
                            description = details.detailed_description or description
                            datasheet_url = details.primary_datasheet

                            if details.parameters:
                                for key, value in details.parameters.items():
                                    if 'voltage' in key.lower():
                                        default_voltage = value
                                        break

                    except Exception as api_error:
                        print(f"DigiKey API lookup failed: {api_error}")

                    template = ComponentTemplate(
                        id=None,
                        category=result['category'],
                        subcategory=result['subcategory'],
                        name=name,
                        designation_prefix=result['designation_prefix'],
                        component_type=result['component_type'],
                        default_voltage=default_voltage,
                        description=description,
                        manufacturer=manufacturer,
                        part_number=result['part_number'],
                        datasheet_url=datasheet_url,
                        image_path=None,
                        symbol_svg=None
                    )

                    component_id = self.db_manager.add_component_template(template)

                    QMessageBox.information(
                        self,
                        "Success",
                        f"Component '{name}' added to library!\n"
                        f"Part Number: {result['part_number']}"
                    )

                    self.load_components()
                    self.component_added.emit(component_id)

                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Failed to add component: {e}"
                    )

    def get_selected_template(self) -> Optional[ComponentTemplate]:
        """Get currently selected component template.

        Returns:
            Selected template or None
        """
        if self.view_mode == "grid" and self.selected_card:
            return self.selected_card.template

        if self.view_mode == "tree":
            current = self.tree.currentItem()
            if isinstance(current, ComponentListItem):
                return current.template

        return None
