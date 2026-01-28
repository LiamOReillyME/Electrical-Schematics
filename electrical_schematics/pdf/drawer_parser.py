"""Parser for DRAWER-style industrial electrical diagrams.

This parser handles the specific format of industrial electrical diagrams
with device tag lists and cable routing tables across multiple pages.
"""

import fitz  # PyMuPDF
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class DeviceInfo:
    """Information about a device from the device tag list."""

    tag: str  # e.g., "-A1", "+DG-B1"
    page_ref: str  # Page reference in diagram
    tech_data: str  # Technical specifications
    type_designation: str  # Type/model
    part_number: str  # Part/article number
    voltage_level: str = "UNKNOWN"  # 24VDC, 400VAC, etc.

    def __post_init__(self) -> None:
        """Automatically determine voltage level from technical data."""
        if not self.voltage_level or self.voltage_level == "UNKNOWN":
            self.voltage_level = self._detect_voltage()

    def _detect_voltage(self) -> str:
        """Detect voltage level from technical data string."""
        tech_lower = self.tech_data.lower()

        # Check for specific voltage mentions
        if re.search(r'\b24vdc?\b', tech_lower):
            return "24VDC"
        elif re.search(r'\b5vdc?\b', tech_lower):
            return "5VDC"
        elif re.search(r'\b400va', tech_lower):
            return "400VAC"
        elif re.search(r'\b230va', tech_lower):
            return "230VAC"
        elif re.search(r'\b150-260va', tech_lower):
            return "230VAC"  # Likely 230VAC supply

        return "UNKNOWN"


@dataclass
class CableConnection:
    """A single conductor connection in a cable."""

    cable_name: str  # e.g., "+CD-B1"
    cable_type: str  # e.g., "BMGH-Typ:STS24 8x0,25 qmm"
    source: str  # Source terminal e.g., "-A1-X5:3"
    target: str  # Target terminal e.g., "+DG-B1:0V"
    function_source: str = ""  # Function description at source
    function_target: str = ""  # Function description at target
    wire_color: str = ""  # Wire color code
    conductor_num: int = 0  # Conductor number in cable


@dataclass
class DrawerDiagram:
    """Complete parsed DRAWER electrical diagram."""

    pdf_path: Path
    devices: Dict[str, DeviceInfo] = field(default_factory=dict)
    connections: List[CableConnection] = field(default_factory=list)

    def get_device(self, tag: str) -> Optional[DeviceInfo]:
        """Get device info by tag."""
        return self.devices.get(tag)

    def get_connections_for_device(self, tag: str) -> List[CableConnection]:
        """Get all cable connections involving a device."""
        connections = []
        for conn in self.connections:
            # Extract device tag from terminal references
            source_device = self._extract_device_tag(conn.source)
            target_device = self._extract_device_tag(conn.target)

            if source_device == tag or target_device == tag:
                connections.append(conn)

        return connections

    @staticmethod
    def _extract_device_tag(terminal_ref: str) -> str:
        """Extract device tag from terminal reference.

        Terminal references can be:
        - Device with terminal block: "-A1-X5:3" -> device is "-A1", terminal is "X5:3"
        - Device with terminal: "+DG-B1:0V" -> device is "+DG-B1", terminal is "0V"
        - Simple device: "-K1" -> device is "-K1"

        The pattern is: [+-]DEVICE[-TERMINAL_BLOCK][:PIN]

        Examples:
            "-A1-X5:3" -> "-A1"
            "+DG-B1:0V" -> "+DG-B1"
            "-K1:13" -> "-K1"
        """
        # Match: [+-] followed by alphanumeric, optionally followed by -X# (terminal block)
        # Terminal block typically starts with X followed by numbers
        match = re.match(r'([+-][A-Z0-9]+)(?:-X\d+)?', terminal_ref)
        if match:
            return match.group(1)

        # Fallback: just get the device part before any colon or second dash
        match = re.match(r'([+-][A-Z0-9]+)', terminal_ref)
        if match:
            return match.group(1)

        return ""

    def get_voltage_level(self, terminal_ref: str) -> str:
        """Get voltage level for a terminal reference."""
        device_tag = self._extract_device_tag(terminal_ref)
        device = self.get_device(device_tag)
        if device:
            return device.voltage_level
        return "UNKNOWN"


class DrawerParser:
    """Parser for DRAWER-style electrical diagrams."""

    def __init__(self, pdf_path: Path):
        """Initialize the parser.

        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = pdf_path
        self.doc: Optional[fitz.Document] = None

    def parse(self) -> DrawerDiagram:
        """Parse the complete diagram.

        Returns:
            Parsed DrawerDiagram object
        """
        self.doc = fitz.open(self.pdf_path)

        diagram = DrawerDiagram(pdf_path=self.pdf_path)

        # Parse device tag list (typically pages 26-27)
        diagram.devices = self._parse_device_tags()

        # Parse cable connections (typically pages 28-40)
        diagram.connections = self._parse_cable_connections()

        self.doc.close()
        self.doc = None

        return diagram

    def _parse_device_tags(self) -> Dict[str, DeviceInfo]:
        """Parse device tag list from PDF.

        The device list has a vertical layout with each field on separate lines:
        Line 1: Device tag (e.g., "-A1")
        Line 2: Page reference (e.g., "18 0")
        Line 3: Technical data (e.g., "24VDC 24xD-IN 8xD-OUT 4xCO")
        Line 4: Type designation (e.g., "PCD3.M9K47")
        Line 5: Part number (e.g., "6223994")

        Returns:
            Dictionary mapping device tags to DeviceInfo objects
        """
        devices = {}

        # Device tags are typically on pages 26-27
        # But we'll search all pages for robustness
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()

            # Look for "Device tag" or "Betriebsmittelkennzeichen" header
            if "Device tag" not in text and "Betriebsmittelkennzeichen" not in text:
                continue

            lines = [l.strip() for l in text.split('\n')]

            # Find where the actual device data starts
            data_start = 0
            for i, line in enumerate(lines):
                if re.match(r'^[+-][A-Z0-9]+(?:-[A-Z0-9]+)?$', line):
                    data_start = i
                    break

            # Parse devices in groups of ~5-8 lines
            i = data_start
            while i < len(lines):
                line = lines[i]

                # Look for device tag (format: +/- followed by alphanumeric)
                if re.match(r'^[+-][A-Z0-9]+(?:-[A-Z0-9]+)?$', line):
                    tag = line

                    # Next lines should contain device info
                    if i + 4 < len(lines):
                        page_ref = lines[i + 1]
                        tech_data = lines[i + 2]
                        type_des = lines[i + 3]
                        part_num = lines[i + 4]

                        # Validate this looks like a device entry
                        # Page ref should be numbers, part number should be 7 digits
                        if re.search(r'\d', page_ref) and re.search(r'\d{6,8}', part_num):
                            device = DeviceInfo(
                                tag=tag,
                                page_ref=page_ref,
                                tech_data=tech_data,
                                type_designation=type_des,
                                part_number=part_num
                            )

                            devices[tag] = device

                            # Skip ahead past this entry and description lines
                            i += 5
                            continue

                i += 1

        return devices

    def _parse_cable_connections(self) -> List[CableConnection]:
        """Parse cable routing tables from PDF.

        Returns:
            List of CableConnection objects
        """
        connections = []

        # Cable diagrams are typically on pages 28-40
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()

            # Look for "Cable diagram" or "Kabelplan" header
            if "Cable diagram" not in text and "Kabelplan" not in text:
                continue

            lines = text.split('\n')
            lines = [l.strip() for l in lines if l.strip()]

            # State machine for parsing cable entries
            current_cable_name = None
            current_cable_type = None
            conductor_num = 0

            i = 0
            while i < len(lines):
                line = lines[i]

                # Look for cable name (starts with +CD-)
                if re.match(r'\+CD-', line):
                    current_cable_name = line
                    conductor_num = 0
                    i += 1
                    continue

                # Look for cable type (contains "Typ:" or "qmm")
                if re.search(r'Typ:|qmm', line):
                    current_cable_type = line
                    i += 1
                    continue

                # Look for source terminal reference
                source_match = re.match(r'([+-][A-Z0-9]+-[A-Z0-9]+:[A-Z0-9]+)', line)
                if source_match and current_cable_name:
                    source = source_match.group(1)

                    # Look for target in upcoming lines (usually 2-4 lines ahead)
                    target = None
                    function_source = ""
                    function_target = ""
                    wire_color = ""

                    for j in range(1, min(6, len(lines) - i)):
                        next_line = lines[i + j]

                        # Look for target terminal
                        target_match = re.match(r'([+-][A-Z0-9]+-[A-Z0-9]+:[A-Z0-9]+)', next_line)
                        if target_match:
                            target = target_match.group(1)
                            break

                        # Collect function text (lines between source and target)
                        if not target_match and len(next_line) > 1:
                            if not function_source:
                                function_source = next_line
                            else:
                                function_target = next_line

                    # Look for wire color (2-3 letter codes like BK, GN, GNBN)
                    for j in range(1, min(6, len(lines) - i)):
                        next_line = lines[i + j]
                        if re.match(r'^[A-Z]{2,4}$', next_line):
                            wire_color = next_line
                            break

                    if target:
                        conductor_num += 1
                        connection = CableConnection(
                            cable_name=current_cable_name,
                            cable_type=current_cable_type or "",
                            source=source,
                            target=target,
                            function_source=function_source,
                            function_target=function_target,
                            wire_color=wire_color,
                            conductor_num=conductor_num
                        )
                        connections.append(connection)

                i += 1

        return connections
