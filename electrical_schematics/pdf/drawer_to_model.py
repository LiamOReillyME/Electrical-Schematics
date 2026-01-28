"""Convert DRAWER diagram format to internal application models."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from electrical_schematics.models import (
    IndustrialComponent,
    IndustrialComponentType,
    SensorState,
    Wire,
    WiringDiagram,
)
from electrical_schematics.models.wire import WirePoint
from electrical_schematics.pdf.drawer_parser import (
    CableConnection,
    DeviceInfo,
    DrawerDiagram,
)


class DrawerToModelConverter:
    """Converts DRAWER format to internal application models."""

    @staticmethod
    def convert(
        drawer_diagram: DrawerDiagram,
        auto_position: bool = True
    ) -> WiringDiagram:
        """Convert DRAWER diagram to WiringDiagram.

        Args:
            drawer_diagram: Parsed DRAWER diagram
            auto_position: If True, automatically find component positions in PDF

        Returns:
            WiringDiagram suitable for simulation
        """
        wiring_diagram = WiringDiagram(
            name=drawer_diagram.pdf_path.stem if drawer_diagram.pdf_path else "Diagram",
            pdf_path=drawer_diagram.pdf_path
        )

        # Convert devices
        wiring_diagram.components = DrawerToModelConverter._convert_devices(
            drawer_diagram.devices
        )

        # Convert connections
        wiring_diagram.wires = DrawerToModelConverter._convert_connections(
            drawer_diagram.connections,
            drawer_diagram
        )

        # Auto-populate component positions from PDF
        if auto_position and drawer_diagram.pdf_path:
            DrawerToModelConverter.populate_component_positions(
                wiring_diagram,
                drawer_diagram.pdf_path
            )

            # BUGFIX: Generate wire paths after component positions are known
            # This ensures wires can be rendered in the GUI
            DrawerToModelConverter.generate_wire_paths(wiring_diagram)

        return wiring_diagram

    @staticmethod
    def generate_wire_paths(
        diagram: WiringDiagram,
        routing_style: str = "manhattan"
    ) -> int:
        """Generate visual paths for all wires in the diagram.

        Creates wire paths connecting component positions using the specified
        routing style. Only generates paths for wires where both endpoints
        have known positions.

        Args:
            diagram: WiringDiagram with wires and positioned components
            routing_style: Routing style ("manhattan", "straight", "l_path")

        Returns:
            Number of wires that got paths generated
        """
        generated_count = 0

        # Create component position lookup
        component_positions = {}
        for comp in diagram.components:
            # Check if component has a valid position
            if comp.x != 0 or comp.y != 0 or comp.page_positions:
                # Use primary position
                component_positions[comp.id] = {
                    'x': comp.x,
                    'y': comp.y,
                    'width': comp.width,
                    'height': comp.height,
                    'page': comp.page
                }

        # Generate paths for each wire
        for wire in diagram.wires:
            # Skip if wire already has a path
            if wire.path and len(wire.path) > 0:
                continue

            # Get endpoint positions
            from_pos = component_positions.get(wire.from_component_id)
            to_pos = component_positions.get(wire.to_component_id)

            # Skip if either endpoint is missing
            if not from_pos or not to_pos:
                continue

            # Calculate center points of components
            from_x = from_pos['x'] + from_pos['width'] / 2
            from_y = from_pos['y'] + from_pos['height'] / 2
            to_x = to_pos['x'] + to_pos['width'] / 2
            to_y = to_pos['y'] + to_pos['height'] / 2

            # Generate path based on routing style
            if routing_style == "manhattan":
                wire.path = DrawerToModelConverter._generate_manhattan_path(
                    from_x, from_y, to_x, to_y
                )
            elif routing_style == "l_path":
                wire.path = DrawerToModelConverter._generate_l_path(
                    from_x, from_y, to_x, to_y
                )
            else:  # straight
                wire.path = [
                    WirePoint(from_x, from_y),
                    WirePoint(to_x, to_y)
                ]

            generated_count += 1

        return generated_count

    @staticmethod
    def _generate_manhattan_path(
        x1: float, y1: float,
        x2: float, y2: float
    ) -> List[WirePoint]:
        """Generate Manhattan (orthogonal) path between two points.

        Args:
            x1, y1: Start point
            x2, y2: End point

        Returns:
            List of WirePoint forming Manhattan path
        """
        # Calculate midpoint
        mid_x = (x1 + x2) / 2

        return [
            WirePoint(x1, y1),       # Start
            WirePoint(mid_x, y1),    # Horizontal segment
            WirePoint(mid_x, y2),    # Vertical segment
            WirePoint(x2, y2)        # End
        ]

    @staticmethod
    def _generate_l_path(
        x1: float, y1: float,
        x2: float, y2: float
    ) -> List[WirePoint]:
        """Generate L-shaped path between two points.

        Args:
            x1, y1: Start point
            x2, y2: End point

        Returns:
            List of WirePoint forming L-shaped path
        """
        # Choose L-bend direction based on relative positions
        if abs(x2 - x1) > abs(y2 - y1):
            # Horizontal-first L
            return [
                WirePoint(x1, y1),
                WirePoint(x2, y1),
                WirePoint(x2, y2)
            ]
        else:
            # Vertical-first L
            return [
                WirePoint(x1, y1),
                WirePoint(x1, y2),
                WirePoint(x2, y2)
            ]

    @staticmethod
    def populate_component_positions(
        diagram: WiringDiagram,
        pdf_path: Path,
        schematic_pages: Optional[Tuple[int, int]] = None
    ) -> Dict[str, bool]:
        """Populate component positions by finding device tags in PDF.

        Searches the PDF schematic pages for device tag text and updates
        component x, y, width, height, and page fields.

        Args:
            diagram: WiringDiagram with components to position
            pdf_path: Path to PDF file
            schematic_pages: Optional (start, end) page range to search

        Returns:
            Dictionary mapping component IDs to success status (True if found)
        """
        from electrical_schematics.pdf.component_position_finder import (
            ComponentPositionFinder,
        )

        # Collect device tags from components
        device_tags = [comp.designation for comp in diagram.components]

        if not device_tags:
            return {}

        # Find positions
        results: Dict[str, bool] = {}

        try:
            with ComponentPositionFinder(pdf_path, schematic_pages) as finder:
                position_result = finder.find_positions(device_tags)

                # Update components with found positions
                for component in diagram.components:
                    tag = component.designation

                    if tag in position_result.positions:
                        pos = position_result.positions[tag]
                        # Set primary position and page
                        component.x = pos.x
                        component.y = pos.y
                        component.width = max(pos.width, 40.0)  # Minimum width
                        component.height = max(pos.height, 30.0)  # Minimum height
                        component.page = pos.page  # Store page number

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

                    # Handle components that appear on multiple pages (ambiguous matches)
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

        except Exception as e:
            # Log but don't fail - positions are optional
            print(f"Warning: Failed to find component positions: {e}")
            for tag in device_tags:
                results[tag] = False

        return results

    @staticmethod
    def _convert_devices(devices: Dict[str, DeviceInfo]) -> List[IndustrialComponent]:
        """Convert DRAWER devices to IndustrialComponents.

        Args:
            devices: Dictionary of DRAWER devices

        Returns:
            List of IndustrialComponents
        """
        components = []

        for tag, device in devices.items():
            component_type = DrawerToModelConverter._map_device_type(device)

            component = IndustrialComponent(
                id=tag,
                type=component_type,
                designation=tag,
                description=device.type_designation,
                voltage_rating=device.voltage_level,
                state=SensorState.UNKNOWN,
                normally_open=True  # Default, will be refined later
            )

            components.append(component)

        return components

    @staticmethod
    def _map_device_type(device: DeviceInfo) -> IndustrialComponentType:
        """Map DRAWER device to IndustrialComponentType.

        Args:
            device: DRAWER device info

        Returns:
            Appropriate IndustrialComponentType
        """
        tag = device.tag
        tech_data = device.tech_data.lower()

        # Check by tag prefix and suffix
        if tag.startswith('+DG-M'):
            return IndustrialComponentType.MOTOR
        elif tag.startswith('+DG-B'):
            return IndustrialComponentType.PROXIMITY_SENSOR  # Encoder treated as sensor
        elif tag.startswith('+DG-V'):
            return IndustrialComponentType.SOLENOID_VALVE
        elif tag.startswith('-A'):
            return IndustrialComponentType.PLC_INPUT  # PLC
        elif tag.startswith('-F'):
            if 'circuit breaker' in tech_data or 'sccr' in tech_data:
                return IndustrialComponentType.CIRCUIT_BREAKER
            return IndustrialComponentType.FUSE
        elif tag.startswith('-K'):
            if 'contactor' in tech_data:
                return IndustrialComponentType.CONTACTOR
            return IndustrialComponentType.RELAY
        elif tag.startswith('-G'):
            return IndustrialComponentType.POWER_24VDC  # Power supply
        elif tag.startswith('-U'):
            return IndustrialComponentType.MOTOR  # VFD/Drive
        elif tag.startswith('-EL'):
            return IndustrialComponentType.OTHER  # Fan
        elif tag.startswith('-R'):
            return IndustrialComponentType.OTHER  # Resistor
        elif tag.startswith('-Z'):
            return IndustrialComponentType.OTHER  # Filter

        # Check by voltage/type
        if device.voltage_level == "24VDC":
            if 'power' in tech_data or 'supply' in tech_data:
                return IndustrialComponentType.POWER_24VDC
            return IndustrialComponentType.PLC_INPUT
        elif device.voltage_level == "400VAC":
            if 'motor' in tech_data or 'kw' in tech_data:
                return IndustrialComponentType.MOTOR
            return IndustrialComponentType.POWER_400VAC
        elif device.voltage_level == "230VAC":
            return IndustrialComponentType.POWER_230VAC

        return IndustrialComponentType.OTHER

    @staticmethod
    def _convert_connections(
        connections: List[CableConnection],
        drawer_diagram: DrawerDiagram
    ) -> List[Wire]:
        """Convert DRAWER connections to Wires.

        Args:
            connections: List of DRAWER cable connections
            drawer_diagram: Original diagram for lookups

        Returns:
            List of Wire objects
        """
        wires = []

        for conn in connections:
            # Extract device tags from terminal references
            source_device = drawer_diagram._extract_device_tag(conn.source)
            target_device = drawer_diagram._extract_device_tag(conn.target)

            # Determine voltage level
            voltage_level = drawer_diagram.get_voltage_level(conn.source)
            if voltage_level == "UNKNOWN":
                voltage_level = drawer_diagram.get_voltage_level(conn.target)

            wire = Wire(
                id=f"{conn.cable_name}_{conn.conductor_num}",
                wire_number=conn.cable_name,
                voltage_level=voltage_level,
                color=conn.wire_color,
                from_component_id=source_device,
                from_terminal=conn.source,
                to_component_id=target_device,
                to_terminal=conn.target,
                is_energized=False
            )

            wires.append(wire)

        return wires

    @staticmethod
    def infer_power_sources(diagram: WiringDiagram) -> None:
        """Identify and mark power source components.

        Looks for:
        - Devices with "power" in designation
        - 24VDC power supplies
        - 400VAC mains connections

        Args:
            diagram: WiringDiagram to analyze (modified in place)
        """
        for component in diagram.components:
            # Check if this is a power source
            if component.type == IndustrialComponentType.POWER_24VDC:
                continue  # Already marked

            # Power supplies
            if '-G' in component.designation and '24VDC' in component.voltage_rating:
                component.type = IndustrialComponentType.POWER_24VDC

            # Check for mains connections (usually no specific device, just terminal)
            if component.voltage_rating == "400VAC" and component.designation.startswith('-F'):
                # Circuit breakers on 400VAC are often at mains input
                component.type = IndustrialComponentType.POWER_400VAC

    @staticmethod
    def identify_sensors(diagram: WiringDiagram) -> None:
        """Identify sensor/switch components and set their defaults.

        Args:
            diagram: WiringDiagram to analyze (modified in place)
        """
        for component in diagram.components:
            if component.is_sensor():
                # Default sensors to OFF state
                component.state = SensorState.OFF

                # Most sensors are NO (normally open)
                component.normally_open = True

                # E-stops and safety switches are typically NC
                if component.description and 'emergency' in component.description.lower():
                    component.normally_open = False
