"""Wire drawing tool with multi-point routing."""

from enum import Enum
from typing import Optional, List, Tuple
from PySide6.QtCore import QPointF, Signal, QObject
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
from electrical_schematics.models import Wire, WirePoint, IndustrialComponent


class WireType(Enum):
    """Types of wires with associated colors."""
    DC_24V = ("24VDC", QColor(255, 0, 0), "24VDC")  # Red
    DC_0V = ("0V", QColor(0, 0, 255), "0V")  # Blue
    AC_POWER = ("AC", QColor(0, 0, 0), "AC")  # Black


class DrawingState(Enum):
    """States for wire drawing state machine."""
    IDLE = "idle"
    DRAWING = "drawing"


class WireDrawingTool(QObject):
    """Tool for drawing wires with multi-point routing."""

    # Signals
    wire_completed = Signal(object)  # Wire object
    drawing_cancelled = Signal()
    state_changed = Signal(str)  # State name for UI updates

    def __init__(self):
        """Initialize wire drawing tool."""
        super().__init__()

        self.state = DrawingState.IDLE
        self.current_wire_type = WireType.DC_24V

        # Drawing state
        self.start_component: Optional[IndustrialComponent] = None
        self.start_terminal: Optional[int] = None
        self.waypoints: List[QPointF] = []
        self.current_cursor_pos: Optional[QPointF] = None

        # Terminal detection radius (in PDF coordinates)
        self.terminal_radius = 10.0

    def set_wire_type(self, wire_type: WireType) -> None:
        """Set the current wire type.

        Args:
            wire_type: Wire type to use
        """
        self.current_wire_type = wire_type

    def get_wire_type(self) -> WireType:
        """Get the current wire type.

        Returns:
            Current wire type
        """
        return self.current_wire_type

    def is_drawing(self) -> bool:
        """Check if currently drawing a wire.

        Returns:
            True if in drawing state
        """
        return self.state == DrawingState.DRAWING

    def handle_click(
        self,
        pdf_pos: QPointF,
        components: List[IndustrialComponent],
        terminal_positions: dict
    ) -> bool:
        """Handle click event for wire drawing.

        Args:
            pdf_pos: Click position in PDF coordinates
            components: List of all components
            terminal_positions: Dict mapping component_id -> list of terminal positions (PDF coords)

        Returns:
            True if click was handled (drawing in progress)
        """
        if self.state == DrawingState.IDLE:
            # Try to start wire from a terminal
            component, terminal_idx = self._find_terminal_at(pdf_pos, components, terminal_positions)

            if component and terminal_idx is not None:
                # Start drawing wire
                self.start_component = component
                self.start_terminal = terminal_idx
                self.waypoints = []
                self.state = DrawingState.DRAWING
                self.state_changed.emit("Drawing wire - click to add waypoints, click terminal to complete")
                return True

            return False

        elif self.state == DrawingState.DRAWING:
            # Check if clicking on a terminal (to complete wire)
            component, terminal_idx = self._find_terminal_at(pdf_pos, components, terminal_positions)

            if component and terminal_idx is not None and component.id != self.start_component.id:
                # Complete the wire
                self._complete_wire(component, terminal_idx, terminal_positions)
                return True
            else:
                # Add waypoint
                self._add_waypoint(pdf_pos)
                return True

        return False

    def handle_mouse_move(self, pdf_pos: QPointF) -> None:
        """Handle mouse move for preview.

        Args:
            pdf_pos: Current mouse position in PDF coordinates
        """
        if self.state == DrawingState.DRAWING:
            self.current_cursor_pos = pdf_pos

    def handle_right_click(self) -> bool:
        """Handle right click to cancel drawing.

        Returns:
            True if drawing was cancelled
        """
        if self.state == DrawingState.DRAWING:
            self.cancel_drawing()
            return True
        return False

    def handle_escape(self) -> bool:
        """Handle escape key to cancel drawing.

        Returns:
            True if drawing was cancelled
        """
        return self.handle_right_click()

    def cancel_drawing(self) -> None:
        """Cancel the current wire drawing."""
        if self.state == DrawingState.DRAWING:
            self.state = DrawingState.IDLE
            self.start_component = None
            self.start_terminal = None
            self.waypoints = []
            self.current_cursor_pos = None
            self.drawing_cancelled.emit()
            self.state_changed.emit("Wire drawing cancelled")

    def _find_terminal_at(
        self,
        pos: QPointF,
        components: List[IndustrialComponent],
        terminal_positions: dict
    ) -> Tuple[Optional[IndustrialComponent], Optional[int]]:
        """Find terminal at the given position.

        Args:
            pos: Position in PDF coordinates
            components: List of all components
            terminal_positions: Dict mapping component_id -> list of terminal positions

        Returns:
            Tuple of (component, terminal_index) or (None, None)
        """
        for component in components:
            if component.id not in terminal_positions:
                continue

            terminals = terminal_positions[component.id]
            for idx, terminal_pos in enumerate(terminals):
                # Check distance to terminal
                dx = pos.x() - terminal_pos.x()
                dy = pos.y() - terminal_pos.y()
                distance = (dx * dx + dy * dy) ** 0.5

                if distance <= self.terminal_radius:
                    return component, idx

        return None, None

    def _add_waypoint(self, pos: QPointF) -> None:
        """Add a waypoint to the current wire.

        Args:
            pos: Waypoint position in PDF coordinates
        """
        self.waypoints.append(pos)
        self.state_changed.emit(f"Added waypoint {len(self.waypoints)} - click terminal to complete or add more waypoints")

    def _complete_wire(
        self,
        end_component: IndustrialComponent,
        end_terminal: int,
        terminal_positions: dict
    ) -> None:
        """Complete the wire and emit signal.

        Args:
            end_component: Component where wire ends
            end_terminal: Terminal index on end component
            terminal_positions: Dict mapping component_id -> list of terminal positions
        """
        # Get start and end positions
        start_pos = terminal_positions[self.start_component.id][self.start_terminal]
        end_pos = terminal_positions[end_component.id][end_terminal]

        # Build path: start -> waypoints -> end
        path_points = []
        path_points.append(WirePoint(start_pos.x(), start_pos.y()))

        for waypoint in self.waypoints:
            path_points.append(WirePoint(waypoint.x(), waypoint.y()))

        path_points.append(WirePoint(end_pos.x(), end_pos.y()))

        # Create wire object
        wire = Wire(
            id=f"wire_{id(self)}_{len(path_points)}",
            voltage_level=self.current_wire_type.value[2],  # "24VDC", "0V", or "AC"
            path=path_points,
            from_component_id=self.start_component.id,
            to_component_id=end_component.id
        )

        # Reset state
        self.state = DrawingState.IDLE
        self.start_component = None
        self.start_terminal = None
        self.waypoints = []
        self.current_cursor_pos = None

        # Emit completion signal
        self.wire_completed.emit(wire)
        self.state_changed.emit("Wire completed")

    def render_preview(self, painter: QPainter, zoom_level: float) -> None:
        """Render wire preview while drawing.

        Args:
            painter: Qt painter
            zoom_level: Current zoom level
        """
        if self.state != DrawingState.DRAWING or not self.start_component:
            return

        # Get wire color
        wire_color = self.current_wire_type.value[1]
        pen = QPen(wire_color, 3, )
        painter.setPen(pen)

        # We need the start position - this would come from the terminal positions
        # For preview, we'll draw from waypoints if any exist, or just show cursor line
        if len(self.waypoints) > 0 and self.current_cursor_pos:
            # Draw line from last waypoint to cursor
            last_waypoint = self.waypoints[-1]
            screen_start = self._to_screen_coords(last_waypoint, zoom_level)
            screen_end = self._to_screen_coords(self.current_cursor_pos, zoom_level)
            painter.drawLine(screen_start, screen_end)

        # Draw waypoint markers
        painter.setBrush(QBrush(wire_color))
        for waypoint in self.waypoints:
            screen_pos = self._to_screen_coords(waypoint, zoom_level)
            painter.drawEllipse(screen_pos, 4, 4)

    def _to_screen_coords(self, pdf_pos: QPointF, zoom_level: float) -> QPointF:
        """Convert PDF coordinates to screen coordinates.

        Args:
            pdf_pos: Position in PDF coordinates
            zoom_level: Current zoom level

        Returns:
            Position in screen coordinates
        """
        return QPointF(
            pdf_pos.x() * zoom_level * 2,
            pdf_pos.y() * zoom_level * 2
        )

    def get_preview_path(self, terminal_positions: dict) -> Optional[List[QPointF]]:
        """Get the current preview path including cursor position.

        Args:
            terminal_positions: Dict mapping component_id -> list of terminal positions

        Returns:
            List of points forming the preview path, or None if not drawing
        """
        if self.state != DrawingState.DRAWING or not self.start_component:
            return None

        path = []

        # Start position
        if self.start_component.id in terminal_positions:
            start_pos = terminal_positions[self.start_component.id][self.start_terminal]
            path.append(start_pos)

        # Waypoints
        path.extend(self.waypoints)

        # Current cursor position
        if self.current_cursor_pos:
            path.append(self.current_cursor_pos)

        return path if len(path) > 1 else None
