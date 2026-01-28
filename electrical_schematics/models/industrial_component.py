"""Data models for industrial electrical components."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict


class IndustrialComponentType(Enum):
    """Types of industrial electrical components."""
    # Power sources
    POWER_24VDC = "power_24vdc"
    POWER_400VAC = "power_400vac"
    POWER_230VAC = "power_230vac"
    GROUND = "ground"

    # Sensors and inputs
    PROXIMITY_SENSOR = "proximity_sensor"
    PHOTOELECTRIC_SENSOR = "photoelectric_sensor"
    LIMIT_SWITCH = "limit_switch"
    PRESSURE_SWITCH = "pressure_switch"
    TEMPERATURE_SENSOR = "temperature_sensor"
    PUSH_BUTTON = "push_button"
    EMERGENCY_STOP = "emergency_stop"

    # Outputs and actuators
    RELAY = "relay"
    CONTACTOR = "contactor"
    SOLENOID_VALVE = "solenoid_valve"
    MOTOR = "motor"
    VFD = "vfd"  # Variable Frequency Drive
    INDICATOR_LIGHT = "indicator_light"
    BUZZER = "buzzer"

    # Control
    PLC_INPUT = "plc_input"
    PLC_OUTPUT = "plc_output"
    PLC_INPUT_STATE = "plc_input_state"  # Toggleable PLC input state indicator
    TIMER = "timer"
    COUNTER = "counter"

    # Passive components
    FUSE = "fuse"
    CIRCUIT_BREAKER = "circuit_breaker"
    TERMINAL_BLOCK = "terminal_block"
    CONNECTOR = "connector"

    OTHER = "other"


class SensorState(Enum):
    """States for sensors and switches."""
    OFF = "off"
    ON = "on"
    UNKNOWN = "unknown"


class ContactType(Enum):
    """Contact configuration types for relays/contactors."""
    NO = "normally_open"      # Normally Open - closes when energized
    NC = "normally_closed"    # Normally Closed - opens when energized
    CHANGEOVER = "changeover" # SPDT (has both NO and NC)


@dataclass
class ContactBlock:
    """Represents a contact block on a relay or contactor.

    Industrial relays and contactors have multiple contact blocks,
    each identified by terminal numbers (e.g., 13-14 for NO, 21-22 for NC).
    """
    terminal_from: str           # Terminal number (e.g., "13", "21", "1")
    terminal_to: str             # Terminal number (e.g., "14", "22", "2")
    contact_type: ContactType    # NO, NC, or changeover
    label: Optional[str] = None  # Optional label (e.g., "K1:13-14")

    # State tracking
    is_closed: bool = False      # Current state (closed = conducting)

    def get_designation(self, parent_designation: str = "") -> str:
        """Get full contact designation.

        Args:
            parent_designation: Parent component designation (e.g., "K1")

        Returns:
            Full contact designation (e.g., "K1:13-14")
        """
        if self.label:
            return self.label
        base = f"{self.terminal_from}-{self.terminal_to}"
        if parent_designation:
            return f"{parent_designation}:{base}"
        return base

    def get_state_for_coil(self, coil_energized: bool) -> bool:
        """Determine if contact is closed based on coil state.

        Args:
            coil_energized: True if coil is energized

        Returns:
            True if contact is closed (conducting)
        """
        if self.contact_type == ContactType.NO:
            return coil_energized
        elif self.contact_type == ContactType.NC:
            return not coil_energized
        else:
            # Changeover - state depends on which terminal pair is queried
            return coil_energized


@dataclass
class CoilTerminals:
    """Represents coil terminals for a relay/contactor."""
    positive: str = "A1"  # Positive coil terminal
    negative: str = "A2"  # Negative coil terminal


@dataclass
class PagePosition:
    """Position of a component on a specific PDF page.

    Used to track components that appear on multiple pages.
    """
    page: int           # PDF page number (0-indexed)
    x: float            # X coordinate in PDF points
    y: float            # Y coordinate in PDF points
    width: float        # Width in PDF points
    height: float       # Height in PDF points
    confidence: float = 1.0  # Match confidence (0.0 to 1.0)


@dataclass
class IndustrialComponent:
    """Represents an industrial electrical component.

    Supports various component types with appropriate terminal configurations:
    - Relays/Contactors: Coil terminals + multiple contact blocks
    - Sensors: Power terminals + output terminal
    - Motors: Phase terminals (U, V, W)
    - Switches: NO/NC contact pairs
    """

    id: str
    type: IndustrialComponentType
    designation: str  # e.g., "S1", "K1", "M1"
    description: Optional[str] = None
    voltage_rating: Optional[str] = None  # e.g., "24VDC", "400VAC"

    # Position in PDF (in points) - primary position (first/best match)
    x: float = 0.0
    y: float = 0.0
    width: float = 40.0
    height: float = 30.0

    # Page number in PDF (0-indexed) - primary page for this component
    page: int = 0

    # Multi-page support: positions on all pages where this component appears
    # Key is page number, value is PagePosition
    page_positions: Dict[int, PagePosition] = field(default_factory=dict)

    # For sensors/switches - current state
    state: SensorState = SensorState.UNKNOWN

    # Normally open (NO) or normally closed (NC) for switches
    normally_open: bool = True

    # For relays/contactors - coil state
    coil_energized: bool = False

    # For relays/contactors - coil terminal configuration
    coil_terminals: Optional[CoilTerminals] = None

    # For relays/contactors - list of contact blocks
    contact_blocks: List[ContactBlock] = field(default_factory=list)

    # Legacy: list of contact designations (kept for backward compatibility)
    contacts: List[str] = field(default_factory=list)

    # Current rating (for contactors, fuses, breakers)
    current_rating: Optional[str] = None  # e.g., "16A", "25A"

    # Light color (for indicator lights)
    light_color: Optional[str] = None  # e.g., "green", "red", "yellow"

    def __post_init__(self) -> None:
        """Initialize mutable defaults and set up default configurations."""
        # Initialize coil terminals for relays/contactors if not set
        if self.coil_terminals is None and self.type in [
            IndustrialComponentType.RELAY,
            IndustrialComponentType.CONTACTOR
        ]:
            self.coil_terminals = CoilTerminals()

        # Set up default contact blocks for relays/contactors if none specified
        if not self.contact_blocks and self.type in [
            IndustrialComponentType.RELAY,
            IndustrialComponentType.CONTACTOR
        ]:
            self._setup_default_contacts()

        # Try to extract page number from description if not set
        if self.page == 0 and self.description:
            self._extract_page_from_description()

    def _extract_page_from_description(self) -> None:
        """Extract page number from description if present."""
        import re
        if self.description:
            match = re.search(r'Page (\d+)', self.description)
            if match:
                self.page = int(match.group(1)) - 1  # Convert to 0-indexed

    def _setup_default_contacts(self) -> None:
        """Set up default contact configuration based on component type."""
        if self.type == IndustrialComponentType.RELAY:
            # Default relay: 1 NO contact (13-14)
            self.contact_blocks = [
                ContactBlock("13", "14", ContactType.NO)
            ]
        elif self.type == IndustrialComponentType.CONTACTOR:
            # Default contactor: 3 main contacts (power) + 1 auxiliary NO
            self.contact_blocks = [
                ContactBlock("1", "2", ContactType.NO, label="L1-T1"),
                ContactBlock("3", "4", ContactType.NO, label="L2-T2"),
                ContactBlock("5", "6", ContactType.NO, label="L3-T3"),
                ContactBlock("13", "14", ContactType.NO),  # Auxiliary NO
            ]

    def add_page_position(
        self,
        page: int,
        x: float,
        y: float,
        width: float,
        height: float,
        confidence: float = 1.0
    ) -> None:
        """Add a position for this component on a specific page.

        Used for components that appear on multiple pages.

        Args:
            page: PDF page number (0-indexed)
            x: X coordinate in PDF points
            y: Y coordinate in PDF points
            width: Width in PDF points
            height: Height in PDF points
            confidence: Match confidence (0.0 to 1.0)
        """
        self.page_positions[page] = PagePosition(
            page=page,
            x=x,
            y=y,
            width=width,
            height=height,
            confidence=confidence
        )

        # If this is the first position or has higher confidence, make it primary
        if len(self.page_positions) == 1 or confidence >= max(
            pos.confidence for pos in self.page_positions.values()
        ):
            self.page = page
            self.x = x
            self.y = y
            self.width = width
            self.height = height

    def get_pages(self) -> List[int]:
        """Get all pages where this component appears.

        Returns:
            List of page numbers (0-indexed), sorted
        """
        if self.page_positions:
            return sorted(self.page_positions.keys())
        elif self.x != 0.0 or self.y != 0.0:
            return [self.page]
        return []

    def get_position_for_page(self, page: int) -> Optional[PagePosition]:
        """Get the position of this component on a specific page.

        Args:
            page: PDF page number (0-indexed)

        Returns:
            PagePosition if component is on this page, None otherwise
        """
        if page in self.page_positions:
            return self.page_positions[page]
        elif page == self.page and (self.x != 0.0 or self.y != 0.0):
            # Fallback to primary position if page matches
            return PagePosition(
                page=self.page,
                x=self.x,
                y=self.y,
                width=self.width,
                height=self.height
            )
        return None

    def is_on_page(self, page: int) -> bool:
        """Check if this component appears on a specific page.

        Args:
            page: PDF page number (0-indexed)

        Returns:
            True if component is on this page
        """
        if page in self.page_positions:
            return True
        if page == self.page and (self.x != 0.0 or self.y != 0.0):
            return True
        return False

    def add_contact(
        self,
        terminal_from: str,
        terminal_to: str,
        contact_type: ContactType,
        label: Optional[str] = None
    ) -> ContactBlock:
        """Add a contact block to this component.

        Args:
            terminal_from: From terminal number
            terminal_to: To terminal number
            contact_type: NO, NC, or changeover
            label: Optional contact label

        Returns:
            The created ContactBlock
        """
        contact = ContactBlock(terminal_from, terminal_to, contact_type, label)
        self.contact_blocks.append(contact)
        return contact

    def get_contacts_by_type(self, contact_type: ContactType) -> List[ContactBlock]:
        """Get all contacts of a specific type.

        Args:
            contact_type: Type of contacts to retrieve

        Returns:
            List of matching ContactBlock objects
        """
        return [c for c in self.contact_blocks if c.contact_type == contact_type]

    def get_no_contacts(self) -> List[ContactBlock]:
        """Get all normally-open contacts."""
        return self.get_contacts_by_type(ContactType.NO)

    def get_nc_contacts(self) -> List[ContactBlock]:
        """Get all normally-closed contacts."""
        return self.get_contacts_by_type(ContactType.NC)

    def update_contact_states(self) -> None:
        """Update all contact states based on coil energization."""
        for contact in self.contact_blocks:
            contact.is_closed = contact.get_state_for_coil(self.coil_energized)

    def energize_coil(self) -> None:
        """Energize the coil (for relays/contactors)."""
        self.coil_energized = True
        self.update_contact_states()

    def de_energize_coil(self) -> None:
        """De-energize the coil (for relays/contactors)."""
        self.coil_energized = False
        self.update_contact_states()

    def toggle_coil(self) -> bool:
        """Toggle coil state.

        Returns:
            New coil state (True = energized)
        """
        if self.coil_energized:
            self.de_energize_coil()
        else:
            self.energize_coil()
        return self.coil_energized

    def is_power_source(self) -> bool:
        """Check if component is a power source."""
        return self.type in [
            IndustrialComponentType.POWER_24VDC,
            IndustrialComponentType.POWER_400VAC,
            IndustrialComponentType.POWER_230VAC,
        ]

    def is_sensor(self) -> bool:
        """Check if component is a sensor or switch."""
        return self.type in [
            IndustrialComponentType.PROXIMITY_SENSOR,
            IndustrialComponentType.PHOTOELECTRIC_SENSOR,
            IndustrialComponentType.LIMIT_SWITCH,
            IndustrialComponentType.PRESSURE_SWITCH,
            IndustrialComponentType.TEMPERATURE_SENSOR,
            IndustrialComponentType.PUSH_BUTTON,
            IndustrialComponentType.EMERGENCY_STOP,
            IndustrialComponentType.PLC_INPUT_STATE,  # Toggleable PLC input
        ]

    def is_relay_or_contactor(self) -> bool:
        """Check if component is a relay or contactor."""
        return self.type in [
            IndustrialComponentType.RELAY,
            IndustrialComponentType.CONTACTOR,
        ]

    def is_energized(self) -> bool:
        """Check if component allows current flow based on its state.

        For sensors/switches: depends on state and NO/NC configuration
        For relays/contactors: checks coil energization
        For other components: assumed to pass current if not explicitly OFF
        """
        if not self.is_sensor():
            return True

        if self.state == SensorState.UNKNOWN:
            return False

        # NO contact: closed when sensor is ON
        # NC contact: closed when sensor is OFF
        if self.normally_open:
            return self.state == SensorState.ON
        else:
            return self.state == SensorState.OFF

    def get_contact_string(self) -> str:
        """Get a human-readable string describing contacts.

        Returns:
            String like "3NO + 1NC" or "1NO"
        """
        no_count = len(self.get_no_contacts())
        nc_count = len(self.get_nc_contacts())

        parts = []
        if no_count > 0:
            parts.append(f"{no_count}NO")
        if nc_count > 0:
            parts.append(f"{nc_count}NC")

        return " + ".join(parts) if parts else "No contacts"

    def get_terminal_labels(self) -> List[str]:
        """Get list of all terminal labels for this component.

        Returns:
            List of terminal labels
        """
        terminals = []

        # Add coil terminals for relays/contactors
        if self.coil_terminals:
            terminals.extend([self.coil_terminals.positive, self.coil_terminals.negative])

        # Add contact terminals
        for contact in self.contact_blocks:
            terminals.extend([contact.terminal_from, contact.terminal_to])

        return list(set(terminals))  # Remove duplicates

    def get_display_description(self, max_length: int = 40) -> str:
        """Get a cleaned-up description suitable for display.

        Removes redundant information and German text patterns,
        truncates to max_length.

        Args:
            max_length: Maximum length of returned string

        Returns:
            Cleaned description string
        """
        if not self.description:
            return self.type.value.replace('_', ' ').title()

        desc = self.description

        # Remove common German patterns that duplicate info
        import re
        # Remove "Page XX" from display (it's shown separately)
        desc = re.sub(r'\s*Page\s+\d+\s*', ' ', desc)
        # Remove duplicate designation patterns like "-K1 -K1"
        desc = re.sub(r'(-[A-Z]\d+)\s+\1', r'\1', desc)
        # Clean up multiple spaces
        desc = re.sub(r'\s+', ' ', desc).strip()

        # Truncate with ellipsis if too long
        if len(desc) > max_length:
            return desc[:max_length - 3] + '...'
        return desc

    def __str__(self) -> str:
        """String representation of the component."""
        desc = f" - {self.description}" if self.description else ""
        voltage = f" ({self.voltage_rating})" if self.voltage_rating else ""

        # Add contact info for relays/contactors
        contacts_str = ""
        if self.is_relay_or_contactor():
            contacts_str = f" [{self.get_contact_string()}]"

        return f"{self.designation}: {self.type.value}{voltage}{contacts_str}{desc}"
