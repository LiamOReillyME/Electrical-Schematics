"""Interactive simulation control panel."""

from typing import Optional, List, Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QLabel, QTextEdit, QGroupBox, QComboBox,
    QListWidgetItem, QCheckBox, QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont, QAction

from electrical_schematics.models import WiringDiagram, SensorState
from electrical_schematics.simulation.interactive_simulator import InteractiveSimulator


# Component type icons (using Unicode symbols for cross-platform support)
COMPONENT_ICONS = {
    'power_24vdc': '+',      # Power source
    'power_400vac': '~',     # AC power
    'power_230vac': '~',     # AC power
    'ground': '-',           # Ground
    'proximity_sensor': 'P', # Proximity
    'photoelectric_sensor': 'E', # Eye/Photo
    'limit_switch': 'L',     # Limit
    'pressure_switch': 'S',  # Switch
    'temperature_sensor': 'T', # Temperature
    'push_button': 'B',      # Button
    'emergency_stop': '!',   # Emergency
    'relay': 'K',            # Relay (German: Kontakt)
    'contactor': 'K',        # Contactor
    'solenoid_valve': 'V',   # Valve
    'motor': 'M',            # Motor
    'indicator_light': '*',  # Light
    'buzzer': '#',           # Sound
    'plc_input': 'I',        # Input
    'plc_output': 'O',       # Output
    'plc_input_state': 'I',  # Input state
    'timer': 'T',            # Timer
    'counter': 'C',          # Counter
    'fuse': 'F',             # Fuse
    'circuit_breaker': 'F',  # Breaker
    'terminal_block': 'X',   # Terminal
    'connector': 'X',        # Connector
    'other': '?',            # Unknown
}


class InteractivePanel(QWidget):
    """Panel for interactive simulation controls."""

    # Signals
    component_toggled = Signal(str)  # designation
    simulation_updated = Signal()
    go_to_page = Signal(int)  # page number (0-indexed)
    component_selected = Signal(str)  # component id

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the panel."""
        super().__init__(parent)

        self.diagram: Optional[WiringDiagram] = None
        self.simulator: Optional[InteractiveSimulator] = None
        self.current_page: Optional[int] = None
        self.filter_current_page_only = False

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout(self)

        # Component list
        comp_group = QGroupBox("Components")
        comp_layout = QVBoxLayout(comp_group)

        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All",
            "Contactors/Relays",
            "Sensors/Switches",
            "Fuses/Breakers",
            "Power Sources",
            "Motors/Loads"
        ])
        self.filter_combo.currentTextChanged.connect(self._refresh_component_list)
        filter_layout.addWidget(self.filter_combo)
        comp_layout.addLayout(filter_layout)

        # Page filter checkbox
        page_filter_layout = QHBoxLayout()
        self.page_filter_check = QCheckBox("Current page only")
        self.page_filter_check.setToolTip("Show only components on the currently displayed page")
        self.page_filter_check.stateChanged.connect(self._on_page_filter_changed)
        page_filter_layout.addWidget(self.page_filter_check)

        # Page indicator label
        self.page_count_label = QLabel("")
        self.page_count_label.setStyleSheet("color: #7F8C8D; font-size: 11px;")
        page_filter_layout.addWidget(self.page_count_label)
        page_filter_layout.addStretch()
        comp_layout.addLayout(page_filter_layout)

        # Help hint
        hint_label = QLabel("Double-click to toggle | Right-click for options")
        hint_label.setStyleSheet("color: #7F8C8D; font-size: 11px; font-style: italic;")
        comp_layout.addWidget(hint_label)

        # Component list
        self.component_list = QListWidget()
        self.component_list.setAlternatingRowColors(False)  # We use custom colors
        self.component_list.itemClicked.connect(self._on_component_selected)
        self.component_list.itemDoubleClicked.connect(self._on_component_double_clicked)
        self.component_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.component_list.customContextMenuRequested.connect(self._show_context_menu)
        # Add tooltip
        self.component_list.setToolTip("Click to select, double-click to toggle state")
        # Use monospace font for alignment
        font = QFont("Consolas, Monaco, monospace")
        font.setPointSize(10)
        self.component_list.setFont(font)
        comp_layout.addWidget(self.component_list)

        layout.addWidget(comp_group)

        # Actions
        action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout(action_group)

        self.toggle_btn = QPushButton("Toggle Selected Component")
        self.toggle_btn.setToolTip("Toggle the energization state of the selected component (shortcut: double-click)")
        self.toggle_btn.clicked.connect(self._toggle_selected)
        self.toggle_btn.setEnabled(False)
        action_layout.addWidget(self.toggle_btn)

        self.trace_btn = QPushButton("Trace Circuit Path")
        self.trace_btn.setToolTip("Show the circuit path and explain why the component is energized or de-energized")
        self.trace_btn.clicked.connect(self._trace_selected)
        self.trace_btn.setEnabled(False)
        action_layout.addWidget(self.trace_btn)

        self.goto_btn = QPushButton("Go to Component Page")
        self.goto_btn.setToolTip("Navigate to the PDF page where this component is located")
        self.goto_btn.clicked.connect(self._goto_selected_page)
        self.goto_btn.setEnabled(False)
        action_layout.addWidget(self.goto_btn)

        self.simulate_btn = QPushButton("Run Simulation")
        self.simulate_btn.setToolTip("Re-run the voltage flow simulation with current component states")
        self.simulate_btn.clicked.connect(self._run_simulation)
        action_layout.addWidget(self.simulate_btn)

        layout.addWidget(action_group)

        # Details
        detail_group = QGroupBox("Component Details")
        detail_layout = QVBoxLayout(detail_group)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(200)
        self.detail_text.setPlaceholderText("Select a component to view details...")
        detail_layout.addWidget(self.detail_text)

        layout.addWidget(detail_group)

    def set_diagram(self, diagram: Optional[WiringDiagram]) -> None:
        """Set the wiring diagram.

        Args:
            diagram: Wiring diagram (can be None to clear)
        """
        self.diagram = diagram
        if diagram:
            self.simulator = InteractiveSimulator(diagram)
            self._refresh_component_list()
            # Run initial simulation
            self._run_simulation()
        else:
            self.simulator = None
            self.component_list.clear()
            self.detail_text.clear()
            self.toggle_btn.setEnabled(False)
            self.trace_btn.setEnabled(False)
            self.goto_btn.setEnabled(False)
            self.page_count_label.setText("")

    def set_current_page(self, page: int) -> None:
        """Set the current PDF page for filtering.

        Args:
            page: Current page number (0-indexed)
        """
        self.current_page = page
        self._update_page_count_label()
        if self.filter_current_page_only:
            self._refresh_component_list()

    def _on_page_filter_changed(self, state: int) -> None:
        """Handle page filter checkbox change."""
        self.filter_current_page_only = (state == Qt.Checked)
        self._refresh_component_list()

    def _update_page_count_label(self) -> None:
        """Update the page component count label."""
        if not self.diagram or self.current_page is None:
            self.page_count_label.setText("")
            return

        # Count components on current page
        count = sum(1 for c in self.diagram.components if c.page == self.current_page)
        total = len(self.diagram.components)

        if count > 0:
            self.page_count_label.setText(f"Page {self.current_page + 1}: {count} of {total} components")
        else:
            self.page_count_label.setText(f"Page {self.current_page + 1}: No components")

    def _get_page_counts(self) -> Dict[int, int]:
        """Get component count per page.

        Returns:
            Dict mapping page number to component count
        """
        if not self.diagram:
            return {}

        counts: Dict[int, int] = {}
        for comp in self.diagram.components:
            page = comp.page
            counts[page] = counts.get(page, 0) + 1
        return counts

    def _refresh_component_list(self) -> None:
        """Refresh the component list based on filter."""
        if not self.diagram:
            return

        # Remember current selection
        current_item = self.component_list.currentItem()
        current_designation = current_item.data(Qt.UserRole) if current_item else None

        self.component_list.clear()

        filter_text = self.filter_combo.currentText()

        # Get all components, applying filters
        components = []
        for component in self.diagram.components:
            # Apply type filter
            if filter_text == "Contactors/Relays":
                if component.type.value not in ["contactor", "relay"]:
                    continue
            elif filter_text == "Sensors/Switches":
                if not component.is_sensor():
                    continue
            elif filter_text == "Fuses/Breakers":
                if component.type.value not in ["fuse", "circuit_breaker"]:
                    continue
            elif filter_text == "Power Sources":
                if not component.is_power_source():
                    continue
            elif filter_text == "Motors/Loads":
                if component.type.value != "motor":
                    continue

            # Apply page filter
            if self.filter_current_page_only and self.current_page is not None:
                if component.page != self.current_page:
                    continue

            components.append(component)

        # Sort by designation
        components.sort(key=lambda c: c.designation)

        for component in components:
            # Get icon for component type
            icon = COMPONENT_ICONS.get(component.type.value, '?')

            # Format: [Icon] Designation | Page | Voltage | Type
            page_display = f"P{component.page + 1:2d}"
            voltage_rating = component.voltage_rating or "---"
            type_short = component.type.value[:12]

            # Clean description for display
            desc = component.get_display_description(30)

            item_text = f"{icon} {component.designation:10s} {page_display} {voltage_rating:8s} {desc}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, component.designation)
            item.setData(Qt.UserRole + 1, component.id)  # Store ID for selection signal

            # Color code by state with proper contrast
            if self.simulator:
                node = self.simulator.voltage_nodes.get(component.id)
                if node and node.is_energized:
                    # Energized: Green background with dark text
                    item.setBackground(QBrush(QColor(200, 255, 200)))  # Light green
                    item.setForeground(QBrush(QColor(0, 80, 0)))  # Dark green text
                else:
                    # De-energized: Red background with dark text
                    item.setBackground(QBrush(QColor(255, 200, 200)))  # Light red
                    item.setForeground(QBrush(QColor(120, 0, 0)))  # Dark red text

            # Highlight if on current page
            if self.current_page is not None and component.page == self.current_page:
                # Add a subtle indicator for current page components
                font = item.font()
                font.setBold(True)
                item.setFont(font)

            # Add tooltip with more details
            tooltip = f"{component.designation}: {component.type.value}"
            if component.description:
                tooltip += f"\n{component.description}"
            tooltip += f"\nVoltage: {voltage_rating}"
            tooltip += f"\nPage: {component.page + 1}"
            if self.simulator:
                node = self.simulator.voltage_nodes.get(component.id)
                state = "ENERGIZED" if node and node.is_energized else "DE-ENERGIZED"
                tooltip += f"\nState: {state}"
            item.setToolTip(tooltip)

            self.component_list.addItem(item)

            # Restore selection
            if current_designation and component.designation == current_designation:
                item.setSelected(True)
                self.component_list.setCurrentItem(item)

        # Update page count label
        self._update_page_count_label()

    def _show_context_menu(self, position) -> None:
        """Show context menu for component list.

        Args:
            position: Click position
        """
        item = self.component_list.itemAt(position)
        if not item:
            return

        menu = QMenu(self)

        # Toggle action
        toggle_action = QAction("Toggle State", self)
        toggle_action.triggered.connect(self._toggle_selected)
        menu.addAction(toggle_action)

        # Trace action
        trace_action = QAction("Trace Circuit", self)
        trace_action.triggered.connect(self._trace_selected)
        menu.addAction(trace_action)

        menu.addSeparator()

        # Go to page action
        designation = item.data(Qt.UserRole)
        if self.diagram:
            component = self.diagram.get_component_by_designation(designation)
            if component:
                goto_action = QAction(f"Go to Page {component.page + 1}", self)
                goto_action.triggered.connect(lambda: self.go_to_page.emit(component.page))
                menu.addAction(goto_action)

        menu.exec(self.component_list.mapToGlobal(position))

    def _on_component_selected(self, item: QListWidgetItem) -> None:
        """Handle component selection.

        Args:
            item: Selected list item
        """
        self.toggle_btn.setEnabled(True)
        self.trace_btn.setEnabled(True)
        self.goto_btn.setEnabled(True)

        designation = item.data(Qt.UserRole)
        component_id = item.data(Qt.UserRole + 1)
        self._show_component_details(designation)

        # Emit selection signal with component ID
        if component_id:
            self.component_selected.emit(component_id)

    def _on_component_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle component double-click (toggle).

        Args:
            item: Double-clicked item
        """
        designation = item.data(Qt.UserRole)
        self._toggle_component(designation)

    def _toggle_selected(self) -> None:
        """Toggle the selected component."""
        current_item = self.component_list.currentItem()
        if current_item:
            designation = current_item.data(Qt.UserRole)
            self._toggle_component(designation)

    def _toggle_component(self, designation: str) -> None:
        """Toggle a component and update simulation.

        Args:
            designation: Component designation
        """
        if not self.simulator:
            return

        # Toggle component
        self.simulator.toggle_component(designation)

        # Refresh display
        self._refresh_component_list()
        self._show_component_details(designation)

        # Emit signal
        self.component_toggled.emit(designation)
        self.simulation_updated.emit()

    def _trace_selected(self) -> None:
        """Trace circuit for selected component."""
        current_item = self.component_list.currentItem()
        if not current_item or not self.simulator:
            return

        designation = current_item.data(Qt.UserRole)
        explanation = self.simulator.explain_state(designation)
        self.detail_text.setPlainText(explanation)

    def _goto_selected_page(self) -> None:
        """Navigate to the page of the selected component."""
        current_item = self.component_list.currentItem()
        if not current_item or not self.diagram:
            return

        designation = current_item.data(Qt.UserRole)
        component = self.diagram.get_component_by_designation(designation)
        if component:
            self.go_to_page.emit(component.page)

    def _show_component_details(self, designation: str) -> None:
        """Show details for a component.

        Args:
            designation: Component designation
        """
        if not self.diagram or not self.simulator:
            return

        component = self.diagram.get_component_by_designation(designation)
        if not component:
            return

        node = self.simulator.voltage_nodes.get(component.id)

        details = f"Component: {designation}\n"
        details += f"Type: {component.type.value}\n"
        details += f"Description: {component.description or 'N/A'}\n"
        details += f"Voltage Rating: {component.voltage_rating or 'N/A'}\n"
        details += f"Page: {component.page + 1}\n"
        details += f"\nCurrent State:\n"

        if node and node.is_energized:
            details += f"  Status: ENERGIZED\n"
            details += f"  Voltage: {node.voltage_level}V\n"
            details += f"  Type: {node.voltage_type}\n"
        else:
            details += f"  Status: DE-ENERGIZED\n"

        if component.is_sensor():
            details += f"\nSensor Configuration:\n"
            details += f"  State: {component.state.value}\n"
            details += f"  Contact Type: {'NO (Normally Open)' if component.normally_open else 'NC (Normally Closed)'}\n"
            details += f"\n(Double-click to toggle sensor state)"

        self.detail_text.setPlainText(details)

    def _run_simulation(self) -> None:
        """Run simulation step."""
        if not self.simulator:
            return

        self.simulator.simulate_step()
        self._refresh_component_list()
        self.simulation_updated.emit()

    def get_energized_components(self) -> List[str]:
        """Get list of energized component IDs.

        Returns:
            List of component IDs that are currently energized
        """
        if not self.simulator:
            return []

        energized_comps = self.simulator.get_energized_components()
        return [comp.id for comp in energized_comps]

    def select_component_by_id(self, component_id: str) -> None:
        """Select a component in the list by its ID.

        Args:
            component_id: Component ID to select
        """
        for i in range(self.component_list.count()):
            item = self.component_list.item(i)
            if item.data(Qt.UserRole + 1) == component_id:
                self.component_list.setCurrentItem(item)
                self.component_list.scrollToItem(item)
                self._on_component_selected(item)
                break
