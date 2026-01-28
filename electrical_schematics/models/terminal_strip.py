"""Data model for terminal strips and terminal blocks."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class TerminalStripType(Enum):
    """Types of terminal strips/blocks."""
    FEED_THROUGH = "feed_through"              # Simple pass-through
    GROUND = "ground"                           # PE/Earth terminals
    FUSE = "fuse"                              # Built-in fuse holder
    DISCONNECT = "disconnect"                   # Knife disconnect/test point
    MULTI_LEVEL = "multi_level"                # 2 or 3 levels stacked
    DISTRIBUTION = "distribution"               # 1 input to N outputs
    LED_INDICATOR = "led_indicator"            # With status LED
    HIGH_CURRENT = "high_current"              # Heavy duty (>25A)


class TerminalColor(Enum):
    """Standard terminal block colors per IEC 60446."""
    GRAY = "gray"                   # RAL 7035 - General use
    BLUE = "blue"                   # RAL 5012 - Neutral
    GREEN_YELLOW = "green_yellow"   # PE/Ground
    RED = "red"                     # Phase/Warning
    ORANGE = "orange"               # High voltage warning
    BROWN = "brown"                 # Phase
    BLACK = "black"                 # General


@dataclass
class TerminalPosition:
    """Represents a single terminal position on a strip.

    For multi-level terminals, multiple TerminalPosition objects
    share the same position number but different levels.
    """
    position: int                    # Position number (1, 2, 3...)
    level: int = 1                   # Level number (1, 2, 3 for multi-level)
    terminal_number: str = ""        # Display number (e.g., "1", "1.1", "N")
    has_test_point: bool = False     # Knife disconnect available
    has_led: bool = False            # Status LED present
    led_color: Optional[str] = None  # LED color if present

    def __post_init__(self):
        """Generate terminal number if not provided."""
        if not self.terminal_number:
            if self.level > 1:
                # Multi-level notation: "1.1", "1.2", etc.
                self.terminal_number = f"{self.position}.{self.level}"
            else:
                self.terminal_number = str(self.position)

    def get_full_designation(self, strip_designation: str = "") -> str:
        """Get full terminal designation including strip ID.

        Args:
            strip_designation: Parent strip designation (e.g., "X1")

        Returns:
            Full designation (e.g., "X1:1", "X1:2.1")
        """
        if strip_designation:
            return f"{strip_designation}:{self.terminal_number}"
        return self.terminal_number


@dataclass
class TerminalStrip:
    """Represents a DIN rail mounted terminal strip/block.

    Terminal strips are passive components that provide organized
    connection points for wiring. They mount on DIN rail (typically 35mm)
    and provide screw or spring-cage wire terminations.
    """

    # Identity
    designation: str                              # e.g., "X1", "X10", "PE1"
    terminal_type: TerminalStripType              # Type classification

    # Physical specifications
    position_count: int                           # Number of terminal positions
    level_count: int = 1                          # Levels per position (1-3)
    wire_gauge_min: str = "24 AWG"               # Minimum wire size
    wire_gauge_max: str = "12 AWG"               # Maximum wire size
    wire_size_min_mm2: float = 0.5               # Min size in mm²
    wire_size_max_mm2: float = 2.5               # Max size in mm²

    # Electrical ratings
    voltage_rating: str = "300V"                  # Voltage rating
    current_rating: str = "24A"                   # Current per position

    # Appearance
    color: TerminalColor = TerminalColor.GRAY     # Terminal body color

    # Special features
    has_fuse: bool = False                        # Built-in fuse holder
    fuse_type: Optional[str] = None              # e.g., "5x20mm", "1/4x1-1/4"
    has_disconnect: bool = False                  # Knife disconnect present
    has_led: bool = False                         # LED indicator present
    led_voltage: Optional[str] = None            # LED operating voltage

    # Terminal positions (auto-generated if not provided)
    terminals: List[TerminalPosition] = field(default_factory=list)

    # Manufacturer data
    manufacturer: str = ""                        # e.g., "Phoenix Contact"
    part_number: str = ""                         # Manufacturer part number
    series: str = ""                              # Product series
    description: str = ""                         # Human-readable description

    # DigiKey integration
    digikey_part_number: Optional[str] = None
    digikey_url: Optional[str] = None
    datasheet_url: Optional[str] = None
    image_url: Optional[str] = None
    unit_price: Optional[float] = None
    stock_quantity: Optional[int] = None

    # Physical mounting
    din_rail_width_mm: float = 5.2               # Width on DIN rail (mm)
    height_mm: float = 41.0                      # Total height (mm)
    depth_mm: float = 32.0                       # Depth (mm)

    # Position in diagram (if placed)
    x: float = 0.0
    y: float = 0.0
    width: float = 80.0
    height: float = 30.0
    page: int = 0

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    notes: str = ""
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize terminal positions if not provided."""
        if not self.terminals:
            self._generate_terminal_positions()

        # Set special features flags based on type
        if self.terminal_type == TerminalStripType.FUSE:
            self.has_fuse = True
            if not self.fuse_type:
                self.fuse_type = "5x20mm"

        if self.terminal_type == TerminalStripType.DISCONNECT:
            self.has_disconnect = True

        if self.terminal_type == TerminalStripType.LED_INDICATOR:
            self.has_led = True
            if not self.led_voltage:
                self.led_voltage = "24VDC"

    def _generate_terminal_positions(self):
        """Generate terminal positions based on configuration."""
        self.terminals = []

        for pos in range(1, self.position_count + 1):
            for level in range(1, self.level_count + 1):
                # For multi-level terminals, use explicit numbering format
                if self.level_count > 1:
                    terminal_number = f"{pos}.{level}"
                else:
                    terminal_number = str(pos)

                terminal = TerminalPosition(
                    position=pos,
                    level=level,
                    terminal_number=terminal_number,  # Explicitly set number
                    has_test_point=self.has_disconnect,
                    has_led=self.has_led and level == 1,  # LED only on level 1
                )
                self.terminals.append(terminal)

    def get_terminal(self, position: int, level: int = 1) -> Optional[TerminalPosition]:
        """Get a specific terminal by position and level.

        Args:
            position: Position number (1-indexed)
            level: Level number (1-indexed)

        Returns:
            TerminalPosition if found, None otherwise
        """
        for terminal in self.terminals:
            if terminal.position == position and terminal.level == level:
                return terminal
        return None

    def get_terminal_by_number(self, terminal_number: str) -> Optional[TerminalPosition]:
        """Get terminal by its number string.

        Args:
            terminal_number: Terminal number (e.g., "1", "2.1", "N")

        Returns:
            TerminalPosition if found, None otherwise
        """
        for terminal in self.terminals:
            if terminal.terminal_number == terminal_number:
                return terminal
        return None

    def get_terminal_count(self) -> int:
        """Get total number of individual terminals.

        Returns:
            Total terminals (position_count * level_count)
        """
        return self.position_count * self.level_count

    def get_display_name(self) -> str:
        """Get human-readable display name.

        Returns:
            Display name with key specifications
        """
        levels = f"{self.level_count}-level " if self.level_count > 1 else ""
        type_name = self.terminal_type.value.replace('_', ' ').title()

        if self.manufacturer and self.part_number:
            return f"{self.manufacturer} {self.part_number} ({levels}{self.position_count}-pos)"

        return f"{levels}{self.position_count}-pos {type_name} Terminal {self.designation}"

    def get_specification_summary(self) -> str:
        """Get concise specification summary.

        Returns:
            Specification string (e.g., "24A 300V, 0.5-2.5mm²")
        """
        specs = [
            self.current_rating,
            self.voltage_rating,
            f"{self.wire_size_min_mm2}-{self.wire_size_max_mm2}mm²"
        ]

        if self.has_fuse:
            specs.append(f"Fuse: {self.fuse_type}")
        if self.has_led:
            specs.append(f"LED: {self.led_voltage}")

        return ", ".join(specs)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "designation": self.designation,
            "terminal_type": self.terminal_type.value,
            "position_count": self.position_count,
            "level_count": self.level_count,
            "wire_gauge_min": self.wire_gauge_min,
            "wire_gauge_max": self.wire_gauge_max,
            "wire_size_min_mm2": self.wire_size_min_mm2,
            "wire_size_max_mm2": self.wire_size_max_mm2,
            "voltage_rating": self.voltage_rating,
            "current_rating": self.current_rating,
            "color": self.color.value,
            "has_fuse": self.has_fuse,
            "fuse_type": self.fuse_type,
            "has_disconnect": self.has_disconnect,
            "has_led": self.has_led,
            "led_voltage": self.led_voltage,
            "terminals": [
                {
                    "position": t.position,
                    "level": t.level,
                    "terminal_number": t.terminal_number,
                    "has_test_point": t.has_test_point,
                    "has_led": t.has_led,
                    "led_color": t.led_color
                }
                for t in self.terminals
            ],
            "manufacturer": self.manufacturer,
            "part_number": self.part_number,
            "series": self.series,
            "description": self.description,
            "digikey_part_number": self.digikey_part_number,
            "digikey_url": self.digikey_url,
            "datasheet_url": self.datasheet_url,
            "image_url": self.image_url,
            "unit_price": self.unit_price,
            "stock_quantity": self.stock_quantity,
            "din_rail_width_mm": self.din_rail_width_mm,
            "height_mm": self.height_mm,
            "depth_mm": self.depth_mm,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "page": self.page,
            "created_at": self.created_at.isoformat(),
            "notes": self.notes,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TerminalStrip":
        """Create TerminalStrip from dictionary.

        Args:
            data: Dictionary with terminal strip data

        Returns:
            TerminalStrip instance
        """
        # Parse datetime
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        # Parse enums
        terminal_type = TerminalStripType(data["terminal_type"])
        color = TerminalColor(data.get("color", "gray"))

        # Parse terminals
        terminals = []
        for t_data in data.get("terminals", []):
            terminal = TerminalPosition(
                position=t_data["position"],
                level=t_data.get("level", 1),
                terminal_number=t_data.get("terminal_number", ""),
                has_test_point=t_data.get("has_test_point", False),
                has_led=t_data.get("has_led", False),
                led_color=t_data.get("led_color")
            )
            terminals.append(terminal)

        return cls(
            designation=data["designation"],
            terminal_type=terminal_type,
            position_count=data["position_count"],
            level_count=data.get("level_count", 1),
            wire_gauge_min=data.get("wire_gauge_min", "24 AWG"),
            wire_gauge_max=data.get("wire_gauge_max", "12 AWG"),
            wire_size_min_mm2=data.get("wire_size_min_mm2", 0.5),
            wire_size_max_mm2=data.get("wire_size_max_mm2", 2.5),
            voltage_rating=data.get("voltage_rating", "300V"),
            current_rating=data.get("current_rating", "24A"),
            color=color,
            has_fuse=data.get("has_fuse", False),
            fuse_type=data.get("fuse_type"),
            has_disconnect=data.get("has_disconnect", False),
            has_led=data.get("has_led", False),
            led_voltage=data.get("led_voltage"),
            terminals=terminals,
            manufacturer=data.get("manufacturer", ""),
            part_number=data.get("part_number", ""),
            series=data.get("series", ""),
            description=data.get("description", ""),
            digikey_part_number=data.get("digikey_part_number"),
            digikey_url=data.get("digikey_url"),
            datasheet_url=data.get("datasheet_url"),
            image_url=data.get("image_url"),
            unit_price=data.get("unit_price"),
            stock_quantity=data.get("stock_quantity"),
            din_rail_width_mm=data.get("din_rail_width_mm", 5.2),
            height_mm=data.get("height_mm", 41.0),
            depth_mm=data.get("depth_mm", 32.0),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            width=data.get("width", 80.0),
            height=data.get("height", 30.0),
            page=data.get("page", 0),
            created_at=created_at,
            notes=data.get("notes", ""),
            tags=data.get("tags", [])
        )

    def __str__(self) -> str:
        """String representation."""
        return f"{self.designation}: {self.get_display_name()} - {self.get_specification_summary()}"
