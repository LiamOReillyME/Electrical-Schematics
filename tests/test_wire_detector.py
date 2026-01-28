"""Tests for visual wire detector and wire path generation."""


from electrical_schematics.pdf.visual_wire_detector import (
    ColorClassifier,
    VisualWire,
    WireColor,
    WirePath,
    WirePathGenerator,
    WirePathTracer,
    WirePoint,
    generate_wire_paths_from_connections,
)


class TestWireColor:
    """Tests for WireColor enum."""

    def test_wire_color_values(self) -> None:
        """Test WireColor enum has expected values."""
        assert WireColor.RED.value == "red"
        assert WireColor.BLUE.value == "blue"
        assert WireColor.GREEN.value == "green"
        assert WireColor.BLACK.value == "black"
        assert WireColor.BROWN.value == "brown"
        assert WireColor.YELLOW_GREEN.value == "yellow_green"


class TestWirePoint:
    """Tests for WirePoint dataclass."""

    def test_wire_point_creation(self) -> None:
        """Test creating WirePoint."""
        point = WirePoint(100.0, 200.0)
        assert point.x == 100.0
        assert point.y == 200.0

    def test_wire_point_distance(self) -> None:
        """Test distance calculation between points."""
        p1 = WirePoint(0.0, 0.0)
        p2 = WirePoint(3.0, 4.0)
        assert p1.distance_to(p2) == 5.0

    def test_wire_point_distance_same(self) -> None:
        """Test distance to same point is zero."""
        p = WirePoint(10.0, 20.0)
        assert p.distance_to(p) == 0.0

    def test_wire_point_equality(self) -> None:
        """Test WirePoint equality with tolerance."""
        p1 = WirePoint(100.0, 200.0)
        p2 = WirePoint(100.05, 200.04)
        # Should be equal due to rounding tolerance
        assert p1 == p2

    def test_wire_point_inequality(self) -> None:
        """Test WirePoint inequality for different points."""
        p1 = WirePoint(100.0, 200.0)
        p2 = WirePoint(100.2, 200.0)
        # Should not be equal - difference > 0.1
        assert p1 != p2

    def test_wire_point_hash(self) -> None:
        """Test WirePoint hashing for dict/set usage."""
        p1 = WirePoint(100.0, 200.0)
        p2 = WirePoint(100.05, 200.04)
        # Same hash due to rounding
        assert hash(p1) == hash(p2)

        # Can be used in set
        points = {p1, p2}
        assert len(points) == 1


class TestVisualWire:
    """Tests for VisualWire dataclass."""

    def test_visual_wire_creation(self) -> None:
        """Test creating VisualWire."""
        wire = VisualWire(
            page_number=0,
            start_x=10.0,
            start_y=20.0,
            end_x=100.0,
            end_y=20.0,
            color=WireColor.RED,
            rgb=(1.0, 0.0, 0.0),
            thickness=1.5
        )
        assert wire.page_number == 0
        assert wire.color == WireColor.RED
        assert wire.thickness == 1.5

    def test_visual_wire_voltage_type_red(self) -> None:
        """Test voltage type inference for red wire."""
        wire = VisualWire(
            page_number=0, start_x=0, start_y=0, end_x=10, end_y=0,
            color=WireColor.RED, rgb=(1.0, 0.0, 0.0), thickness=1.0
        )
        assert wire.voltage_type == "24VDC"

    def test_visual_wire_voltage_type_blue(self) -> None:
        """Test voltage type inference for blue wire."""
        wire = VisualWire(
            page_number=0, start_x=0, start_y=0, end_x=10, end_y=0,
            color=WireColor.BLUE, rgb=(0.0, 0.0, 1.0), thickness=1.0
        )
        assert wire.voltage_type == "0V"

    def test_visual_wire_voltage_type_green(self) -> None:
        """Test voltage type inference for green PE wire."""
        wire = VisualWire(
            page_number=0, start_x=0, start_y=0, end_x=10, end_y=0,
            color=WireColor.GREEN, rgb=(0.0, 1.0, 0.0), thickness=1.0
        )
        assert wire.voltage_type == "PE"

    def test_visual_wire_voltage_type_black(self) -> None:
        """Test voltage type inference for black wire (400VAC)."""
        wire = VisualWire(
            page_number=0, start_x=0, start_y=0, end_x=10, end_y=0,
            color=WireColor.BLACK, rgb=(0.0, 0.0, 0.0), thickness=1.0
        )
        assert wire.voltage_type == "400VAC"

    def test_visual_wire_length(self) -> None:
        """Test wire length calculation."""
        wire = VisualWire(
            page_number=0, start_x=0, start_y=0, end_x=30, end_y=40,
            color=WireColor.RED, rgb=(1.0, 0.0, 0.0), thickness=1.0
        )
        assert wire.length == 50.0  # 3-4-5 triangle scaled by 10

    def test_visual_wire_horizontal(self) -> None:
        """Test horizontal wire detection."""
        wire = VisualWire(
            page_number=0, start_x=0, start_y=50, end_x=100, end_y=50,
            color=WireColor.RED, rgb=(1.0, 0.0, 0.0), thickness=1.0
        )
        assert wire.is_horizontal
        assert not wire.is_vertical

    def test_visual_wire_vertical(self) -> None:
        """Test vertical wire detection."""
        wire = VisualWire(
            page_number=0, start_x=50, start_y=0, end_x=50, end_y=100,
            color=WireColor.RED, rgb=(1.0, 0.0, 0.0), thickness=1.0
        )
        assert wire.is_vertical
        assert not wire.is_horizontal

    def test_visual_wire_diagonal(self) -> None:
        """Test diagonal wire is neither horizontal nor vertical."""
        wire = VisualWire(
            page_number=0, start_x=0, start_y=0, end_x=100, end_y=100,
            color=WireColor.RED, rgb=(1.0, 0.0, 0.0), thickness=1.0
        )
        assert not wire.is_horizontal
        assert not wire.is_vertical


class TestColorClassifier:
    """Tests for ColorClassifier."""

    def test_classify_pure_red(self) -> None:
        """Test classification of pure red."""
        result = ColorClassifier.classify((1.0, 0.0, 0.0))
        assert result == WireColor.RED

    def test_classify_red_relaxed(self) -> None:
        """Test classification of red with relaxed thresholds."""
        # Not pure red but should still be classified as red
        result = ColorClassifier.classify((0.85, 0.15, 0.1))
        assert result == WireColor.RED

    def test_classify_pure_blue(self) -> None:
        """Test classification of pure blue."""
        result = ColorClassifier.classify((0.0, 0.0, 1.0))
        assert result == WireColor.BLUE

    def test_classify_blue_relaxed(self) -> None:
        """Test classification of blue with relaxed thresholds."""
        result = ColorClassifier.classify((0.1, 0.2, 0.8))
        assert result == WireColor.BLUE

    def test_classify_pure_green(self) -> None:
        """Test classification of pure green."""
        result = ColorClassifier.classify((0.0, 1.0, 0.0))
        assert result == WireColor.GREEN

    def test_classify_green_relaxed(self) -> None:
        """Test classification of green with relaxed thresholds."""
        result = ColorClassifier.classify((0.1, 0.75, 0.2))
        assert result == WireColor.GREEN

    def test_classify_black(self) -> None:
        """Test classification of black."""
        result = ColorClassifier.classify((0.05, 0.05, 0.05))
        assert result == WireColor.BLACK

    def test_classify_gray(self) -> None:
        """Test classification of gray."""
        result = ColorClassifier.classify((0.5, 0.5, 0.5))
        assert result == WireColor.GRAY

    def test_classify_white(self) -> None:
        """Test classification of white."""
        result = ColorClassifier.classify((0.95, 0.95, 0.95))
        assert result == WireColor.WHITE

    def test_classify_orange(self) -> None:
        """Test classification of orange."""
        # Orange: hue ~30 degrees
        result = ColorClassifier.classify((1.0, 0.5, 0.0))
        assert result == WireColor.ORANGE

    def test_hsv_conversion(self) -> None:
        """Test RGB to HSV conversion."""
        # Red should have hue near 0 or 360
        h, s, v = ColorClassifier.rgb_to_hsv(1.0, 0.0, 0.0)
        assert h == 0.0
        assert s == 1.0
        assert v == 1.0

        # Blue should have hue ~240
        h, s, v = ColorClassifier.rgb_to_hsv(0.0, 0.0, 1.0)
        assert h == 240.0

        # Green should have hue ~120
        h, s, v = ColorClassifier.rgb_to_hsv(0.0, 1.0, 0.0)
        assert h == 120.0


class TestWirePathTracer:
    """Tests for WirePathTracer."""

    def _create_segment(self, x1: float, y1: float, x2: float, y2: float,
                       color: WireColor = WireColor.RED) -> VisualWire:
        """Helper to create wire segment."""
        return VisualWire(
            page_number=0, start_x=x1, start_y=y1, end_x=x2, end_y=y2,
            color=color, rgb=(1.0, 0.0, 0.0), thickness=1.0
        )

    def test_trace_single_segment(self) -> None:
        """Test tracing single segment returns single path."""
        tracer = WirePathTracer()
        segments = [self._create_segment(0, 0, 100, 0)]

        paths = tracer.trace_paths(segments)

        assert len(paths) == 1
        assert len(paths[0].segments) == 1

    def test_trace_connected_segments(self) -> None:
        """Test tracing two connected segments."""
        tracer = WirePathTracer()
        segments = [
            self._create_segment(0, 0, 100, 0),
            self._create_segment(100, 0, 100, 100)
        ]

        paths = tracer.trace_paths(segments)

        # Should merge into one path
        assert len(paths) == 1
        assert len(paths[0].segments) == 2

    def test_trace_disconnected_segments(self) -> None:
        """Test tracing disconnected segments creates separate paths."""
        tracer = WirePathTracer()
        segments = [
            self._create_segment(0, 0, 50, 0),
            self._create_segment(200, 0, 250, 0)  # Far away
        ]

        paths = tracer.trace_paths(segments)

        # Should create two separate paths
        assert len(paths) == 2

    def test_trace_with_tolerance(self) -> None:
        """Test tracing connects nearby segments within tolerance."""
        tracer = WirePathTracer(tolerance=10.0)
        segments = [
            self._create_segment(0, 0, 100, 0),
            self._create_segment(105, 0, 200, 0)  # 5 units gap, within tolerance
        ]

        paths = tracer.trace_paths(segments)

        # Should connect due to tolerance
        assert len(paths) == 1

    def test_trace_different_colors_separate(self) -> None:
        """Test that different colors create separate paths."""
        tracer = WirePathTracer()
        segments = [
            self._create_segment(0, 0, 100, 0, WireColor.RED),
            self._create_segment(100, 0, 200, 0, WireColor.BLUE)
        ]

        paths = tracer.trace_paths(segments)

        # Different colors should stay separate
        assert len(paths) == 2

    def test_find_junctions(self) -> None:
        """Test finding junction points."""
        tracer = WirePathTracer()
        # Create T-junction
        segments = [
            self._create_segment(0, 50, 100, 50),    # Horizontal
            self._create_segment(100, 50, 200, 50),  # Horizontal continuation
            self._create_segment(100, 50, 100, 100)  # Vertical branch
        ]

        junctions = tracer.find_junctions(segments)

        # Point (100, 50) is a junction
        assert len(junctions) == 1
        assert junctions[0].x == 100.0
        assert junctions[0].y == 50.0

    def test_empty_segments(self) -> None:
        """Test tracing empty segment list."""
        tracer = WirePathTracer()
        paths = tracer.trace_paths([])
        assert paths == []


class TestWirePathGenerator:
    """Tests for WirePathGenerator."""

    def test_manhattan_path_horizontal_first(self) -> None:
        """Test Manhattan path generation."""
        path = WirePathGenerator.generate_manhattan_path(0, 0, 100, 100)

        # Should have 4 points: start, mid-horizontal, mid-vertical, end
        assert len(path) == 4
        assert path[0].x == 0 and path[0].y == 0
        assert path[-1].x == 100 and path[-1].y == 100

        # Check path is orthogonal
        for i in range(len(path) - 1):
            p1, p2 = path[i], path[i + 1]
            # Either dx or dy should be 0
            assert p1.x == p2.x or p1.y == p2.y

    def test_l_path_horizontal_first(self) -> None:
        """Test L-path generation (horizontal first)."""
        path = WirePathGenerator.generate_l_path(0, 0, 100, 100, horizontal_first=True)

        assert len(path) == 3
        assert path[0].x == 0 and path[0].y == 0
        assert path[1].x == 100 and path[1].y == 0  # Corner
        assert path[2].x == 100 and path[2].y == 100

    def test_l_path_vertical_first(self) -> None:
        """Test L-path generation (vertical first)."""
        path = WirePathGenerator.generate_l_path(0, 0, 100, 100, horizontal_first=False)

        assert len(path) == 3
        assert path[0].x == 0 and path[0].y == 0
        assert path[1].x == 0 and path[1].y == 100  # Corner
        assert path[2].x == 100 and path[2].y == 100

    def test_straight_line(self) -> None:
        """Test straight line generation."""
        path = WirePathGenerator.generate_straight_line(0, 0, 100, 100)

        assert len(path) == 2
        assert path[0].x == 0 and path[0].y == 0
        assert path[1].x == 100 and path[1].y == 100

    def test_smooth_path(self) -> None:
        """Test smooth bezier path generation."""
        path = WirePathGenerator.generate_smooth_path(0, 0, 100, 0, segments=10)

        # Should have 11 points (0 to 10 inclusive)
        assert len(path) == 11
        assert path[0].x == 0 and path[0].y == 0
        assert path[-1].x == 100 and path[-1].y == 0

    def test_smooth_path_degenerate(self) -> None:
        """Test smooth path with same start and end."""
        path = WirePathGenerator.generate_smooth_path(50, 50, 50, 50)

        # Should still return valid path
        assert len(path) == 2


class TestLineClassifier:
    """Tests for LineClassifier (wire discrimination)."""

    def test_border_detection_top(self) -> None:
        """Test detection of top border line."""
        from electrical_schematics.pdf.visual_wire_detector import LineClassifier, LineType

        classifier = LineClassifier(page_width=600, page_height=800)

        # Top border line
        line = VisualWire(
            page_number=0, start_x=0, start_y=5, end_x=500, end_y=5,
            color=WireColor.BLACK, rgb=(0.0, 0.0, 0.0), thickness=1.0
        )

        assert classifier._is_border(line)

    def test_border_detection_bottom(self) -> None:
        """Test detection of bottom border line."""
        from electrical_schematics.pdf.visual_wire_detector import LineClassifier

        classifier = LineClassifier(page_width=600, page_height=800)

        # Bottom border line
        line = VisualWire(
            page_number=0, start_x=0, start_y=790, end_x=500, end_y=790,
            color=WireColor.BLACK, rgb=(0.0, 0.0, 0.0), thickness=1.0
        )

        assert classifier._is_border(line)

    def test_title_block_detection(self) -> None:
        """Test detection of title block lines."""
        from electrical_schematics.pdf.visual_wire_detector import LineClassifier

        classifier = LineClassifier(page_width=600, page_height=800)

        # Title block line (bottom 15% of page)
        line = VisualWire(
            page_number=0, start_x=400, start_y=700, end_x=500, end_y=700,
            color=WireColor.BLACK, rgb=(0.0, 0.0, 0.0), thickness=1.0
        )

        assert classifier._is_title_block(line)

    def test_header_detection(self) -> None:
        """Test detection of header region lines."""
        from electrical_schematics.pdf.visual_wire_detector import LineClassifier

        classifier = LineClassifier(page_width=600, page_height=800)

        # Header line (top 20 points)
        line = VisualWire(
            page_number=0, start_x=100, start_y=10, end_x=100, end_y=15,
            color=WireColor.BLACK, rgb=(0.0, 0.0, 0.0), thickness=1.0
        )

        assert classifier._is_title_block(line)

    def test_wire_characteristics_colored_long(self) -> None:
        """Test wire detection for long colored line."""
        from electrical_schematics.pdf.visual_wire_detector import LineClassifier

        classifier = LineClassifier(page_width=600, page_height=800)

        # Long red wire
        line = VisualWire(
            page_number=0, start_x=100, start_y=200, end_x=400, end_y=200,
            color=WireColor.RED, rgb=(1.0, 0.0, 0.0), thickness=1.5
        )

        assert classifier._has_wire_characteristics(line)

    def test_wire_characteristics_colored_short(self) -> None:
        """Test wire detection for short colored diagonal."""
        from electrical_schematics.pdf.visual_wire_detector import LineClassifier

        classifier = LineClassifier(page_width=600, page_height=800)

        # Short blue diagonal
        line = VisualWire(
            page_number=0, start_x=100, start_y=200, end_x=110, end_y=210,
            color=WireColor.BLUE, rgb=(0.0, 0.0, 1.0), thickness=1.0
        )

        assert classifier._has_wire_characteristics(line)

    def test_component_outline_detection(self) -> None:
        """Test detection of component outline."""
        from electrical_schematics.pdf.visual_wire_detector import LineClassifier

        classifier = LineClassifier(page_width=600, page_height=800)

        # Create a small box shape
        lines = [
            VisualWire(0, 100, 100, 120, 100, WireColor.BLACK, (0,0,0), 1),
            VisualWire(0, 120, 100, 120, 120, WireColor.BLACK, (0,0,0), 1),
            VisualWire(0, 120, 120, 100, 120, WireColor.BLACK, (0,0,0), 1),
            VisualWire(0, 100, 120, 100, 100, WireColor.BLACK, (0,0,0), 1),
        ]

        # First line should be classified as component outline
        assert classifier._is_component_outline(lines[0], lines)


class TestVisualWireDetectorWithClassification:
    """Tests for wire detection with classification enabled."""

    def test_detect_wires_only_filters_borders(self) -> None:
        """Test that detect_wires_only filters out border lines."""
        # This would require a mock PDF with known content
        # Placeholder for integration test
        pass

    def test_classify_all_lines_returns_dict(self) -> None:
        """Test that classify_all_lines returns classification dict."""
        # Placeholder for integration test with mock PDF
        pass


class TestWirePath:
    """Tests for WirePath dataclass."""

    def _create_segment(self, x1: float, y1: float, x2: float, y2: float) -> VisualWire:
        """Helper to create wire segment."""
        return VisualWire(
            page_number=0, start_x=x1, start_y=y1, end_x=x2, end_y=y2,
            color=WireColor.RED, rgb=(1.0, 0.0, 0.0), thickness=1.0
        )

    def test_wire_path_total_length(self) -> None:
        """Test total length calculation."""
        path = WirePath(
            segments=[
                self._create_segment(0, 0, 100, 0),  # Length 100
                self._create_segment(100, 0, 100, 50)  # Length 50
            ],
            color=WireColor.RED,
            page_number=0
        )

        assert path.total_length == 150.0

    def test_wire_path_points(self) -> None:
        """Test point extraction from path."""
        path = WirePath(
            segments=[
                self._create_segment(0, 0, 100, 0),
                self._create_segment(100, 0, 100, 50)
            ],
            color=WireColor.RED,
            page_number=0
        )

        points = path.points
        assert len(points) == 3  # start + 2 end points
        assert points[0].x == 0 and points[0].y == 0
        assert points[1].x == 100 and points[1].y == 0
        assert points[2].x == 100 and points[2].y == 50

    def test_wire_path_voltage_type(self) -> None:
        """Test voltage type from path."""
        path = WirePath(
            segments=[self._create_segment(0, 0, 100, 0)],
            color=WireColor.RED,
            page_number=0
        )

        assert path.voltage_type == "24VDC"

    def test_empty_wire_path(self) -> None:
        """Test empty path handling."""
        path = WirePath()

        assert path.total_length == 0.0
        assert path.points == []
        assert path.voltage_type == "UNKNOWN"


class TestGenerateWirePathsFromConnections:
    """Tests for the generate_wire_paths_from_connections function."""

    def test_generate_manhattan_paths(self) -> None:
        """Test generating Manhattan paths from connections."""
        connections = [
            {
                'source_device': 'K1',
                'target_device': 'M1',
                'voltage_level': '24VDC',
                'wire_color': 'RD'
            }
        ]

        positions = {
            'K1': {'x': 0, 'y': 0, 'width': 40, 'height': 30},
            'M1': {'x': 200, 'y': 100, 'width': 40, 'height': 30}
        }

        wires = generate_wire_paths_from_connections(
            connections, positions, routing_style="manhattan"
        )

        assert len(wires) == 1
        assert wires[0]['from_component_id'] == 'K1'
        assert wires[0]['to_component_id'] == 'M1'
        assert wires[0]['voltage_level'] == '24VDC'
        assert len(wires[0]['path']) == 4  # Manhattan has 4 points

    def test_generate_straight_paths(self) -> None:
        """Test generating straight-line paths."""
        connections = [
            {'source_device': 'A', 'target_device': 'B'}
        ]

        positions = {
            'A': {'x': 0, 'y': 0, 'width': 20, 'height': 20},
            'B': {'x': 100, 'y': 100, 'width': 20, 'height': 20}
        }

        wires = generate_wire_paths_from_connections(
            connections, positions, routing_style="straight"
        )

        assert len(wires) == 1
        assert len(wires[0]['path']) == 2

    def test_missing_position_skipped(self) -> None:
        """Test that connections with missing positions are skipped."""
        connections = [
            {'source_device': 'A', 'target_device': 'B'},
            {'source_device': 'A', 'target_device': 'C'}  # C has no position
        ]

        positions = {
            'A': {'x': 0, 'y': 0, 'width': 20, 'height': 20},
            'B': {'x': 100, 'y': 0, 'width': 20, 'height': 20}
            # C is missing
        }

        wires = generate_wire_paths_from_connections(connections, positions)

        # Only A->B should have a path
        assert len(wires) == 1
        assert wires[0]['to_component_id'] == 'B'

    def test_empty_connections(self) -> None:
        """Test with empty connection list."""
        wires = generate_wire_paths_from_connections([], {})
        assert wires == []

    def test_center_calculation(self) -> None:
        """Test that paths use component centers."""
        connections = [{'source_device': 'A', 'target_device': 'B'}]

        positions = {
            'A': {'x': 0, 'y': 0, 'width': 100, 'height': 100},
            'B': {'x': 200, 'y': 0, 'width': 100, 'height': 100}
        }

        wires = generate_wire_paths_from_connections(
            connections, positions, routing_style="straight"
        )

        path = wires[0]['path']
        # Start should be center of A: (0+50, 0+50) = (50, 50)
        assert path[0].x == 50.0
        assert path[0].y == 50.0
        # End should be center of B: (200+50, 0+50) = (250, 50)
        assert path[1].x == 250.0
        assert path[1].y == 50.0
