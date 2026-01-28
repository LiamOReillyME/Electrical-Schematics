"""Interactive PDF viewer widget with annotation support."""

from typing import Optional, List, Dict, Tuple
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QScrollArea, QMenu
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QPen, QColor, QPixmap, QMouseEvent, QBrush,
    QDragEnterEvent, QDragMoveEvent, QDropEvent, QKeyEvent, QFont, QAction
)
from electrical_schematics.pdf import PDFRenderer
from electrical_schematics.models import IndustrialComponent, Wire
from electrical_schematics.gui.wire_tool import WireDrawingTool, WireType
import json


class ComponentOverlay:
    """Represents a visual overlay for a component on a specific page."""

    def __init__(
        self,
        component: IndustrialComponent,
        is_energized: bool,
        page: int,
        rect: Optional[QRectF] = None
    ):
        """Initialize component overlay.

        Args:
            component: The component to overlay
            is_energized: Whether component is energized
            page: PDF page number (0-indexed)
            rect: Optional custom rectangle (uses component position if None)
        """
        self.component = component
        self.is_energized = is_energized
        self.page = page
        if rect is not None:
            self.rect = rect
        else:
            self.rect = QRectF(component.x, component.y, component.width, component.height)


class PDFViewer(QWidget):
    """Widget for displaying PDF and annotating components."""

    # Signals
    component_dropped = Signal(float, float, dict)  # x, y, component_data
    component_double_clicked = Signal(object)  # IndustrialComponent
    component_selected = Signal(str)  # component_id (empty string if cleared)
    component_edit_requested = Signal(object)  # IndustrialComponent (for context menu edit)
    component_delete_requested = Signal(object)  # IndustrialComponent (for context menu delete)
    component_toggle_requested = Signal(object)  # IndustrialComponent (for context menu toggle)
    component_moved = Signal(object, float, float)  # IndustrialComponent, new_x, new_y
    wire_completed = Signal(object)  # Wire object
    wire_drawing_state_changed = Signal(str)  # State message for UI
    page_changed = Signal(int)  # Current page number (0-indexed)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the PDF viewer."""
        super().__init__(parent)

        self.renderer: Optional[PDFRenderer] = None
        self.pdf_path: Optional[str] = None
        self.current_page = 0
        self.zoom_level = 1.0
        self.pixmap: Optional[QPixmap] = None

        # Annotation state (removed - components are drag-drop only)
        self.annotations: List[QRect] = []

        # Component overlays for simulation visualization
        self.component_overlays: List[ComponentOverlay] = []
        self.show_overlays = True

        # Component selection
        self.selected_component_id: Optional[str] = None

        # Component hover state
        self.hovered_component_id: Optional[str] = None

        # Component dragging state
        self.dragging_component: Optional[IndustrialComponent] = None
        self.drag_offset_x: float = 0.0
        self.drag_offset_y: float = 0.0

        # Wire drawing
        self.wire_tool = WireDrawingTool()
        self.wire_tool.wire_completed.connect(self._on_wire_completed)
        self.wire_tool.state_changed.connect(self.wire_drawing_state_changed.emit)
        self.wires: List[Wire] = []
        self.show_wires = True
        self.wire_drawing_mode = False  # Controlled by main window

        # Enable drag-and-drop
        self.setAcceptDrops(True)

        # Enable keyboard events for ESC
        self.setFocusPolicy(Qt.StrongFocus)

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

        # Enable context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area for panning
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        # Label to display PDF
        self.pdf_label = QLabel()
        self.pdf_label.setAlignment(Qt.AlignCenter)
        self.pdf_label.setStyleSheet("background-color: #2b2b2b;")
        self.pdf_label.setMouseTracking(True)

        # Initial message
        self.pdf_label.setText("Open a PDF file to begin")
        self.pdf_label.setStyleSheet("""
            background-color: #2b2b2b;
            color: #7F8C8D;
            font-size: 16px;
        """)

        self.scroll_area.setWidget(self.pdf_label)
        layout.addWidget(self.scroll_area)

    def _show_context_menu(self, position: QPoint) -> None:
        """Show context menu at the given position.

        Args:
            position: Position in widget coordinates
        """
        if not self.pixmap:
            return

        # Convert to PDF coordinates
        label_pos = self.pdf_label.mapFromGlobal(self.mapToGlobal(position))
        pdf_x = label_pos.x() / (self.zoom_level * 2)
        pdf_y = label_pos.y() / (self.zoom_level * 2)

        # Find component at this position
        component = self._find_component_at(pdf_x, pdf_y)

        # Create context menu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3498DB;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background-color: #D5DBDB;
                margin: 4px 8px;
            }
        """)

        if component:
            # Select the component first
            self.selected_component_id = component.id
            self.component_selected.emit(component.id)
            self._update_display()

            # Component-specific actions
            edit_action = QAction("Edit Component...", self)
            edit_action.setShortcut("Enter")
            edit_action.triggered.connect(lambda: self.component_edit_requested.emit(component))
            menu.addAction(edit_action)

            toggle_action = QAction("Toggle State", self)
            toggle_action.setShortcut("Space")
            toggle_action.triggered.connect(lambda: self.component_toggle_requested.emit(component))
            menu.addAction(toggle_action)

            menu.addSeparator()

            # Check energization state for display
            energized_status = "Unknown"
            for overlay in self.component_overlays:
                if overlay.component.id == component.id:
                    energized_status = "Energized" if overlay.is_energized else "De-energized"
                    break

            status_action = QAction(f"Status: {energized_status}", self)
            status_action.setEnabled(False)
            menu.addAction(status_action)

            type_action = QAction(f"Type: {component.type.value}", self)
            type_action.setEnabled(False)
            menu.addAction(type_action)

            if component.voltage_rating:
                voltage_action = QAction(f"Voltage: {component.voltage_rating}", self)
                voltage_action.setEnabled(False)
                menu.addAction(voltage_action)

            # Show page info - show all pages if multi-page
            pages = component.get_pages()
            if len(pages) > 1:
                page_str = ", ".join(str(p + 1) for p in pages)
                page_action = QAction(f"Pages: {page_str}", self)
            else:
                page_action = QAction(f"Page: {component.page + 1}", self)
            page_action.setEnabled(False)
            menu.addAction(page_action)

            menu.addSeparator()

            delete_action = QAction("Delete Component", self)
            delete_action.setShortcut("Delete")
            delete_action.triggered.connect(lambda: self.component_delete_requested.emit(component))
            menu.addAction(delete_action)

        else:
            # No component at position - general actions
            if self.wire_drawing_mode:
                cancel_wire = QAction("Cancel Wire Drawing", self)
                cancel_wire.triggered.connect(self.cancel_wire_drawing)
                menu.addAction(cancel_wire)
            else:
                # Placeholder for future features
                paste_action = QAction("Paste Component", self)
                paste_action.setEnabled(False)  # Not yet implemented
                menu.addAction(paste_action)

        menu.exec(self.mapToGlobal(position))

    def load_pdf(self, pdf_path: str, page: int = 0) -> None:
        """Load a PDF file.

        Args:
            pdf_path: Path to the PDF file
            page: Page number to display (0-indexed)
        """
        from pathlib import Path

        if self.renderer:
            self.renderer.close()

        self.pdf_path = pdf_path
        self.renderer = PDFRenderer(Path(pdf_path))
        self.current_page = page

        # Reset the label style for PDF display
        self.pdf_label.setStyleSheet("background-color: #2b2b2b;")
        self.pdf_label.setText("")

        self.render_page()
        # Emit page changed signal
        self.page_changed.emit(self.current_page)

    def render_page(self) -> None:
        """Render the current page."""
        if not self.renderer:
            return

        self.pixmap = self.renderer.render_page(self.current_page, self.zoom_level)
        if self.pixmap:
            self._update_display()

    def _update_display(self) -> None:
        """Update the displayed image with annotations."""
        if not self.pixmap:
            return

        # Create a copy to draw annotations on
        display_pixmap = QPixmap(self.pixmap)
        painter = QPainter(display_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        # Draw component overlays (simulation state)
        if self.show_overlays:
            for overlay in self.component_overlays:
                if overlay.page == self.current_page:
                    self._draw_component_overlay(painter, overlay)

        # Draw wires
        if self.show_wires:
            self._draw_wires(painter)

        # Draw wire preview if drawing
        if self.wire_tool.is_drawing():
            self._draw_wire_preview(painter)

        painter.end()

        self.pdf_label.setPixmap(display_pixmap)

    def _draw_component_overlay(self, painter: QPainter, overlay: ComponentOverlay) -> None:
        """Draw a component overlay on the PDF.

        Args:
            painter: Qt painter
            overlay: Component overlay to draw
        """
        # Convert PDF coordinates to screen coordinates
        rect = QRectF(
            overlay.rect.x() * self.zoom_level * 2,
            overlay.rect.y() * self.zoom_level * 2,
            overlay.rect.width() * self.zoom_level * 2,
            overlay.rect.height() * self.zoom_level * 2
        )

        # Check if this component is selected or hovered
        is_selected = (overlay.component.id == self.selected_component_id)
        is_hovered = (overlay.component.id == self.hovered_component_id)

        # Choose color based on selection, hover, and energization state
        if is_selected:
            # Yellow highlight for selected components
            fill_color = QColor(255, 255, 0, 100)  # Semi-transparent yellow
            border_color = QColor(255, 200, 0, 255)
            border_style = Qt.DashLine
            border_width = 4
            text_bg_color = QColor(255, 200, 0, 220)  # Yellow background for text
            text_color = QColor(0, 0, 0)  # Black text
        elif is_hovered:
            # Blue highlight for hovered components
            fill_color = QColor(52, 152, 219, 60)  # Semi-transparent blue
            border_color = QColor(52, 152, 219, 255)
            border_style = Qt.SolidLine
            border_width = 3
            if overlay.is_energized:
                text_bg_color = QColor(39, 174, 96, 220)
                text_color = QColor(255, 255, 255)
            else:
                text_bg_color = QColor(231, 76, 60, 220)
                text_color = QColor(255, 255, 255)
        elif overlay.is_energized:
            # Green overlay for energized components
            fill_color = QColor(0, 255, 0, 60)  # Semi-transparent green
            border_color = QColor(0, 200, 0, 200)
            border_style = Qt.SolidLine
            border_width = 3
            text_bg_color = QColor(39, 174, 96, 220)  # Green background
            text_color = QColor(255, 255, 255)  # White text
        else:
            # Red overlay for de-energized components
            fill_color = QColor(255, 0, 0, 40)  # Semi-transparent red
            border_color = QColor(200, 0, 0, 150)
            border_style = Qt.SolidLine
            border_width = 3
            text_bg_color = QColor(231, 76, 60, 220)  # Red background
            text_color = QColor(255, 255, 255)  # White text

        # Draw filled rectangle
        painter.setBrush(QBrush(fill_color))
        painter.setPen(QPen(border_color, border_width, border_style))
        painter.drawRect(rect)

        # Draw component designation label with background for contrast
        designation = overlay.component.designation

        # Set up font
        font = QFont("Arial", max(8, int(10 * self.zoom_level)))
        font.setBold(True)
        painter.setFont(font)

        # Calculate text size
        font_metrics = painter.fontMetrics()
        text_width = font_metrics.horizontalAdvance(designation) + 8
        text_height = font_metrics.height() + 4

        # Draw text background
        text_rect = QRectF(
            rect.x() + 3,
            rect.y() + 3,
            text_width,
            text_height
        )
        painter.setBrush(QBrush(text_bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(text_rect, 3, 3)

        # Draw text
        painter.setPen(QPen(text_color))
        painter.drawText(
            text_rect,
            Qt.AlignCenter,
            designation
        )

        # Draw terminal points
        self._draw_terminals(painter, overlay.component)

    def _draw_terminals(self, painter: QPainter, component: IndustrialComponent) -> None:
        """Draw terminal points for a component.

        Args:
            painter: Qt painter
            component: Component to draw terminals for
        """
        # BUGFIX: Get PDF coordinates for terminals, then convert to screen
        pdf_terminals = self._get_terminal_positions_pdf(component)

        # Convert to screen coordinates
        screen_terminals = []
        for pdf_term in pdf_terminals:
            screen_x = pdf_term.x() * self.zoom_level * 2
            screen_y = pdf_term.y() * self.zoom_level * 2
            screen_terminals.append(QPointF(screen_x, screen_y))

        # Draw terminal circles with better visibility
        terminal_radius = max(3, 4 * self.zoom_level)  # Scale with zoom, minimum 3

        # Draw outer circle (dark border)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(0, 0, 0, 200), 2))
        for terminal_pos in screen_terminals:
            painter.drawEllipse(terminal_pos, terminal_radius + 1, terminal_radius + 1)

        # Draw inner circle (yellow fill)
        painter.setBrush(QBrush(QColor(255, 230, 0, 255)))  # Brighter yellow
        painter.setPen(QPen(QColor(200, 180, 0), 1))
        for terminal_pos in screen_terminals:
            painter.drawEllipse(terminal_pos, terminal_radius, terminal_radius)

    def _get_terminal_positions_pdf(self, component: IndustrialComponent) -> List[QPointF]:
        """Calculate terminal positions for a component in PDF coordinates.

        BUGFIX: This method calculates terminals directly in PDF coordinates,
        avoiding the double-conversion bug.

        Args:
            component: Component to get terminals for

        Returns:
            List of terminal positions in PDF coordinates
        """
        from electrical_schematics.models import IndustrialComponentType

        terminals = []
        center_x = component.x + component.width / 2
        center_y = component.y + component.height / 2

        # Define terminal positions based on component type (in PDF coords)
        component_type = component.type

        if component_type in [IndustrialComponentType.CONTACTOR, IndustrialComponentType.RELAY]:
            # Contactors/Relays: coil terminals on left, contact terminals on right
            terminals.append(QPointF(component.x + 10, center_y - 10))
            terminals.append(QPointF(component.x + 10, center_y + 10))
            terminals.append(QPointF(component.x + component.width - 10, center_y - 10))
            terminals.append(QPointF(component.x + component.width - 10, center_y + 10))

        elif component_type in [
            IndustrialComponentType.PROXIMITY_SENSOR,
            IndustrialComponentType.PHOTOELECTRIC_SENSOR,
            IndustrialComponentType.LIMIT_SWITCH,
            IndustrialComponentType.PRESSURE_SWITCH,
            IndustrialComponentType.TEMPERATURE_SENSOR
        ]:
            # Sensors: power on left, output on right
            terminals.append(QPointF(component.x + 10, center_y - 10))
            terminals.append(QPointF(component.x + 10, center_y + 10))
            terminals.append(QPointF(component.x + component.width - 10, center_y))

        elif component_type in [IndustrialComponentType.POWER_24VDC, IndustrialComponentType.POWER_400VAC]:
            # Power supplies: positive/L on top, negative/N on bottom
            terminals.append(QPointF(center_x, component.y + 10))
            terminals.append(QPointF(center_x, component.y + component.height - 10))

        elif component_type == IndustrialComponentType.MOTOR:
            # Motors: three-phase terminals at top
            terminals.append(QPointF(center_x - 15, component.y + 10))
            terminals.append(QPointF(center_x, component.y + 10))
            terminals.append(QPointF(center_x + 15, component.y + 10))

        elif component_type in [IndustrialComponentType.PLC_INPUT, IndustrialComponentType.PLC_OUTPUT]:
            # PLC modules: terminals along left edge
            num_terminals = 8
            spacing = component.height / (num_terminals + 1)
            for i in range(num_terminals):
                terminals.append(QPointF(component.x + 10, component.y + spacing * (i + 1)))

        else:
            # Default: two terminals on left and right
            terminals.append(QPointF(component.x + 10, center_y))
            terminals.append(QPointF(component.x + component.width - 10, center_y))

        return terminals

    def _draw_wires(self, painter: QPainter) -> None:
        """Draw all wires on the PDF.

        Args:
            painter: Qt painter
        """
        for wire in self.wires:
            # Determine color based on voltage level
            if "24" in wire.voltage_level or "24VDC" in wire.voltage_level:
                color = QColor(231, 76, 60)  # Red for 24VDC
            elif "0V" in wire.voltage_level or wire.voltage_level == "0V":
                color = QColor(52, 152, 219)  # Blue for 0V
            elif "AC" in wire.voltage_level:
                color = QColor(44, 62, 80)  # Dark gray for AC
            else:
                color = QColor(149, 165, 166)  # Gray for unknown

            pen = QPen(color, 3)
            painter.setPen(pen)

            # Convert path points to screen coordinates
            screen_points = []
            for point in wire.path:
                screen_x = point.x * self.zoom_level * 2
                screen_y = point.y * self.zoom_level * 2
                screen_points.append(QPointF(screen_x, screen_y))

            # Draw connected line segments
            for i in range(len(screen_points) - 1):
                painter.drawLine(screen_points[i], screen_points[i + 1])

            # Draw terminal connection circles at start and end
            painter.setBrush(QBrush(color))
            if len(screen_points) >= 2:
                painter.drawEllipse(screen_points[0], 5, 5)
                painter.drawEllipse(screen_points[-1], 5, 5)

    def _draw_wire_preview(self, painter: QPainter) -> None:
        """Draw wire preview while drawing.

        Args:
            painter: Qt painter
        """
        terminal_positions = self._get_all_terminal_positions()
        preview_path = self.wire_tool.get_preview_path(terminal_positions)
        if not preview_path or len(preview_path) < 2:
            return

        wire_type = self.wire_tool.get_wire_type()
        wire_color = wire_type.value[1]

        pen = QPen(wire_color, 3, Qt.DashLine)
        painter.setPen(pen)

        for i in range(len(preview_path) - 1):
            screen_start = QPointF(
                preview_path[i].x() * self.zoom_level * 2,
                preview_path[i].y() * self.zoom_level * 2
            )
            screen_end = QPointF(
                preview_path[i + 1].x() * self.zoom_level * 2,
                preview_path[i + 1].y() * self.zoom_level * 2
            )
            painter.drawLine(screen_start, screen_end)

        painter.setBrush(QBrush(wire_color))
        for i in range(1, len(preview_path) - 1):
            screen_pos = QPointF(
                preview_path[i].x() * self.zoom_level * 2,
                preview_path[i].y() * self.zoom_level * 2
            )
            painter.drawEllipse(screen_pos, 4, 4)

    def _get_all_terminal_positions(self) -> Dict[str, List[QPointF]]:
        """Get terminal positions for all components in PDF coordinates.

        BUGFIX: Completely rewritten to calculate terminals directly in PDF coordinates
        instead of converting from screen coordinates.

        Returns:
            Dict mapping component_id to list of terminal positions (PDF coords)
        """
        terminal_positions = {}

        for overlay in self.component_overlays:
            if overlay.page == self.current_page:
                # Calculate terminals based on component's PDF position directly
                pdf_terminals = self._get_terminal_positions_pdf(overlay.component)
                terminal_positions[overlay.component.id] = pdf_terminals

        return terminal_positions

    def _on_wire_completed(self, wire: Wire) -> None:
        """Handle wire completion from wire tool.

        Args:
            wire: Completed wire
        """
        self.wires.append(wire)
        self._update_display()
        self.wire_completed.emit(wire)

    def _find_component_at(self, pdf_x: float, pdf_y: float) -> Optional[IndustrialComponent]:
        """Find component at the given PDF coordinates.

        Args:
            pdf_x: X coordinate in PDF space
            pdf_y: Y coordinate in PDF space

        Returns:
            Component at position or None
        """
        for overlay in self.component_overlays:
            if overlay.page == self.current_page:
                rect = overlay.rect
                if (rect.x() <= pdf_x <= rect.x() + rect.width() and
                    rect.y() <= pdf_y <= rect.y() + rect.height()):
                    return overlay.component
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press for wire drawing, component selection, or area selection."""
        if event.button() == Qt.LeftButton and self.pixmap:
            label_pos = self.pdf_label.mapFromGlobal(event.globalPosition().toPoint())

            pdf_x = label_pos.x() / (self.zoom_level * 2)
            pdf_y = label_pos.y() / (self.zoom_level * 2)
            pdf_pos = QPointF(pdf_x, pdf_y)

            if self.wire_drawing_mode or self.wire_tool.is_drawing():
                components = [overlay.component for overlay in self.component_overlays if overlay.page == self.current_page]
                terminal_positions = self._get_all_terminal_positions()

                handled = self.wire_tool.handle_click(pdf_pos, components, terminal_positions)
                if handled:
                    self._update_display()
                    return

            clicked_component = self._find_component_at(pdf_x, pdf_y)

            if clicked_component:
                self.selected_component_id = clicked_component.id
                self.component_selected.emit(clicked_component.id)

                if not self.wire_drawing_mode:
                    self.dragging_component = clicked_component
                    self.drag_offset_x = pdf_x - clicked_component.x
                    self.drag_offset_y = pdf_y - clicked_component.y
                    self.setCursor(Qt.ClosedHandCursor)

                self._update_display()
            else:
                self.selected_component_id = None
                self.component_selected.emit("")
                self._update_display()

        elif event.button() == Qt.RightButton:
            if self.wire_tool.is_drawing():
                if self.wire_tool.handle_right_click():
                    self._update_display()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move for wire preview, component dragging, or hover effects."""
        if not self.pixmap:
            return

        label_pos = self.pdf_label.mapFromGlobal(event.globalPosition().toPoint())

        pdf_x = label_pos.x() / (self.zoom_level * 2)
        pdf_y = label_pos.y() / (self.zoom_level * 2)
        pdf_pos = QPointF(pdf_x, pdf_y)

        if self.dragging_component:
            self.dragging_component.x = pdf_x - self.drag_offset_x
            self.dragging_component.y = pdf_y - self.drag_offset_y

            for overlay in self.component_overlays:
                if overlay.component.id == self.dragging_component.id:
                    overlay.rect = QRectF(
                        self.dragging_component.x,
                        self.dragging_component.y,
                        self.dragging_component.width,
                        self.dragging_component.height
                    )

            self._update_display()
            return

        if self.wire_tool.is_drawing():
            self.wire_tool.handle_mouse_move(pdf_pos)
            self._update_display()
            return

        hovered_component = self._find_component_at(pdf_x, pdf_y)
        new_hovered_id = hovered_component.id if hovered_component else None

        if new_hovered_id != self.hovered_component_id:
            self.hovered_component_id = new_hovered_id

            if hovered_component:
                if self.wire_drawing_mode:
                    self.setCursor(Qt.CrossCursor)
                else:
                    self.setCursor(Qt.OpenHandCursor)
            else:
                if self.wire_drawing_mode:
                    self.setCursor(Qt.CrossCursor)
                else:
                    self.setCursor(Qt.ArrowCursor)

            self._update_display()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release to finalize component dragging."""
        if self.dragging_component:
            # Emit moved signal before clearing state
            moved_component = self.dragging_component
            self.component_moved.emit(moved_component, moved_component.x, moved_component.y)

            # Dragging finished
            self.dragging_component = None
            self.drag_offset_x = 0.0
            self.drag_offset_y = 0.0

            # Reset cursor
            if self.hovered_component_id:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

            self._update_display()

    def set_zoom(self, zoom: float) -> None:
        """Set the zoom level and re-render."""
        self.zoom_level = max(0.1, min(5.0, zoom))
        self.render_page()

    def next_page(self) -> None:
        """Go to the next page."""
        if self.renderer and self.current_page < self.renderer.get_page_count() - 1:
            self.current_page += 1
            self.selected_component_id = None
            self.hovered_component_id = None
            self.render_page()
            self.page_changed.emit(self.current_page)

    def previous_page(self) -> None:
        """Go to the previous page."""
        if self.renderer and self.current_page > 0:
            self.current_page -= 1
            self.selected_component_id = None
            self.hovered_component_id = None
            self.render_page()
            self.page_changed.emit(self.current_page)

    def go_to_page(self, page: int) -> None:
        """Navigate to a specific page.

        Args:
            page: Page number (0-indexed)
        """
        if self.renderer and 0 <= page < self.renderer.get_page_count():
            self.current_page = page
            self.selected_component_id = None
            self.hovered_component_id = None
            self.render_page()
            self.page_changed.emit(self.current_page)

    def get_current_page(self) -> int:
        """Get the current page number.

        Returns:
            Current page number (0-indexed)
        """
        return self.current_page

    def get_page_count(self) -> int:
        """Get total number of pages.

        Returns:
            Total page count
        """
        if self.renderer:
            return self.renderer.get_page_count()
        return 0

    def set_component_overlays(
        self,
        components: List[IndustrialComponent],
        energized_ids: List[str]
    ) -> None:
        """Set component overlays for simulation visualization.

        Creates overlays for all pages where each component appears,
        supporting multi-page components.

        Args:
            components: List of all components
            energized_ids: List of component IDs that are energized
        """
        self.component_overlays.clear()
        energized_set = set(energized_ids)

        for comp in components:
            # Skip components without position
            if comp.x == 0 and comp.y == 0 and not comp.page_positions:
                continue

            is_energized = comp.id in energized_set

            # Handle multi-page components
            if comp.page_positions:
                # Create overlay for each page position
                for page, page_pos in comp.page_positions.items():
                    rect = QRectF(page_pos.x, page_pos.y, page_pos.width, page_pos.height)
                    overlay = ComponentOverlay(
                        component=comp,
                        is_energized=is_energized,
                        page=page,
                        rect=rect
                    )
                    self.component_overlays.append(overlay)
            else:
                # Single position - use component's primary page
                overlay = ComponentOverlay(
                    component=comp,
                    is_energized=is_energized,
                    page=comp.page
                )
                self.component_overlays.append(overlay)

        self._update_display()

    def toggle_overlays(self, show: bool) -> None:
        """Toggle visibility of component overlays.

        Args:
            show: True to show overlays, False to hide
        """
        self.show_overlays = show
        self._update_display()

    def clear_overlays(self) -> None:
        """Clear all component overlays."""
        self.component_overlays.clear()
        self._update_display()

    def select_component(self, component_id: str) -> None:
        """Select a component by ID.

        Args:
            component_id: ID of component to select
        """
        self.selected_component_id = component_id
        self._update_display()

    def clear_selection(self) -> None:
        """Clear component selection."""
        self.selected_component_id = None
        self._update_display()

    def get_selected_component(self) -> Optional[IndustrialComponent]:
        """Get the currently selected component.

        Returns:
            Selected component or None
        """
        if not self.selected_component_id:
            return None

        for overlay in self.component_overlays:
            if overlay.component.id == self.selected_component_id:
                return overlay.component
        return None

    def set_wire_type(self, wire_type: WireType) -> None:
        """Set the wire type for drawing.

        Args:
            wire_type: Wire type to use
        """
        self.wire_tool.set_wire_type(wire_type)

    def set_wire_drawing_mode(self, enabled: bool) -> None:
        """Enable or disable wire drawing mode.

        Args:
            enabled: True to enable wire drawing mode
        """
        self.wire_drawing_mode = enabled
        if enabled:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
            self.wire_tool.cancel_drawing()
            self._update_display()

    def cancel_wire_drawing(self) -> None:
        """Cancel current wire drawing."""
        self.wire_tool.cancel_drawing()
        self._update_display()

    def is_drawing_wire(self) -> bool:
        """Check if currently drawing a wire.

        Returns:
            True if drawing wire
        """
        return self.wire_tool.is_drawing()

    def set_wires(self, wires: List[Wire]) -> None:
        """Set the list of wires to display.

        Args:
            wires: List of wires
        """
        self.wires = wires
        self._update_display()

    def clear_wires(self) -> None:
        """Clear all wires."""
        self.wires.clear()
        self._update_display()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events.

        Args:
            event: Key event
        """
        if event.key() == Qt.Key_Escape:
            if self.wire_tool.handle_escape():
                self._update_display()
                event.accept()
                return
            if self.selected_component_id:
                self.selected_component_id = None
                self.component_selected.emit("")
                self._update_display()
                event.accept()
                return

        if event.key() == Qt.Key_Delete:
            selected = self.get_selected_component()
            if selected:
                self.component_delete_requested.emit(selected)
                event.accept()
                return

        super().keyPressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event.

        Args:
            event: Drag enter event
        """
        if event.mimeData().hasFormat('application/x-component-template'):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Handle drag move event.

        Args:
            event: Drag move event
        """
        if event.mimeData().hasFormat('application/x-component-template'):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event.

        Args:
            event: Drop event
        """
        if not event.mimeData().hasFormat('application/x-component-template'):
            event.ignore()
            return

        pos = event.position().toPoint()
        label_pos = self.pdf_label.mapFromGlobal(self.mapToGlobal(pos))

        pdf_x = label_pos.x() / (self.zoom_level * 2)
        pdf_y = label_pos.y() / (self.zoom_level * 2)

        try:
            component_json = event.mimeData().data('application/x-component-template').data().decode('utf-8')
            component_data = json.loads(component_json)

            self.component_dropped.emit(pdf_x, pdf_y, component_data)
            event.acceptProposedAction()

        except Exception as e:
            print(f"Error parsing dropped component data: {e}")
            event.ignore()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Handle mouse double-click event.

        Args:
            event: Mouse event
        """
        if event.button() == Qt.LeftButton and self.pixmap:
            label_pos = self.pdf_label.mapFromGlobal(event.globalPosition().toPoint())

            pdf_x = label_pos.x() / (self.zoom_level * 2)
            pdf_y = label_pos.y() / (self.zoom_level * 2)

            for overlay in self.component_overlays:
                if overlay.page == self.current_page:
                    rect = overlay.rect
                    if (rect.x() <= pdf_x <= rect.x() + rect.width() and
                        rect.y() <= pdf_y <= rect.y() + rect.height()):
                        self.component_double_clicked.emit(overlay.component)
                        return

        super().mouseDoubleClickEvent(event)
