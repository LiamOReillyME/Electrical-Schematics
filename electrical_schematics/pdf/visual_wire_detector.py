"""Visual wire detection from PDF pages using color analysis.

This module provides advanced wire detection capabilities including:
- RGB and HSV color space detection for improved accuracy
- Wire path tracing algorithms (BFS/DFS graph traversal)
- Manhattan and straight-line routing generation
- Integration with cable routing tables
- Wire vs border/grid discrimination using heuristic classification
"""

import colorsys
import math
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Literal

import fitz  # PyMuPDF


class LineType(Enum):
    """Classification of detected line segments."""
    WIRE = "wire"                    # Actual electrical wire
    BORDER = "border"                # Page border/frame
    TITLE_BLOCK = "title_block"      # Title block grid lines
    TABLE_GRID = "table_grid"        # Table/grid lines
    COMPONENT_OUTLINE = "component_outline"  # Component shape outlines
    UNKNOWN = "unknown"              # Unclassified


class WireColor(Enum):
    """Wire color classifications based on industrial standards."""
    RED = "red"          # 24V / L+
    BLUE = "blue"        # 0V / L-
    GREEN = "green"      # Ground/PE
    YELLOW_GREEN = "yellow_green"  # PE (protective earth)
    BLACK = "black"      # Various / Phase
    BROWN = "brown"      # Phase L1 / 24V+
    WHITE = "white"      # Neutral / Signal
    ORANGE = "orange"    # Control circuits
    GRAY = "gray"        # Control circuits
    OTHER = "other"


@dataclass
class WirePoint:
    """A point in a wire path."""
    x: float
    y: float

    def distance_to(self, other: 'WirePoint') -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def __hash__(self) -> int:
        """Hash based on rounded coordinates for tolerance-based matching."""
        return hash((round(self.x, 1), round(self.y, 1)))

    def __eq__(self, other: object) -> bool:
        """Equality with tolerance for floating point comparison."""
        if not isinstance(other, WirePoint):
            return False
        return (round(self.x, 1) == round(other.x, 1) and
                round(self.y, 1) == round(other.y, 1))


@dataclass
class VisualWire:
    """A visually detected wire segment on a PDF page."""

    page_number: int
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    color: WireColor
    rgb: Tuple[float, float, float]
    thickness: float

    @property
    def voltage_type(self) -> str:
        """Infer voltage type from wire color based on industrial conventions."""
        voltage_map = {
            WireColor.RED: "24VDC",
            WireColor.BROWN: "24VDC",
            WireColor.BLUE: "0V",
            WireColor.GREEN: "PE",
            WireColor.YELLOW_GREEN: "PE",
            WireColor.BLACK: "400VAC",
            WireColor.ORANGE: "24VDC",
        }
        return voltage_map.get(self.color, "UNKNOWN")

    @property
    def start_point(self) -> WirePoint:
        """Get start point as WirePoint."""
        return WirePoint(self.start_x, self.start_y)

    @property
    def end_point(self) -> WirePoint:
        """Get end point as WirePoint."""
        return WirePoint(self.end_x, self.end_y)

    @property
    def length(self) -> float:
        """Calculate wire segment length."""
        dx = self.end_x - self.start_x
        dy = self.end_y - self.start_y
        return math.sqrt(dx ** 2 + dy ** 2)

    @property
    def is_horizontal(self) -> bool:
        """Check if wire is primarily horizontal."""
        dx = abs(self.end_x - self.start_x)
        dy = abs(self.end_y - self.start_y)
        return dx > dy * 3  # 3:1 ratio for horizontal

    @property
    def is_vertical(self) -> bool:
        """Check if wire is primarily vertical."""
        dx = abs(self.end_x - self.start_x)
        dy = abs(self.end_y - self.start_y)
        return dy > dx * 3  # 3:1 ratio for vertical


@dataclass
class WirePath:
    """A complete wire path consisting of connected segments."""

    segments: List[VisualWire] = field(default_factory=list)
    color: WireColor = WireColor.OTHER
    page_number: int = 0

    @property
    def points(self) -> List[WirePoint]:
        """Get ordered list of points along the path."""
        if not self.segments:
            return []

        points = [self.segments[0].start_point]
        for segment in self.segments:
            points.append(segment.end_point)
        return points

    @property
    def total_length(self) -> float:
        """Calculate total path length."""
        return sum(seg.length for seg in self.segments)

    @property
    def voltage_type(self) -> str:
        """Get voltage type from first segment."""
        if self.segments:
            return self.segments[0].voltage_type
        return "UNKNOWN"


class ColorClassifier:
    """Advanced color classification using RGB and HSV color spaces."""

    # Color thresholds in HSV (Hue 0-360, Saturation 0-1, Value 0-1)
    # Hue ranges: Red 0-30 and 330-360, Orange 30-60, Yellow 60-90,
    #             Green 90-150, Cyan 150-210, Blue 210-270,
    #             Purple 270-330

    @staticmethod
    def rgb_to_hsv(r: float, g: float, b: float) -> Tuple[float, float, float]:
        """Convert RGB (0-1 range) to HSV (H: 0-360, S: 0-1, V: 0-1)."""
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        return h * 360, s, v

    @classmethod
    def classify(cls, rgb: Tuple[float, float, float]) -> WireColor:
        """Classify RGB color into wire categories using HSV analysis.

        Args:
            rgb: RGB tuple (0-1 range)

        Returns:
            WireColor classification
        """
        r, g, b = rgb

        # Convert to HSV for better color discrimination
        h, s, v = cls.rgb_to_hsv(r, g, b)

        # Black detection: very low value (brightness)
        if v < 0.15:
            return WireColor.BLACK

        # White detection: high value, low saturation (check BEFORE gray)
        # White has both high brightness AND low saturation
        if v > 0.85 and s < 0.15:
            return WireColor.WHITE

        # Gray detection: low saturation with medium-high brightness
        # Only classify as gray if not bright enough to be white
        if s < 0.15 and 0.3 < v <= 0.85:
            return WireColor.GRAY

        # Saturated colors - use hue for classification
        if s >= 0.25:
            # Red (0-20 or 340-360)
            if h < 20 or h > 340:
                return WireColor.RED

            # Orange (20-45)
            if 20 <= h < 45:
                return WireColor.ORANGE

            # Yellow-Green (45-80) - could be yellow-green PE wire
            if 45 <= h < 80:
                # Check if it's the typical yellow-green PE color
                if g > 0.5 and r > 0.5:
                    return WireColor.YELLOW_GREEN
                return WireColor.OTHER

            # Green (80-160)
            if 80 <= h < 160:
                return WireColor.GREEN

            # Blue (200-260)
            if 200 <= h < 260:
                return WireColor.BLUE

            # Brown (15-40 with lower saturation/value)
            if 15 <= h < 40 and v < 0.6:
                return WireColor.BROWN

        # Fallback RGB-based detection for edge cases
        return cls._rgb_fallback(r, g, b)

    @staticmethod
    def _rgb_fallback(r: float, g: float, b: float) -> WireColor:
        """Fallback RGB-based classification for edge cases."""
        # Red: high red, low green/blue (relaxed thresholds)
        if r > 0.5 and g < 0.4 and b < 0.4 and r > max(g, b) * 1.5:
            return WireColor.RED

        # Blue: high blue, low red/green (relaxed thresholds)
        if b > 0.5 and r < 0.4 and g < 0.4 and b > max(r, g) * 1.5:
            return WireColor.BLUE

        # Green: high green (relaxed thresholds)
        if g > 0.5 and r < 0.4 and b < 0.4 and g > max(r, b) * 1.5:
            return WireColor.GREEN

        # Brown: medium values with red dominant
        if 0.3 < r < 0.7 and g < 0.4 and b < 0.3:
            return WireColor.BROWN

        # Black: all values low
        if r < 0.25 and g < 0.25 and b < 0.25:
            return WireColor.BLACK

        return WireColor.OTHER


class LineClassifier:
    """Classifies line segments to distinguish wires from borders, grids, etc."""

    def __init__(
        self,
        page_width: float,
        page_height: float,
        border_margin: float = 20.0,
        title_block_ratio: float = 0.85,
        grid_tolerance: float = 3.0,
        shape_tolerance: float = 8.0
    ):
        """Initialize the line classifier.

        Args:
            page_width: PDF page width in points
            page_height: PDF page height in points
            border_margin: Margin from page edge to classify as border
            title_block_ratio: Y-position ratio (0-1) above which is title block
            grid_tolerance: Alignment tolerance for grid detection (points)
            shape_tolerance: Proximity tolerance for shape detection (points)
        """
        self.page_width = page_width
        self.page_height = page_height
        self.border_margin = border_margin
        self.title_block_y = page_height * title_block_ratio
        self.grid_tolerance = grid_tolerance
        self.shape_tolerance = shape_tolerance

        # Track all lines for pattern analysis
        self._all_lines: List[VisualWire] = []
        self._horizontal_positions: List[float] = []
        self._vertical_positions: List[float] = []

    def classify_line(
        self,
        line: VisualWire,
        all_lines: Optional[List[VisualWire]] = None
    ) -> LineType:
        """Classify a line segment as wire, border, grid, etc.

        Args:
            line: Line segment to classify
            all_lines: All lines on the page (for pattern detection)

        Returns:
            LineType classification
        """
        # 1. Border check - lines near page edges
        if self._is_border(line):
            return LineType.BORDER

        # 2. Title block check - lines in bottom region
        if self._is_title_block(line):
            return LineType.TITLE_BLOCK

        # 3. Grid pattern check - regularly spaced lines
        if all_lines and self._is_grid_line(line, all_lines):
            return LineType.TABLE_GRID

        # 4. Component outline check - small clustered lines forming shapes
        if all_lines and self._is_component_outline(line, all_lines):
            return LineType.COMPONENT_OUTLINE

        # 5. Wire characteristics check
        if self._has_wire_characteristics(line):
            return LineType.WIRE

        return LineType.UNKNOWN

    def _is_border(self, line: VisualWire) -> bool:
        """Check if line is part of page border.

        Borders are:
        - Very close to page edges (within margin)
        - Often form rectangles
        - Usually span most of page dimension
        """
        margin = self.border_margin

        # Check if line endpoints are near page edges
        near_left = line.start_x < margin or line.end_x < margin
        near_right = line.start_x > self.page_width - margin or line.end_x > self.page_width - margin
        near_top = line.start_y < margin or line.end_y < margin
        near_bottom = line.start_y > self.page_height - margin or line.end_y > self.page_height - margin

        # Horizontal line at top or bottom
        if line.is_horizontal and (near_top or near_bottom):
            if line.length > self.page_width * 0.7:  # Spans most of page
                return True

        # Vertical line at left or right
        if line.is_vertical and (near_left or near_right):
            if line.length > self.page_height * 0.7:  # Spans most of page
                return True

        return False

    def _is_title_block(self, line: VisualWire) -> bool:
        """Check if line is part of title block or header.

        Title blocks are typically:
        - At bottom of page (y > 85% of page height)
        - At top of page (y < 20 points - header region)
        - Form grid patterns
        - Small to medium length
        """
        # Header region (top of page)
        if line.start_y < 20 and line.end_y < 20:
            return True

        # Check if both endpoints in title block region (bottom)
        if line.start_y > self.title_block_y and line.end_y > self.title_block_y:
            # Title block lines are often short to medium length
            if line.length < self.page_width * 0.4:
                return True

            # Or horizontal lines spanning width
            if line.is_horizontal and line.length > self.page_width * 0.5:
                return True

        return False

    def _is_grid_line(self, line: VisualWire, all_lines: List[VisualWire]) -> bool:
        """Check if line is part of a regular grid pattern.

        Grid lines have:
        - Regular spacing in same orientation
        - Multiple parallel lines at similar positions
        - Uniform lengths
        """
        tolerance = self.grid_tolerance

        # Get parallel lines in same orientation
        if line.is_horizontal:
            # Find other horizontal lines at similar y-position
            similar_y = [
                other for other in all_lines
                if other.is_horizontal and
                abs(other.start_y - line.start_y) < tolerance and
                id(other) != id(line)
            ]

            # Check for regular spacing pattern (3+ lines)
            if len(similar_y) >= 2:
                # Get y-positions of parallel lines
                y_positions = sorted([line.start_y] + [l.start_y for l in similar_y[:2]])
                if len(y_positions) >= 3:
                    # Check for regular spacing
                    spacing = [y_positions[i+1] - y_positions[i] for i in range(len(y_positions)-1)]
                    avg_spacing = sum(spacing) / len(spacing)
                    # If spacing is consistent, it's likely a grid
                    if all(abs(s - avg_spacing) < tolerance * 2 for s in spacing):
                        return True

        elif line.is_vertical:
            # Find other vertical lines at similar x-position
            similar_x = [
                other for other in all_lines
                if other.is_vertical and
                abs(other.start_x - line.start_x) < tolerance and
                id(other) != id(line)
            ]

            if len(similar_x) >= 2:
                x_positions = sorted([line.start_x] + [l.start_x for l in similar_x[:2]])
                if len(x_positions) >= 3:
                    spacing = [x_positions[i+1] - x_positions[i] for i in range(len(x_positions)-1)]
                    avg_spacing = sum(spacing) / len(spacing)
                    if all(abs(s - avg_spacing) < tolerance * 2 for s in spacing):
                        return True

        return False

    def _is_component_outline(self, line: VisualWire, all_lines: List[VisualWire]) -> bool:
        """Check if line is part of a component outline.

        Component outlines:
        - Short line segments (< 30 points typically)
        - Form closed or nearly closed shapes
        - Have multiple connected segments nearby
        - Often black/gray color (rarely colored)
        - Not horizontal or vertical (wires are usually orthogonal)
        """
        # Longer lines are not component outlines
        if line.length > 50:
            return False

        # Colored lines are usually wires, not outlines
        if line.color in [WireColor.RED, WireColor.BLUE, WireColor.GREEN,
                         WireColor.BROWN, WireColor.ORANGE]:
            return False

        # Very short lines forming shapes
        if line.length < 25:
            # Check if line has nearby parallel/perpendicular segments
            # forming a box-like structure
            tolerance = self.shape_tolerance
            nearby_count = 0

            for other in all_lines:
                if id(other) == id(line):
                    continue

                # Only check other short lines
                if other.length > 50:
                    continue

                # Check if endpoints are close
                if (line.start_point.distance_to(other.start_point) < tolerance or
                    line.start_point.distance_to(other.end_point) < tolerance or
                    line.end_point.distance_to(other.start_point) < tolerance or
                    line.end_point.distance_to(other.end_point) < tolerance):

                    # Check if other line is similar length (forming a shape)
                    if 0.5 < other.length / line.length < 2.0:
                        nearby_count += 1

                if nearby_count >= 2:
                    # Multiple similar-length lines connected = likely component outline
                    return True

        return False

    def _has_wire_characteristics(self, line: VisualWire) -> bool:
        """Check if line has characteristics typical of electrical wires.

        Wires typically:
        - Longer lines connecting distant points (> 30 points)
        - Colored (not just black/gray)
        - Horizontal or vertical in schematic layouts
        - May have thickness variations
        - Short colored diagonal segments (wire connectors)
        """
        # Very long lines are almost always wires
        if line.length > 50:
            # Any color is fine for very long lines
            return True

        # Long lines are likely wires
        if line.length > 30:
            # Colored lines are usually wires (not black/gray/white)
            if line.color not in [WireColor.BLACK, WireColor.GRAY, WireColor.WHITE, WireColor.OTHER]:
                return True

            # Long horizontal/vertical black/gray lines are likely wires
            if line.is_horizontal or line.is_vertical:
                return True

        # Medium-length colored lines
        if line.length > 15:
            if line.color in [WireColor.RED, WireColor.BLUE, WireColor.GREEN,
                            WireColor.BROWN, WireColor.ORANGE]:
                return True

            # Medium-length gray lines that are horizontal/vertical
            if line.color == WireColor.GRAY and (line.is_horizontal or line.is_vertical):
                return True

        # Short colored diagonal segments (often wire connectors/junctions)
        # These are common in schematics for connecting components
        if line.length >= 8:
            if line.color in [WireColor.RED, WireColor.BLUE, WireColor.GREEN]:
                # Accept short colored diagonals as wires
                return True

        return False


class WirePathTracer:
    """Algorithm to trace continuous wire paths from line segments."""

    def __init__(self, tolerance: float = 5.0):
        """Initialize the path tracer.

        Args:
            tolerance: Distance tolerance for connecting segments (in points)
        """
        self.tolerance = tolerance
        self._adjacency: Dict[WirePoint, List[Tuple[WirePoint, VisualWire]]] = defaultdict(list)
        # Map from segment to all its connected segments (including via tolerance)
        self._segment_connections: Dict[int, Set[int]] = defaultdict(set)

    def build_graph(self, segments: List[VisualWire]) -> None:
        """Build adjacency graph from wire segments.

        Args:
            segments: List of wire segments to connect
        """
        self._adjacency.clear()
        self._segment_connections.clear()

        # Create segment lookup by endpoint
        point_to_segments: Dict[WirePoint, List[VisualWire]] = defaultdict(list)

        for segment in segments:
            start = segment.start_point
            end = segment.end_point

            # Add bidirectional edges
            self._adjacency[start].append((end, segment))
            self._adjacency[end].append((start, segment))

            # Track which segments touch each point
            point_to_segments[start].append(segment)
            point_to_segments[end].append(segment)

        # Build direct segment connections from shared points
        for _point, segs in point_to_segments.items():
            for i, seg1 in enumerate(segs):
                for seg2 in segs[i+1:]:
                    self._segment_connections[id(seg1)].add(id(seg2))
                    self._segment_connections[id(seg2)].add(id(seg1))

        # Connect nearby endpoints (within tolerance)
        self._connect_nearby_segments(segments, point_to_segments)

    def _connect_nearby_segments(
        self,
        segments: List[VisualWire],
        point_to_segments: Dict[WirePoint, List[VisualWire]]
    ) -> None:
        """Connect wire segments that are close but not exactly touching."""
        # Collect all unique points with their segments
        all_points = list(point_to_segments.keys())

        # Find and connect nearby points
        for i, p1 in enumerate(all_points):
            for p2 in all_points[i + 1:]:
                dist = p1.distance_to(p2)
                if 0 < dist <= self.tolerance:
                    # Connect all segments at p1 to all segments at p2
                    segs_at_p1 = point_to_segments[p1]
                    segs_at_p2 = point_to_segments[p2]

                    for seg1 in segs_at_p1:
                        for seg2 in segs_at_p2:
                            self._segment_connections[id(seg1)].add(id(seg2))
                            self._segment_connections[id(seg2)].add(id(seg1))

                    # Also add virtual adjacency for graph traversal
                    self._adjacency[p1].append((p2, None))
                    self._adjacency[p2].append((p1, None))

    def trace_paths(self, segments: List[VisualWire]) -> List[WirePath]:
        """Trace all continuous wire paths from segments.

        Uses BFS to find connected components and trace paths.

        Args:
            segments: List of wire segments

        Returns:
            List of WirePath objects representing complete wire routes
        """
        if not segments:
            return []

        self.build_graph(segments)

        # Create ID to segment lookup
        id_to_segment = {id(seg): seg for seg in segments}

        visited_segments: Set[int] = set()
        paths: List[WirePath] = []

        for segment in segments:
            seg_id = id(segment)
            if seg_id in visited_segments:
                continue

            # Start BFS from this segment using direct segment connections
            path_segments = self._bfs_trace_segments(
                segment, id_to_segment, visited_segments
            )
            if path_segments:
                path = WirePath(
                    segments=path_segments,
                    color=segment.color,
                    page_number=segment.page_number
                )
                paths.append(path)

        return paths

    def _bfs_trace_segments(
        self,
        start_segment: VisualWire,
        id_to_segment: Dict[int, VisualWire],
        visited: Set[int]
    ) -> List[VisualWire]:
        """BFS traversal using direct segment connections.

        Args:
            start_segment: Starting wire segment
            id_to_segment: Mapping from segment ID to segment
            visited: Set of visited segment IDs

        Returns:
            List of connected segments forming a path
        """
        path_segments: List[VisualWire] = []
        queue = [id(start_segment)]
        visited.add(id(start_segment))

        while queue:
            current_id = queue.pop(0)
            current = id_to_segment[current_id]
            path_segments.append(current)

            # Find connected segments through the segment connection map
            for neighbor_id in self._segment_connections.get(current_id, []):
                if neighbor_id not in visited:
                    neighbor = id_to_segment.get(neighbor_id)
                    if neighbor and neighbor.color == current.color:
                        visited.add(neighbor_id)
                        queue.append(neighbor_id)

        return path_segments

    def find_junctions(self, segments: List[VisualWire]) -> List[WirePoint]:
        """Find junction points where 3+ wires meet.

        Args:
            segments: List of wire segments

        Returns:
            List of junction points
        """
        self.build_graph(segments)
        junctions = []

        for point, neighbors in self._adjacency.items():
            # Filter to only actual segments (not virtual connections)
            segment_count = sum(1 for _, seg in neighbors if seg is not None)
            if segment_count >= 3:
                junctions.append(point)

        return junctions


class WirePathGenerator:
    """Generates visual wire paths from component positions and cable routing data."""

    @staticmethod
    def generate_manhattan_path(
        src_x: float, src_y: float,
        tgt_x: float, tgt_y: float,
        exit_direction: str = "auto"
    ) -> List[WirePoint]:
        """Generate orthogonal (right-angle) wire path.

        Args:
            src_x, src_y: Source position
            tgt_x, tgt_y: Target position
            exit_direction: "horizontal", "vertical", or "auto"

        Returns:
            List of WirePoint forming Manhattan path
        """
        points = [WirePoint(src_x, src_y)]

        dx = tgt_x - src_x
        dy = tgt_y - src_y

        # Determine routing strategy
        if exit_direction == "auto":
            # Choose based on relative positions
            exit_direction = "horizontal" if abs(dx) > abs(dy) else "vertical"

        if exit_direction == "horizontal":
            # Go horizontal first, then vertical
            mid_x = src_x + dx / 2
            points.append(WirePoint(mid_x, src_y))
            points.append(WirePoint(mid_x, tgt_y))
        else:
            # Go vertical first, then horizontal
            mid_y = src_y + dy / 2
            points.append(WirePoint(src_x, mid_y))
            points.append(WirePoint(tgt_x, mid_y))

        points.append(WirePoint(tgt_x, tgt_y))
        return points

    @staticmethod
    def generate_l_path(
        src_x: float, src_y: float,
        tgt_x: float, tgt_y: float,
        horizontal_first: bool = True
    ) -> List[WirePoint]:
        """Generate L-shaped wire path with single bend.

        Args:
            src_x, src_y: Source position
            tgt_x, tgt_y: Target position
            horizontal_first: If True, go horizontal then vertical

        Returns:
            List of WirePoint forming L-path
        """
        points = [WirePoint(src_x, src_y)]

        if horizontal_first:
            points.append(WirePoint(tgt_x, src_y))  # Horizontal to target x
        else:
            points.append(WirePoint(src_x, tgt_y))  # Vertical to target y

        points.append(WirePoint(tgt_x, tgt_y))
        return points

    @staticmethod
    def generate_straight_line(
        src_x: float, src_y: float,
        tgt_x: float, tgt_y: float
    ) -> List[WirePoint]:
        """Generate direct straight-line path.

        Args:
            src_x, src_y: Source position
            tgt_x, tgt_y: Target position

        Returns:
            List of two WirePoints (start and end)
        """
        return [
            WirePoint(src_x, src_y),
            WirePoint(tgt_x, tgt_y)
        ]

    @staticmethod
    def generate_smooth_path(
        src_x: float, src_y: float,
        tgt_x: float, tgt_y: float,
        segments: int = 10
    ) -> List[WirePoint]:
        """Generate smooth curved path using quadratic bezier.

        Useful for diagonal connections that should curve naturally.

        Args:
            src_x, src_y: Source position
            tgt_x, tgt_y: Target position
            segments: Number of segments for curve approximation

        Returns:
            List of WirePoints along the curve
        """
        # Control point at the midpoint, offset for curve
        mid_x = (src_x + tgt_x) / 2
        mid_y = (src_y + tgt_y) / 2

        # Offset control point perpendicular to line
        dx = tgt_x - src_x
        dy = tgt_y - src_y
        length = math.sqrt(dx * dx + dy * dy)

        if length < 1:
            return [WirePoint(src_x, src_y), WirePoint(tgt_x, tgt_y)]

        # Perpendicular offset (10% of length)
        offset = length * 0.1
        ctrl_x = mid_x - dy / length * offset
        ctrl_y = mid_y + dx / length * offset

        # Generate bezier curve points
        points = []
        for i in range(segments + 1):
            t = i / segments
            # Quadratic bezier formula
            x = (1 - t) ** 2 * src_x + 2 * (1 - t) * t * ctrl_x + t ** 2 * tgt_x
            y = (1 - t) ** 2 * src_y + 2 * (1 - t) * t * ctrl_y + t ** 2 * tgt_y
            points.append(WirePoint(x, y))

        return points


class VisualWireDetector:
    """Detects wires on PDF pages using visual/geometric analysis.

    Features:
    - RGB and HSV color space detection
    - Configurable color thresholds
    - Line filtering by length and orientation
    - Wire path tracing
    """

    # Default detection parameters
    DEFAULT_MIN_LENGTH = 8.0
    DEFAULT_MAX_THICKNESS = 5.0
    DEFAULT_MIN_SATURATION = 0.2

    def __init__(
        self,
        doc: fitz.Document,
        min_wire_length: float = DEFAULT_MIN_LENGTH,
        max_wire_thickness: float = DEFAULT_MAX_THICKNESS,
        min_color_saturation: float = DEFAULT_MIN_SATURATION,
        enable_classification: bool = True
    ):
        """Initialize the detector.

        Args:
            doc: PyMuPDF document
            min_wire_length: Minimum segment length to consider (in points)
            max_wire_thickness: Maximum line thickness for wires
            min_color_saturation: Minimum saturation for colored wires
            enable_classification: Enable wire vs border/grid classification
        """
        self.doc = doc
        self.min_wire_length = min_wire_length
        self.max_wire_thickness = max_wire_thickness
        self.min_color_saturation = min_color_saturation
        self.enable_classification = enable_classification
        self._classifier = ColorClassifier()
        self._path_tracer = WirePathTracer()
        self._line_classifier: Optional[LineClassifier] = None

    def detect_wires(self, page_num: int) -> List[VisualWire]:
        """Detect wires on a specific page.

        Args:
            page_num: Page number (0-indexed)

        Returns:
            List of detected wires
        """
        if page_num >= len(self.doc):
            return []

        page = self.doc[page_num]
        wires = []

        # Get drawing commands from page
        drawings = page.get_drawings()

        for drawing in drawings:
            detected = self._process_drawing(drawing, page_num)
            wires.extend(detected)

        return wires

    def detect_wires_only(self, page_num: int) -> List[VisualWire]:
        """Detect only actual wires, filtering out borders, grids, etc.

        This method uses classification to distinguish electrical wires from:
        - Page borders and frames
        - Title block grid lines
        - Table grids
        - Component outlines

        Args:
            page_num: Page number (0-indexed)

        Returns:
            List of detected wires (filtered)
        """
        if page_num >= len(self.doc):
            return []

        # Get all line segments
        all_lines = self.detect_wires(page_num)

        if not all_lines or not self.enable_classification:
            return all_lines

        # Initialize line classifier with page dimensions
        page = self.doc[page_num]
        page_rect = page.rect
        self._line_classifier = LineClassifier(
            page_width=page_rect.width,
            page_height=page_rect.height
        )

        # Classify each line and keep only wires
        wires_only = []
        for line in all_lines:
            line_type = self._line_classifier.classify_line(line, all_lines)
            if line_type == LineType.WIRE:
                wires_only.append(line)

        return wires_only

    def classify_all_lines(self, page_num: int) -> Dict[LineType, List[VisualWire]]:
        """Classify all detected lines by type.

        Useful for analysis and debugging classification logic.

        Args:
            page_num: Page number (0-indexed)

        Returns:
            Dictionary mapping LineType to list of lines of that type
        """
        if page_num >= len(self.doc):
            return {}

        # Get all line segments
        all_lines = self.detect_wires(page_num)

        if not all_lines:
            return {}

        # Initialize line classifier
        page = self.doc[page_num]
        page_rect = page.rect
        self._line_classifier = LineClassifier(
            page_width=page_rect.width,
            page_height=page_rect.height
        )

        # Classify each line
        classified: Dict[LineType, List[VisualWire]] = defaultdict(list)
        for line in all_lines:
            line_type = self._line_classifier.classify_line(line, all_lines)
            classified[line_type].append(line)

        return dict(classified)

    def _process_drawing(self, drawing: dict, page_num: int) -> List[VisualWire]:
        """Process a single drawing element.

        PyMuPDF drawing structure:
        - drawing["type"] is typically "s" (stroke) or "f" (fill)
        - drawing["items"] contains path commands like:
          ('l', Point(x1, y1), Point(x2, y2)) for lines
          ('m', Point(x, y)) for move commands
          ('c', Point, Point, Point, Point) for curves
          ('re', Rect) for rectangles
          ('qu', Quad) for quadrilaterals

        Args:
            drawing: Drawing dictionary from PyMuPDF
            page_num: Current page number

        Returns:
            List of detected wires from this drawing
        """
        wires = []
        items = drawing.get("items", [])
        color = drawing.get("color")
        stroke_color = drawing.get("stroke")
        width = drawing.get("width", 1.0)

        # Use stroke color if available, otherwise use fill color
        actual_color = stroke_color if stroke_color else color

        if not actual_color or not items:
            return wires

        # Skip if too thick (likely not a wire)
        if width > self.max_wire_thickness:
            return wires

        # Classify the color
        wire_color = self._classifier.classify(actual_color)

        # Process all items looking for line commands
        # PyMuPDF format: ('l', Point(start), Point(end))
        for item in items:
            if not isinstance(item, (tuple, list)) or len(item) < 1:
                continue

            cmd = item[0]

            # Handle line command: ('l', Point(x1,y1), Point(x2,y2))
            if cmd == 'l' and len(item) >= 3:
                start_point = item[1]
                end_point = item[2]

                # Extract coordinates from Point objects or tuples
                start_x, start_y = self._extract_point_coords(start_point)
                end_x, end_y = self._extract_point_coords(end_point)

                if start_x is not None and end_x is not None:
                    if self._is_wire_like((start_x, start_y), (end_x, end_y)):
                        wire = VisualWire(
                            page_number=page_num,
                            start_x=start_x,
                            start_y=start_y,
                            end_x=end_x,
                            end_y=end_y,
                            color=wire_color,
                            rgb=actual_color,
                            thickness=width
                        )
                        wires.append(wire)

        return wires

    def _extract_point_coords(self, point) -> Tuple[Optional[float], Optional[float]]:
        """Extract x, y coordinates from various point representations.

        Handles:
        - PyMuPDF Point objects (have .x and .y attributes)
        - Tuples/lists of coordinates
        - Numbers (returns None, None)

        Args:
            point: A point representation

        Returns:
            Tuple of (x, y) coordinates, or (None, None) if extraction fails
        """
        # Handle PyMuPDF Point objects
        if hasattr(point, 'x') and hasattr(point, 'y'):
            return float(point.x), float(point.y)

        # Handle tuple/list of coordinates
        if isinstance(point, (tuple, list)) and len(point) >= 2:
            try:
                return float(point[0]), float(point[1])
            except (TypeError, ValueError):
                return None, None

        return None, None

    def _is_wire_like(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float]
    ) -> bool:
        """Check if line segment looks like a wire.

        Wires are typically:
        - Horizontal or vertical lines (most common)
        - Diagonal connections (45-degree or other angles)
        - Above minimum length threshold
        - Below maximum thickness

        Args:
            p1: Start point
            p2: End point

        Returns:
            True if this looks like a wire
        """
        dx = abs(p2[0] - p1[0])
        dy = abs(p2[1] - p1[1])

        # Calculate length
        length = math.sqrt(dx ** 2 + dy ** 2)

        # Filter by minimum length
        if length < self.min_wire_length:
            return False

        # Horizontal lines (very common for wires)
        if dy < 2:
            return True

        # Vertical lines (very common for wires)
        if dx < 2:
            return True

        # Diagonal connections - longer ones are more likely valid
        if length > 15:
            return True

        # Short diagonals with specific angles (45, 30, 60 degrees)
        if length > 8:
            angle = math.atan2(dy, dx) * 180 / math.pi
            # Check for common wire angles
            if any(abs(angle - target) < 10 for target in [30, 45, 60]):
                return True

        return False

    def detect_and_trace_paths(self, page_num: int) -> List[WirePath]:
        """Detect wires and trace complete paths.

        Args:
            page_num: Page number (0-indexed)

        Returns:
            List of traced WirePath objects
        """
        segments = self.detect_wires(page_num)
        return self._path_tracer.trace_paths(segments)

    def detect_wires_by_color(
        self,
        page_num: int,
        target_color: WireColor
    ) -> List[VisualWire]:
        """Detect only wires of a specific color.

        Args:
            page_num: Page number
            target_color: Color to filter for

        Returns:
            List of wires matching the color
        """
        all_wires = self.detect_wires(page_num)
        return [w for w in all_wires if w.color == target_color]

    def find_nearest_wire(
        self,
        x: float,
        y: float,
        page_num: int,
        tolerance: float = 10.0
    ) -> Optional[VisualWire]:
        """Find the nearest wire to a point.

        Args:
            x: X coordinate
            y: Y coordinate
            page_num: Page number
            tolerance: Distance tolerance in points

        Returns:
            Nearest wire within tolerance, or None
        """
        wires = self.detect_wires(page_num)

        nearest = None
        min_distance = float('inf')

        for wire in wires:
            dist = self._point_to_segment_distance(
                x, y,
                wire.start_x, wire.start_y,
                wire.end_x, wire.end_y
            )

            if dist < min_distance and dist <= tolerance:
                min_distance = dist
                nearest = wire

        return nearest

    def get_wire_statistics(self, page_num: int) -> Dict[str, any]:
        """Get statistics about detected wires on a page.

        Args:
            page_num: Page number

        Returns:
            Dictionary with wire statistics
        """
        wires = self.detect_wires(page_num)

        # Count by color
        color_counts = defaultdict(int)
        for wire in wires:
            color_counts[wire.color.value] += 1

        # Count by voltage type
        voltage_counts = defaultdict(int)
        for wire in wires:
            voltage_counts[wire.voltage_type] += 1

        # Calculate average length
        if wires:
            avg_length = sum(w.length for w in wires) / len(wires)
            max_length = max(w.length for w in wires)
            min_length = min(w.length for w in wires)
        else:
            avg_length = max_length = min_length = 0

        return {
            'total_count': len(wires),
            'color_distribution': dict(color_counts),
            'voltage_distribution': dict(voltage_counts),
            'average_length': avg_length,
            'max_length': max_length,
            'min_length': min_length,
            'horizontal_count': sum(1 for w in wires if w.is_horizontal),
            'vertical_count': sum(1 for w in wires if w.is_vertical),
        }

    @staticmethod
    def _point_to_segment_distance(
        px: float, py: float,
        x1: float, y1: float,
        x2: float, y2: float
    ) -> float:
        """Calculate distance from point to line segment.

        Args:
            px, py: Point coordinates
            x1, y1: Segment start
            x2, y2: Segment end

        Returns:
            Distance in points
        """
        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)

        # Parameter t along the line
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))

        # Nearest point on segment
        nearest_x = x1 + t * dx
        nearest_y = y1 + t * dy

        return math.sqrt((px - nearest_x) ** 2 + (py - nearest_y) ** 2)


def generate_wire_paths_from_connections(
    connections: List[dict],
    component_positions: Dict[str, dict],
    routing_style: str = "manhattan"
) -> List[dict]:
    """Generate visual wire paths from cable routing data.

    This function creates wire path visualizations by connecting
    component positions based on cable routing table data.

    Args:
        connections: List of connection dictionaries with keys:
            - source_device: str
            - target_device: str
            - voltage_level: str (optional)
            - wire_color: str (optional)
        component_positions: Dictionary mapping device IDs to position dicts:
            - x: float
            - y: float
            - width: float (optional)
            - height: float (optional)
        routing_style: "manhattan", "l_path", "straight", or "smooth"

    Returns:
        List of wire dictionaries with:
            - from_component_id: str
            - to_component_id: str
            - voltage_level: str
            - path: List[WirePoint]
    """
    generator = WirePathGenerator()
    wires = []

    for conn in connections:
        src_device = conn.get('source_device')
        tgt_device = conn.get('target_device')

        src_pos = component_positions.get(src_device)
        tgt_pos = component_positions.get(tgt_device)

        if not src_pos or not tgt_pos:
            continue

        # Get center positions (accounting for component size)
        src_x = src_pos.get('x', 0) + src_pos.get('width', 0) / 2
        src_y = src_pos.get('y', 0) + src_pos.get('height', 0) / 2
        tgt_x = tgt_pos.get('x', 0) + tgt_pos.get('width', 0) / 2
        tgt_y = tgt_pos.get('y', 0) + tgt_pos.get('height', 0) / 2

        # Generate path based on style
        if routing_style == "manhattan":
            path = generator.generate_manhattan_path(src_x, src_y, tgt_x, tgt_y)
        elif routing_style == "l_path":
            path = generator.generate_l_path(src_x, src_y, tgt_x, tgt_y)
        elif routing_style == "smooth":
            path = generator.generate_smooth_path(src_x, src_y, tgt_x, tgt_y)
        else:  # straight
            path = generator.generate_straight_line(src_x, src_y, tgt_x, tgt_y)

        wire = {
            'from_component_id': src_device,
            'to_component_id': tgt_device,
            'voltage_level': conn.get('voltage_level', 'UNKNOWN'),
            'wire_color': conn.get('wire_color', ''),
            'path': path
        }
        wires.append(wire)

    return wires
