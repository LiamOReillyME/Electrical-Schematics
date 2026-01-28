"""Automatic loading and analysis of electrical diagrams."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz

from electrical_schematics.models import IndustrialComponent, IndustrialComponentType, WiringDiagram
from electrical_schematics.models.wire import Wire
from electrical_schematics.models.wire import WirePoint as ModelWirePoint
from electrical_schematics.pdf.drawer_parser import CableConnection, DrawerParser
from electrical_schematics.pdf.drawer_to_model import DrawerToModelConverter
from electrical_schematics.pdf.exact_parts_parser import parse_parts_list
from electrical_schematics.pdf.parts_list_parser import PartsListParser
from electrical_schematics.pdf.visual_wire_detector import (
    VisualWireDetector,
    WirePathGenerator,
    generate_wire_paths_from_connections,
)


class DiagramAutoLoader:
    """Automatically loads and analyzes electrical diagrams."""

    @staticmethod
    def detect_format(pdf_path: Path) -> str:
        """Detect the format of a PDF diagram.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Format identifier: "drawer", "manual", or "unknown"
        """
        doc = fitz.open(pdf_path)

        # Check for DRAWER format indicators
        # DRAWER diagrams have "Device tag" and "Cable diagram" sections
        has_device_tag = False
        has_cable_diagram = False

        for page_num in range(min(30, len(doc))):
            page = doc[page_num]
            text = page.get_text()

            if "Device tag" in text or "Betriebsmittelkennzeichen" in text:
                has_device_tag = True

            if "Cable diagram" in text or "Kabelplan" in text:
                has_cable_diagram = True

            if has_device_tag and has_cable_diagram:
                doc.close()
                return "drawer"

        doc.close()

        # If not DRAWER format, assume manual annotation needed
        return "manual"

    @staticmethod
    def load_diagram(
        pdf_path: Path,
        auto_position: bool = True
    ) -> Tuple[Optional[WiringDiagram], str]:
        """Load and parse a diagram, auto-detecting format.

        Tries multiple strategies in priority order:
        1. DRAWER format (provides components + wires + cable routing)
        2. Generic parts list extraction (provides components only)
        3. Empty diagram for manual annotation

        DRAWER format is prioritized because it provides complete wiring
        information from cable routing tables, which is essential for
        simulation and visualization.

        Args:
            pdf_path: Path to PDF file
            auto_position: If True, automatically find component positions in PDF

        Returns:
            Tuple of (WiringDiagram or None, format_type)
            format_type can be: "drawer", "parts_list", or "manual"
        """
        # Strategy 1: Check for DRAWER format FIRST (highest priority)
        # DRAWER format provides both components AND wires from cable routing tables
        format_type = DiagramAutoLoader.detect_format(pdf_path)
        if format_type == "drawer":
            return DiagramAutoLoader._load_drawer(pdf_path, auto_position), "drawer"

        # Strategy 2: Try generic parts list extraction
        # This only provides components, no wiring information
        parts_diagram = DiagramAutoLoader._load_from_parts_list(pdf_path, auto_position)
        if parts_diagram and len(parts_diagram.components) > 0:
            return parts_diagram, "parts_list"

        # Strategy 3: Return empty diagram for manual annotation
        empty_diagram = WiringDiagram(
            name=pdf_path.stem,
            pdf_path=pdf_path
        )
        return empty_diagram, "manual"

    @staticmethod
    def _load_from_parts_list(
        pdf_path: Path,
        auto_position: bool = True
    ) -> Optional[WiringDiagram]:
        """Load diagram from parts list using exact column coordinates.

        Args:
            pdf_path: Path to PDF file
            auto_position: If True, find component positions in schematic pages

        Returns:
            WiringDiagram with components from parts list, or None if no parts list found
        """
        try:
            # Try exact parser first (with precise column coordinates)
            parts_data = parse_parts_list(pdf_path)

            if not parts_data:
                # Fall back to generic parser if exact parser fails
                parser = PartsListParser(pdf_path)
                parts_components = parser.parse_parts_list()
                parser.close()

                if not parts_components:
                    return None

                # Use generic parser data
                components = []
                for parts_comp in parts_components:
                    comp_type = DiagramAutoLoader._infer_component_type(parts_comp.designation)

                    component = IndustrialComponent(
                        id=parts_comp.designation,
                        type=comp_type,
                        designation=parts_comp.designation,
                        description=parts_comp.description,
                        voltage_rating=parts_comp.voltage_rating,
                        x=0.0,
                        y=0.0,
                        width=40.0,
                        height=30.0
                    )
                    components.append(component)
            else:
                # Use exact parser data (preferred)
                components = []
                for part_data in parts_data:
                    # Extract voltage from technical_data field
                    voltage = DiagramAutoLoader._extract_voltage(part_data.technical_data)

                    # Determine component type from device_tag
                    comp_type = DiagramAutoLoader._infer_component_type(part_data.device_tag)

                    # Create component with exact parser data
                    # Note: PartData.designation is the description field
                    component = IndustrialComponent(
                        id=part_data.device_tag,
                        type=comp_type,
                        designation=part_data.device_tag,
                        description=part_data.designation,
                        voltage_rating=voltage,
                        x=0.0,  # Will be populated by position finder
                        y=0.0,
                        width=40.0,
                        height=30.0
                    )

                    # Store additional data in metadata if available
                    if hasattr(component, 'metadata'):
                        component.metadata = {
                            'technical_data': part_data.technical_data,
                            'part_number': part_data.type_designation
                        }

                    components.append(component)

            # Create diagram
            diagram = WiringDiagram(
                name=pdf_path.stem,
                pdf_path=pdf_path,
                components=components,
                wires=[]  # No wire info from parts list
            )

            # Auto-populate component positions from PDF schematic pages
            if auto_position and components:
                DiagramAutoLoader._populate_component_positions(diagram, pdf_path)

            return diagram

        except Exception as e:
            print(f"Failed to load from parts list: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def _populate_component_positions(
        diagram: WiringDiagram,
        pdf_path: Path
    ) -> Dict[str, bool]:
        """Populate component positions by finding device tags in PDF.

        Searches ALL pages (using title-block-based page classification to
        skip non-schematic pages) and stores positions for every page where
        a component tag is found. This enables multi-page overlay support.

        Args:
            diagram: WiringDiagram with components to position
            pdf_path: Path to PDF file

        Returns:
            Dictionary mapping component IDs to success status
        """
        from electrical_schematics.pdf.component_position_finder import ComponentPositionFinder

        device_tags = [comp.designation for comp in diagram.components]
        if not device_tags:
            return {}

        results: Dict[str, bool] = {}

        try:
            with ComponentPositionFinder(pdf_path) as finder:
                # Search ALL pages -- page classification handles skip logic
                position_result = finder.find_positions(
                    device_tags, search_all_pages=True
                )

                for component in diagram.components:
                    tag = component.designation

                    if tag in position_result.positions:
                        pos = position_result.positions[tag]
                        # Set primary position and page
                        component.x = pos.x
                        component.y = pos.y
                        component.width = max(pos.width, 40.0)
                        component.height = max(pos.height, 30.0)
                        component.page = pos.page  # Store the page number

                        # Also add to page_positions for multi-page support
                        component.add_page_position(
                            page=pos.page,
                            x=pos.x,
                            y=pos.y,
                            width=max(pos.width, 40.0),
                            height=max(pos.height, 30.0),
                            confidence=pos.confidence
                        )
                        results[tag] = True
                    else:
                        results[tag] = False

                    # Handle components that appear on multiple pages
                    if tag in position_result.ambiguous_matches:
                        for pos in position_result.ambiguous_matches[tag]:
                            # Add all positions found for this component
                            component.add_page_position(
                                page=pos.page,
                                x=pos.x,
                                y=pos.y,
                                width=max(pos.width, 40.0),
                                height=max(pos.height, 30.0),
                                confidence=pos.confidence
                            )
                        # If we have positions from ambiguous matches but not
                        # from primary positions, mark as found
                        if tag not in position_result.positions:
                            best = max(
                                position_result.ambiguous_matches[tag],
                                key=lambda p: p.confidence
                            )
                            component.x = best.x
                            component.y = best.y
                            component.width = max(best.width, 40.0)
                            component.height = max(best.height, 30.0)
                            component.page = best.page
                            results[tag] = True

        except Exception as e:
            print(f"Warning: Failed to find component positions: {e}")
            for tag in device_tags:
                results[tag] = False

        return results

    @staticmethod
    def _extract_voltage(technical_data: str) -> str:
        """Extract voltage rating from technical data string.

        Args:
            technical_data: Technical specifications string

        Returns:
            Voltage string (e.g., "24VDC", "230VAC") or empty string
        """
        if not technical_data:
            return ""

        # Common voltage patterns
        voltage_patterns = [
            r'(\d+\s*V\s*(?:DC|AC))',  # 24VDC, 230VAC, 24 V DC
            r'(\d+\s*V)',  # 24V
            r'(DC\s*\d+\s*V)',  # DC 24V
            r'(AC\s*\d+\s*V)',  # AC 230V
        ]

        for pattern in voltage_patterns:
            match = re.search(pattern, technical_data, re.IGNORECASE)
            if match:
                voltage = match.group(1)
                # Normalize format (remove spaces, uppercase)
                voltage = voltage.replace(' ', '').upper()
                return voltage

        return ""

    @staticmethod
    def _infer_component_type(designation: str) -> IndustrialComponentType:
        """Infer component type from designation.

        Args:
            designation: Component designation (e.g., K1, S1, M1)

        Returns:
            IndustrialComponentType
        """
        # Common designation prefixes
        prefix = designation.lstrip('+-').rstrip('0123456789')

        type_map = {
            'K': IndustrialComponentType.CONTACTOR,
            'Q': IndustrialComponentType.CIRCUIT_BREAKER,
            'F': IndustrialComponentType.FUSE,
            'S': IndustrialComponentType.PHOTOELECTRIC_SENSOR,
            'B': IndustrialComponentType.PROXIMITY_SENSOR,  # Often used for proximity sensors
            'M': IndustrialComponentType.MOTOR,
            'A': IndustrialComponentType.PLC_INPUT,  # Often used for PLCs/controllers
            'P': IndustrialComponentType.POWER_24VDC,
            'T': IndustrialComponentType.OTHER,  # Transformer - no specific type available
            'R': IndustrialComponentType.RELAY,
            'L': IndustrialComponentType.INDICATOR_LIGHT,  # Light curtain - closest match
            'E': IndustrialComponentType.EMERGENCY_STOP,
            'X': IndustrialComponentType.TERMINAL_BLOCK,
        }

        return type_map.get(prefix, IndustrialComponentType.OTHER)

    @staticmethod
    def _load_drawer(pdf_path: Path, auto_position: bool = True) -> WiringDiagram:
        """Load a DRAWER format diagram with full analysis.

        Args:
            pdf_path: Path to DRAWER PDF
            auto_position: If True, automatically find component positions

        Returns:
            Fully populated WiringDiagram
        """
        # Parse DRAWER format
        parser = DrawerParser(pdf_path)
        drawer_diagram = parser.parse()

        # Convert to internal model (with auto-positioning)
        wiring_diagram = DrawerToModelConverter.convert(
            drawer_diagram,
            auto_position=auto_position
        )

        # Enhance with automatic analysis
        DrawerToModelConverter.infer_power_sources(wiring_diagram)
        DrawerToModelConverter.identify_sensors(wiring_diagram)

        # Analyze visual wires and cross-reference
        DiagramAutoLoader._analyze_visual_wires(pdf_path, wiring_diagram, drawer_diagram)

        return wiring_diagram

    @staticmethod
    def _analyze_visual_wires(
        pdf_path: Path,
        wiring_diagram: WiringDiagram,
        drawer_diagram
    ) -> None:
        """Analyze visual wire colors and cross-reference with connections.

        Uses enhanced wire detection with HSV color analysis and path tracing.

        Args:
            pdf_path: Path to PDF
            wiring_diagram: WiringDiagram to enhance (modified in place)
            drawer_diagram: Original DRAWER diagram for reference
        """
        doc = fitz.open(pdf_path)
        detector = VisualWireDetector(doc)

        # Track wire statistics across pages
        total_stats = {
            'total_wires': 0,
            'color_counts': {},
            'traced_paths': 0
        }

        # Analyze schematic pages (typically before cable diagrams)
        for page_num in range(min(25, len(doc))):
            # Get basic wire detection
            visual_wires = detector.detect_wires(page_num)

            # Also trace complete paths for better understanding
            wire_paths = detector.detect_and_trace_paths(page_num)

            # Update statistics
            stats = detector.get_wire_statistics(page_num)
            total_stats['total_wires'] += stats['total_count']
            total_stats['traced_paths'] += len(wire_paths)

            for color, count in stats['color_distribution'].items():
                total_stats['color_counts'][color] = (
                    total_stats['color_counts'].get(color, 0) + count
                )

            # Cross-reference visual wires with logical connections
            for visual_wire in visual_wires:
                matched_wire = DiagramAutoLoader._match_visual_to_logical(
                    visual_wire,
                    wiring_diagram,
                    page_num
                )

                if matched_wire:
                    # Update wire voltage based on visual color
                    if visual_wire.voltage_type != "UNKNOWN":
                        matched_wire.voltage_level = visual_wire.voltage_type
                        matched_wire.is_energized = (visual_wire.voltage_type == "24VDC")

                    # Add visual path data if not already present
                    if not matched_wire.path:
                        matched_wire.path = [
                            ModelWirePoint(visual_wire.start_x, visual_wire.start_y),
                            ModelWirePoint(visual_wire.end_x, visual_wire.end_y)
                        ]

        doc.close()

        # Store statistics in diagram metadata
        wiring_diagram.metadata['wire_detection_stats'] = total_stats

    @staticmethod
    def _match_visual_to_logical(
        visual_wire,
        wiring_diagram: WiringDiagram,
        page_num: int
    ) -> Optional:
        """Match a visual wire to a logical connection.

        Uses improved heuristics with extended color mapping.

        Args:
            visual_wire: VisualWire detected from PDF
            wiring_diagram: WiringDiagram with logical connections
            page_num: Page number

        Returns:
            Matched Wire object or None
        """
        # Extended color to voltage mapping
        color_to_voltage = {
            "red": "24VDC",
            "brown": "24VDC",
            "orange": "24VDC",
            "blue": "0V",
            "green": "PE",
            "yellow_green": "PE",
            "black": "400VAC",
        }

        voltage = color_to_voltage.get(visual_wire.color.value)

        if voltage:
            # Find wires with matching or unknown voltage
            for wire in wiring_diagram.wires:
                if wire.voltage_level == voltage or wire.voltage_level == "UNKNOWN":
                    return wire

        return None

    @staticmethod
    def generate_wire_paths(
        wiring_diagram: WiringDiagram,
        routing_style: str = "manhattan"
    ) -> None:
        """Generate visual wire paths for all connections.

        Uses component positions to create visual wire routing paths.

        Args:
            wiring_diagram: WiringDiagram to update (modified in place)
            routing_style: "manhattan", "l_path", "straight", or "smooth"
        """
        # Build component position dictionary
        component_positions = {}
        for comp in wiring_diagram.components:
            component_positions[comp.id] = {
                'x': comp.x,
                'y': comp.y,
                'width': comp.width,
                'height': comp.height
            }

        # Build connection list from wires
        connections = []
        for wire in wiring_diagram.wires:
            if wire.from_component_id and wire.to_component_id:
                connections.append({
                    'source_device': wire.from_component_id,
                    'target_device': wire.to_component_id,
                    'voltage_level': wire.voltage_level or 'UNKNOWN',
                    'wire_color': wire.color or ''
                })

        # Generate paths
        wire_paths = generate_wire_paths_from_connections(
            connections,
            component_positions,
            routing_style
        )

        # Update wire objects with generated paths
        for wire_data in wire_paths:
            # Find corresponding wire
            for wire in wiring_diagram.wires:
                if (wire.from_component_id == wire_data['from_component_id'] and
                    wire.to_component_id == wire_data['to_component_id']):
                    # Convert WirePoint to ModelWirePoint
                    wire.path = [
                        ModelWirePoint(p.x, p.y) for p in wire_data['path']
                    ]
                    break

    @staticmethod
    def generate_wires_from_cable_connections(
        cable_connections: List[CableConnection],
        component_positions: Dict[str, dict],
        routing_style: str = "manhattan"
    ) -> List[Wire]:
        """Generate Wire objects from cable routing table data.

        Creates wires with visual paths based on component positions.

        Args:
            cable_connections: List of CableConnection from DRAWER parser
            component_positions: Dictionary mapping device IDs to position dicts
            routing_style: Routing style for path generation

        Returns:
            List of Wire objects with paths
        """
        wires = []
        generator = WirePathGenerator()

        for i, conn in enumerate(cable_connections):
            # Extract device tags from terminal references
            src_device = DiagramAutoLoader._extract_device_from_terminal(conn.source)
            tgt_device = DiagramAutoLoader._extract_device_from_terminal(conn.target)

            src_pos = component_positions.get(src_device)
            tgt_pos = component_positions.get(tgt_device)

            # Create wire even without positions
            wire = Wire(
                id=f"W{i+1}",
                wire_number=conn.cable_name,
                from_component_id=src_device,
                from_terminal=conn.source,
                to_component_id=tgt_device,
                to_terminal=conn.target,
                color=conn.wire_color,
                voltage_level=DiagramAutoLoader._infer_voltage_from_color(conn.wire_color)
            )

            # Generate path if positions available
            if src_pos and tgt_pos:
                src_x = src_pos.get('x', 0) + src_pos.get('width', 0) / 2
                src_y = src_pos.get('y', 0) + src_pos.get('height', 0) / 2
                tgt_x = tgt_pos.get('x', 0) + tgt_pos.get('width', 0) / 2
                tgt_y = tgt_pos.get('y', 0) + tgt_pos.get('height', 0) / 2

                if routing_style == "manhattan":
                    path_points = generator.generate_manhattan_path(
                        src_x, src_y, tgt_x, tgt_y
                    )
                elif routing_style == "l_path":
                    path_points = generator.generate_l_path(
                        src_x, src_y, tgt_x, tgt_y
                    )
                elif routing_style == "smooth":
                    path_points = generator.generate_smooth_path(
                        src_x, src_y, tgt_x, tgt_y
                    )
                else:
                    path_points = generator.generate_straight_line(
                        src_x, src_y, tgt_x, tgt_y
                    )

                wire.path = [ModelWirePoint(p.x, p.y) for p in path_points]

            wires.append(wire)

        return wires

    @staticmethod
    def _extract_device_from_terminal(terminal_ref: str) -> str:
        """Extract device tag from terminal reference.

        Args:
            terminal_ref: Terminal reference (e.g., "-A1-X5:3")

        Returns:
            Device tag (e.g., "-A1")
        """
        # Match device tag pattern
        match = re.match(r'([+-][A-Z0-9]+(?:-[A-Z0-9]+)?)', terminal_ref)
        if match:
            tag = match.group(1)
            # Remove terminal block suffix if present
            if '-X' in tag:
                tag = tag.split('-X')[0]
            return tag
        return terminal_ref

    @staticmethod
    def _infer_voltage_from_color(wire_color: str) -> str:
        """Infer voltage level from wire color code.

        Uses industrial wire color conventions.

        Args:
            wire_color: Wire color code (e.g., "RD", "BK", "GN")

        Returns:
            Voltage level string
        """
        if not wire_color:
            return 'UNKNOWN'

        # Industrial color codes
        color_map = {
            'RD': '24VDC',    # Red
            'BN': '24VDC',    # Brown
            'OG': '24VDC',    # Orange
            'BU': '0V',       # Blue
            'BK': '400VAC',   # Black
            'GN': 'PE',       # Green
            'GNYE': 'PE',     # Green-Yellow
            'YE': 'PE',       # Yellow
            'WH': 'SIGNAL',   # White
            'GY': 'SIGNAL',   # Gray
        }
        return color_map.get(wire_color.upper(), 'UNKNOWN')

    @staticmethod
    def create_summary(diagram: WiringDiagram) -> str:
        """Create a summary of loaded diagram.

        Args:
            diagram: Loaded WiringDiagram

        Returns:
            Human-readable summary text
        """
        from collections import defaultdict

        summary = f"Loaded: {diagram.name}\n"
        summary += "=" * 60 + "\n\n"

        # Count by voltage
        by_voltage = defaultdict(int)
        for comp in diagram.components:
            by_voltage[comp.voltage_rating] += 1

        summary += "Components by voltage:\n"
        for voltage in sorted(by_voltage.keys()):
            count = by_voltage[voltage]
            summary += f"  {voltage:12s}: {count:3d} devices\n"

        summary += f"\nTotal connections: {len(diagram.wires)}\n"

        # Count by wire voltage
        wire_voltage = defaultdict(int)
        for wire in diagram.wires:
            wire_voltage[wire.voltage_level] += 1

        if wire_voltage:
            summary += "\nConnections by voltage:\n"
            for voltage in sorted(wire_voltage.keys()):
                count = wire_voltage[voltage]
                summary += f"  {voltage:12s}: {count:3d} wires\n"

        # Power sources
        power_sources = diagram.get_power_sources()
        if power_sources:
            summary += f"\nPower sources: {len(power_sources)}\n"
            for ps in power_sources[:3]:
                summary += f"  - {ps.designation} ({ps.voltage_rating})\n"

        # Sensors
        sensors = diagram.get_sensors()
        if sensors:
            summary += f"\nSensors/Switches: {len(sensors)}\n"

        # Position statistics
        positioned = sum(1 for c in diagram.components if c.x != 0.0 or c.y != 0.0)
        if positioned > 0:
            summary += f"\nComponents with positions: {positioned}/{len(diagram.components)}\n"

            # Multi-page statistics
            multi_page = sum(
                1 for c in diagram.components
                if len(c.page_positions) > 1
            )
            if multi_page > 0:
                summary += f"Components on multiple pages: {multi_page}\n"

                # Show page distribution
                page_counts: Dict[int, int] = defaultdict(int)
                for comp in diagram.components:
                    for page_num in comp.get_pages():
                        page_counts[page_num] += 1
                summary += "Components per page:\n"
                for page_num in sorted(page_counts.keys()):
                    summary += f"  Page {page_num:2d}: {page_counts[page_num]:3d} components\n"

        # Wire detection stats if available
        if 'wire_detection_stats' in diagram.metadata:
            stats = diagram.metadata['wire_detection_stats']
            summary += "\nVisual Wire Detection:\n"
            summary += f"  Total wire segments: {stats.get('total_wires', 0)}\n"
            summary += f"  Traced paths: {stats.get('traced_paths', 0)}\n"
            if stats.get('color_counts'):
                summary += "  Color distribution:\n"
                for color, count in sorted(stats['color_counts'].items()):
                    summary += f"    {color}: {count}\n"

        return summary
