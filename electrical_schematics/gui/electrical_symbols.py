"""SVG-based electrical symbols following IEC/ANSI standards.

This module provides standard electrical schematic symbols for:
- Contacts (NO/NC)
- Coils (relay/contactor)
- Switches
- Motors
- Sensors
- Power sources
- Protection devices
- VFDs (Variable Frequency Drives)
"""

from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class ContactType(Enum):
    """Contact configuration types."""
    NO = "normally_open"      # Normally Open
    NC = "normally_closed"    # Normally Closed
    CHANGEOVER = "changeover" # SPDT (NO + NC)


@dataclass
class ContactConfig:
    """Configuration for a contact on a relay/contactor."""
    terminal_from: str       # e.g., "13", "21", "1"
    terminal_to: str         # e.g., "14", "22", "2"
    contact_type: ContactType
    label: Optional[str] = None  # e.g., "K1:13-14"


@dataclass
class ComponentSymbolConfig:
    """Configuration for rendering a component symbol."""
    coil_terminals: Optional[Tuple[str, str]] = None  # e.g., ("A1", "A2")
    contacts: Optional[List[ContactConfig]] = None
    show_designation: bool = True
    designation: str = ""
    energized: bool = False


# Color scheme for electrical symbols
COLORS = {
    'primary': '#2C3E50',        # Dark blue-gray (lines, text)
    'secondary': '#7F8C8D',      # Gray (secondary elements)
    'energized': '#27AE60',      # Green (energized state)
    'de_energized': '#E74C3C',   # Red (de-energized state)
    'coil_fill': '#F39C12',      # Orange (coil fill)
    'contact_no': '#3498DB',     # Blue (NO contact)
    'contact_nc': '#9B59B6',     # Purple (NC contact)
    'background': '#FFFFFF',     # White background
    'terminal': '#F1C40F',       # Yellow (terminals)
}


def _svg_header(width: int = 80, height: int = 60, viewbox: str = "0 0 80 60") -> str:
    """Generate SVG header."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="{viewbox}">
  <style>
    .primary {{ fill: none; stroke: {COLORS['primary']}; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }}
    .primary-fill {{ fill: {COLORS['primary']}; stroke: none; }}
    .coil {{ fill: {COLORS['coil_fill']}; stroke: {COLORS['primary']}; stroke-width: 1.5; }}
    .contact-no {{ fill: none; stroke: {COLORS['contact_no']}; stroke-width: 2; }}
    .contact-nc {{ fill: none; stroke: {COLORS['contact_nc']}; stroke-width: 2; }}
    .terminal {{ fill: {COLORS['terminal']}; stroke: {COLORS['primary']}; stroke-width: 1; }}
    .text {{ font-family: Arial, sans-serif; font-size: 8px; fill: {COLORS['primary']}; }}
    .text-small {{ font-family: Arial, sans-serif; font-size: 6px; fill: {COLORS['secondary']}; }}
    .energized {{ stroke: {COLORS['energized']}; }}
    .de-energized {{ stroke: {COLORS['de_energized']}; }}
  </style>
'''


def _svg_footer() -> str:
    """Generate SVG footer."""
    return '</svg>'


def create_no_contact_symbol(
    x: int = 0,
    y: int = 0,
    width: int = 40,
    height: int = 30,
    label: str = "",
    terminal_labels: Tuple[str, str] = ("13", "14"),
    energized: bool = False,
    **kwargs
) -> str:
    """Create SVG for Normally Open (NO) contact.

    IEC Symbol: Two parallel lines with a gap, movable contact shown open.

    Args:
        x: X position
        y: Y position
        width: Symbol width
        height: Symbol height
        label: Contact label (e.g., "K1")
        terminal_labels: Terminal numbers
        energized: If True, show closed (conducting) state

    Returns:
        SVG string for the NO contact
    """
    cx = x + width // 2
    cy = y + height // 2

    state_class = "energized" if energized else ""

    # NO contact: gap when open, closed line when energized
    if energized:
        # Closed state - straight horizontal line
        contact_line = f'''
  <line x1="{x + 5}" y1="{cy}" x2="{x + width - 5}" y2="{cy}" class="contact-no {state_class}" />
'''
    else:
        # Open state - angled movable contact
        contact_line = f'''
  <line x1="{x + 5}" y1="{cy}" x2="{cx - 5}" y2="{cy}" class="contact-no" />
  <line x1="{cx - 5}" y1="{cy}" x2="{cx + 8}" y2="{cy - 10}" class="contact-no" />
  <line x1="{cx + 5}" y1="{cy}" x2="{x + width - 5}" y2="{cy}" class="contact-no" />
'''

    # Terminal circles
    terminals = f'''
  <circle cx="{x + 5}" cy="{cy}" r="3" class="terminal" />
  <circle cx="{x + width - 5}" cy="{cy}" r="3" class="terminal" />
'''

    # Labels
    labels = f'''
  <text x="{x + 5}" y="{cy + 15}" class="text-small">{terminal_labels[0]}</text>
  <text x="{x + width - 10}" y="{cy + 15}" class="text-small">{terminal_labels[1]}</text>
'''
    if label:
        labels += f'  <text x="{cx}" y="{y + 8}" text-anchor="middle" class="text">{label}</text>\n'

    return contact_line + terminals + labels


def create_nc_contact_symbol(
    x: int = 0,
    y: int = 0,
    width: int = 40,
    height: int = 30,
    label: str = "",
    terminal_labels: Tuple[str, str] = ("21", "22"),
    energized: bool = False,
    **kwargs
) -> str:
    """Create SVG for Normally Closed (NC) contact.

    IEC Symbol: Two parallel lines connected, with diagonal bar indicating NC.

    Args:
        x: X position
        y: Y position
        width: Symbol width
        height: Symbol height
        label: Contact label (e.g., "K1")
        terminal_labels: Terminal numbers
        energized: If True, show open (non-conducting) state

    Returns:
        SVG string for the NC contact
    """
    cx = x + width // 2
    cy = y + height // 2

    state_class = "energized" if energized else ""

    if energized:
        # Open state (energized NC contact opens)
        contact_line = f'''
  <line x1="{x + 5}" y1="{cy}" x2="{cx - 5}" y2="{cy}" class="contact-nc {state_class}" />
  <line x1="{cx - 5}" y1="{cy}" x2="{cx + 8}" y2="{cy - 10}" class="contact-nc {state_class}" />
  <line x1="{cx + 5}" y1="{cy}" x2="{x + width - 5}" y2="{cy}" class="contact-nc {state_class}" />
'''
    else:
        # Closed state - straight line with diagonal NC indicator
        contact_line = f'''
  <line x1="{x + 5}" y1="{cy}" x2="{x + width - 5}" y2="{cy}" class="contact-nc" />
  <line x1="{cx - 3}" y1="{cy - 8}" x2="{cx + 3}" y2="{cy + 8}" class="contact-nc" />
'''

    # Terminal circles
    terminals = f'''
  <circle cx="{x + 5}" cy="{cy}" r="3" class="terminal" />
  <circle cx="{x + width - 5}" cy="{cy}" r="3" class="terminal" />
'''

    # Labels
    labels = f'''
  <text x="{x + 5}" y="{cy + 15}" class="text-small">{terminal_labels[0]}</text>
  <text x="{x + width - 10}" y="{cy + 15}" class="text-small">{terminal_labels[1]}</text>
'''
    if label:
        labels += f'  <text x="{cx}" y="{y + 8}" text-anchor="middle" class="text">{label}</text>\n'

    return contact_line + terminals + labels


def create_coil_symbol(
    x: int = 0,
    y: int = 0,
    width: int = 30,
    height: int = 40,
    designation: str = "K1",
    terminal_labels: Tuple[str, str] = ("A1", "A2"),
    energized: bool = False,
    **kwargs
) -> str:
    """Create SVG for relay/contactor coil.

    IEC Symbol: Rectangle with diagonal lines or parentheses inside.

    Args:
        x: X position
        y: Y position
        width: Symbol width
        height: Symbol height
        designation: Component designation (e.g., "K1")
        terminal_labels: Terminal names
        energized: If True, show energized state

    Returns:
        SVG string for the coil
    """
    cx = x + width // 2
    cy = y + height // 2

    coil_width = width - 10
    coil_height = height - 20
    coil_x = cx - coil_width // 2
    coil_y = cy - coil_height // 2

    fill_color = COLORS['energized'] if energized else COLORS['coil_fill']

    coil = f'''
  <rect x="{coil_x}" y="{coil_y}" width="{coil_width}" height="{coil_height}"
        rx="2" class="coil" style="fill: {fill_color};" />
  <text x="{cx}" y="{cy + 3}" text-anchor="middle" class="text" style="font-weight: bold;">{designation}</text>
'''

    # Connection lines to terminals
    lines = f'''
  <line x1="{cx}" y1="{y + 5}" x2="{cx}" y2="{coil_y}" class="primary" />
  <line x1="{cx}" y1="{coil_y + coil_height}" x2="{cx}" y2="{y + height - 5}" class="primary" />
'''

    # Terminal circles
    terminals = f'''
  <circle cx="{cx}" cy="{y + 5}" r="3" class="terminal" />
  <circle cx="{cx}" cy="{y + height - 5}" r="3" class="terminal" />
'''

    # Terminal labels
    labels = f'''
  <text x="{cx + 8}" y="{y + 8}" class="text-small">{terminal_labels[0]}</text>
  <text x="{cx + 8}" y="{y + height - 2}" class="text-small">{terminal_labels[1]}</text>
'''

    return coil + lines + terminals + labels


def create_relay_symbol(
    width: int = 120,
    height: int = 80,
    designation: str = "K1",
    contacts: Optional[List[ContactConfig]] = None,
    energized: bool = False,
    **kwargs
) -> str:
    """Create complete relay/contactor symbol with coil and contacts.

    Args:
        width: Total symbol width
        height: Total symbol height
        designation: Component designation
        contacts: List of contact configurations
        energized: If True, show energized state

    Returns:
        Complete SVG string for relay with coil and contacts
    """
    if contacts is None:
        # Default: 1 NO contact
        contacts = [
            ContactConfig("13", "14", ContactType.NO),
        ]

    svg = _svg_header(width, height, f"0 0 {width} {height}")

    # Draw coil on left side
    coil_width = 30
    coil_x = 5
    svg += create_coil_symbol(
        x=coil_x, y=10, width=coil_width, height=height - 20,
        designation=designation, energized=energized
    )

    # Draw contacts on right side
    contact_width = 50
    num_contacts = len(contacts)
    contact_height = (height - 10) // max(num_contacts, 1)

    for i, contact in enumerate(contacts):
        contact_y = 5 + i * contact_height
        contact_x = coil_width + 15

        if contact.contact_type == ContactType.NO:
            svg += create_no_contact_symbol(
                x=contact_x, y=contact_y, width=contact_width, height=contact_height,
                label=contact.label or "",
                terminal_labels=(contact.terminal_from, contact.terminal_to),
                energized=energized
            )
        elif contact.contact_type == ContactType.NC:
            svg += create_nc_contact_symbol(
                x=contact_x, y=contact_y, width=contact_width, height=contact_height,
                label=contact.label or "",
                terminal_labels=(contact.terminal_from, contact.terminal_to),
                energized=energized
            )

    # Draw dashed line connecting coil to contacts (mechanical linkage)
    coil_cx = coil_x + coil_width // 2
    svg += f'''
  <line x1="{coil_cx + 15}" y1="{height // 2}" x2="{coil_width + 15}" y2="{height // 2}"
        stroke-dasharray="3,2" class="primary" style="stroke: {COLORS['secondary']};" />
'''

    svg += _svg_footer()
    return svg


def create_motor_symbol(
    width: int = 60,
    height: int = 60,
    designation: str = "M1",
    voltage: str = "400VAC",
    **kwargs
) -> str:
    """Create motor symbol.

    IEC Symbol: Circle with M inside.

    Args:
        width: Symbol width
        height: Symbol height
        designation: Motor designation
        voltage: Voltage rating

    Returns:
        SVG string for motor symbol
    """
    svg = _svg_header(width, height, f"0 0 {width} {height}")

    cx = width // 2
    cy = height // 2
    radius = min(width, height) // 2 - 10

    # Motor circle
    svg += f'''
  <circle cx="{cx}" cy="{cy}" r="{radius}" class="primary" style="fill: #ecf0f1;" />
  <text x="{cx}" y="{cy + 4}" text-anchor="middle" class="text" style="font-size: 14px; font-weight: bold;">M</text>
  <text x="{cx}" y="{cy + 14}" text-anchor="middle" class="text-small">{designation}</text>
'''

    # Three-phase terminals at top
    terminal_spacing = 12
    for i, label in enumerate(["U", "V", "W"]):
        tx = cx - terminal_spacing + i * terminal_spacing
        ty = cy - radius - 5
        svg += f'''
  <line x1="{tx}" y1="{cy - radius}" x2="{tx}" y2="{ty}" class="primary" />
  <circle cx="{tx}" cy="{ty}" r="3" class="terminal" />
  <text x="{tx}" y="{ty - 5}" text-anchor="middle" class="text-small">{label}</text>
'''

    svg += _svg_footer()
    return svg


def create_sensor_symbol(
    width: int = 50,
    height: int = 40,
    designation: str = "B1",
    sensor_type: str = "proximity",
    normally_open: bool = True,
    **kwargs
) -> str:
    """Create sensor symbol (proximity, photoelectric, etc.).

    Args:
        width: Symbol width
        height: Symbol height
        designation: Sensor designation
        sensor_type: Type of sensor
        normally_open: True for NO output, False for NC

    Returns:
        SVG string for sensor symbol
    """
    svg = _svg_header(width, height, f"0 0 {width} {height}")

    cx = width // 2
    cy = height // 2

    # Sensor body (rectangle with rounded corners)
    body_width = width - 20
    body_height = height - 15
    body_x = cx - body_width // 2
    body_y = cy - body_height // 2

    svg += f'''
  <rect x="{body_x}" y="{body_y}" width="{body_width}" height="{body_height}"
        rx="4" class="primary" style="fill: #e8f6f3;" />
'''

    # Sensor type indicator
    if sensor_type == "proximity":
        # Proximity sensor: curved lines
        svg += f'''
  <path d="M {cx - 8} {cy - 5} Q {cx} {cy - 10} {cx + 8} {cy - 5}" class="primary" style="fill: none;" />
  <path d="M {cx - 6} {cy} Q {cx} {cy - 5} {cx + 6} {cy}" class="primary" style="fill: none;" />
'''
    elif sensor_type == "photoelectric":
        # Photoelectric sensor: arrow/light beam
        svg += f'''
  <line x1="{cx - 8}" y1="{cy}" x2="{cx + 5}" y2="{cy}" class="primary" />
  <polygon points="{cx + 5},{cy - 3} {cx + 10},{cy} {cx + 5},{cy + 3}" class="primary-fill" />
'''

    # Designation
    svg += f'''
  <text x="{cx}" y="{cy + body_height // 2 + 10}" text-anchor="middle" class="text">{designation}</text>
'''

    # Output type indicator (NO/NC)
    output_label = "NO" if normally_open else "NC"
    svg += f'''
  <text x="{body_x + body_width - 5}" y="{body_y + 10}" text-anchor="end" class="text-small">{output_label}</text>
'''

    # Terminals
    # Power terminals on left
    svg += f'''
  <circle cx="{body_x}" cy="{cy - 5}" r="3" class="terminal" />
  <circle cx="{body_x}" cy="{cy + 5}" r="3" class="terminal" />
  <text x="{body_x - 5}" y="{cy - 2}" text-anchor="end" class="text-small">+</text>
  <text x="{body_x - 5}" y="{cy + 8}" text-anchor="end" class="text-small">-</text>
'''
    # Output terminal on right
    svg += f'''
  <circle cx="{body_x + body_width}" cy="{cy}" r="3" class="terminal" />
  <text x="{body_x + body_width + 5}" y="{cy + 3}" class="text-small">OUT</text>
'''

    svg += _svg_footer()
    return svg


def create_power_supply_symbol(
    width: int = 40,
    height: int = 50,
    voltage: str = "24VDC",
    designation: str = "",
    **kwargs
) -> str:
    """Create power supply symbol.

    Args:
        width: Symbol width
        height: Symbol height
        voltage: Voltage output
        designation: Component designation (e.g., G1)
        **kwargs: Additional arguments (ignored)

    Returns:
        SVG string for power supply
    """
    # Increase height if we have a designation to display
    if designation:
        height = max(height, 60)

    svg = _svg_header(width, height, f"0 0 {width} {height}")

    cx = width // 2
    cy = height // 2

    # Power supply body
    body_height = height - 30 if designation else height - 20
    body_y = 10

    svg += f'''
  <rect x="5" y="{body_y}" width="{width - 10}" height="{body_height}"
        rx="3" class="primary" style="fill: #fdf2e9;" />
  <text x="{cx}" y="{cy - 5}" text-anchor="middle" class="text-small">{voltage}</text>
'''

    # Show designation if provided
    if designation:
        svg += f'''
  <text x="{cx}" y="{cy + 8}" text-anchor="middle" class="text">{designation}</text>
'''

    # Positive terminal (top)
    svg += f'''
  <line x1="{cx}" y1="5" x2="{cx}" y2="{body_y}" class="primary" style="stroke: #e74c3c;" />
  <circle cx="{cx}" cy="5" r="3" class="terminal" />
  <text x="{cx + 8}" y="8" class="text" style="fill: #e74c3c;">+</text>
'''

    # Negative terminal (bottom)
    svg += f'''
  <line x1="{cx}" y1="{body_y + body_height}" x2="{cx}" y2="{height - 5}" class="primary" style="stroke: #3498db;" />
  <circle cx="{cx}" cy="{height - 5}" r="3" class="terminal" />
  <text x="{cx + 8}" y="{height - 2}" class="text" style="fill: #3498db;">-</text>
'''

    svg += _svg_footer()
    return svg


def create_fuse_symbol(
    width: int = 40,
    height: int = 25,
    designation: str = "F1",
    rating: str = "10A",
    **kwargs
) -> str:
    """Create fuse symbol.

    IEC Symbol: Rectangle with line through.

    Args:
        width: Symbol width
        height: Symbol height
        designation: Fuse designation
        rating: Current rating

    Returns:
        SVG string for fuse
    """
    svg = _svg_header(width, height, f"0 0 {width} {height}")

    cx = width // 2
    cy = height // 2

    fuse_width = width - 16
    fuse_x = (width - fuse_width) // 2

    # Fuse body
    svg += f'''
  <rect x="{fuse_x}" y="{cy - 5}" width="{fuse_width}" height="10"
        rx="2" class="primary" style="fill: #f5f5f5;" />
  <line x1="{fuse_x}" y1="{cy}" x2="{fuse_x + fuse_width}" y2="{cy}" class="primary" />
'''

    # Connection lines
    svg += f'''
  <line x1="5" y1="{cy}" x2="{fuse_x}" y2="{cy}" class="primary" />
  <line x1="{fuse_x + fuse_width}" y1="{cy}" x2="{width - 5}" y2="{cy}" class="primary" />
'''

    # Terminals
    svg += f'''
  <circle cx="5" cy="{cy}" r="3" class="terminal" />
  <circle cx="{width - 5}" cy="{cy}" r="3" class="terminal" />
'''

    # Labels
    svg += f'''
  <text x="{cx}" y="{cy - 8}" text-anchor="middle" class="text">{designation}</text>
  <text x="{cx}" y="{height - 2}" text-anchor="middle" class="text-small">{rating}</text>
'''

    svg += _svg_footer()
    return svg


def create_circuit_breaker_symbol(
    width: int = 40,
    height: int = 35,
    designation: str = "Q1",
    rating: str = "16A",
    **kwargs
) -> str:
    """Create circuit breaker symbol.

    Args:
        width: Symbol width
        height: Symbol height
        designation: Breaker designation
        rating: Current rating

    Returns:
        SVG string for circuit breaker
    """
    svg = _svg_header(width, height, f"0 0 {width} {height}")

    cx = width // 2
    cy = height // 2

    # Circuit breaker representation
    svg += f'''
  <line x1="5" y1="{cy}" x2="{cx - 8}" y2="{cy}" class="primary" />
  <line x1="{cx - 8}" y1="{cy}" x2="{cx + 5}" y2="{cy - 12}" class="primary" />
  <line x1="{cx + 8}" y1="{cy}" x2="{width - 5}" y2="{cy}" class="primary" />
  <rect x="{cx - 3}" y="{cy - 3}" width="6" height="6" class="primary" style="fill: {COLORS['primary']};" />
'''

    # Terminals
    svg += f'''
  <circle cx="5" cy="{cy}" r="3" class="terminal" />
  <circle cx="{width - 5}" cy="{cy}" r="3" class="terminal" />
'''

    # Labels
    svg += f'''
  <text x="{cx}" y="8" text-anchor="middle" class="text">{designation}</text>
  <text x="{cx}" y="{height - 2}" text-anchor="middle" class="text-small">{rating}</text>
'''

    svg += _svg_footer()
    return svg


def create_switch_symbol(
    width: int = 40,
    height: int = 30,
    designation: str = "S1",
    normally_open: bool = True,
    switch_type: str = "push_button",
    **kwargs
) -> str:
    """Create switch symbol (push button, limit switch, etc.).

    Args:
        width: Symbol width
        height: Symbol height
        designation: Switch designation
        normally_open: True for NO, False for NC
        switch_type: Type of switch

    Returns:
        SVG string for switch
    """
    svg = _svg_header(width, height, f"0 0 {width} {height}")

    cx = width // 2
    cy = height // 2

    # Connection lines
    svg += f'''
  <line x1="5" y1="{cy}" x2="{cx - 8}" y2="{cy}" class="primary" />
  <line x1="{cx + 8}" y1="{cy}" x2="{width - 5}" y2="{cy}" class="primary" />
'''

    if normally_open:
        # NO switch - open contact
        svg += f'''
  <line x1="{cx - 8}" y1="{cy}" x2="{cx + 5}" y2="{cy - 10}" class="primary" />
'''
    else:
        # NC switch - closed contact with NC indicator
        svg += f'''
  <line x1="{cx - 8}" y1="{cy}" x2="{cx + 8}" y2="{cy}" class="primary" />
  <line x1="{cx - 2}" y1="{cy - 8}" x2="{cx + 2}" y2="{cy + 2}" class="primary" />
'''

    # Push button indicator
    if switch_type == "push_button":
        svg += f'''
  <line x1="{cx}" y1="{cy - 10}" x2="{cx}" y2="{cy - 15}" class="primary" />
  <line x1="{cx - 5}" y1="{cy - 15}" x2="{cx + 5}" y2="{cy - 15}" class="primary" />
'''
    elif switch_type == "limit_switch":
        # Roller lever indicator
        svg += f'''
  <circle cx="{cx}" cy="{cy - 12}" r="3" class="primary" style="fill: none;" />
  <line x1="{cx}" y1="{cy - 9}" x2="{cx}" y2="{cy - 5}" class="primary" />
'''

    # Terminals
    svg += f'''
  <circle cx="5" cy="{cy}" r="3" class="terminal" />
  <circle cx="{width - 5}" cy="{cy}" r="3" class="terminal" />
'''

    # Designation
    svg += f'''
  <text x="{cx}" y="{height - 2}" text-anchor="middle" class="text">{designation}</text>
'''

    svg += _svg_footer()
    return svg


def create_emergency_stop_symbol(
    width: int = 50,
    height: int = 40,
    designation: str = "S0",
    **kwargs
) -> str:
    """Create emergency stop symbol.

    Args:
        width: Symbol width
        height: Symbol height
        designation: E-stop designation

    Returns:
        SVG string for emergency stop
    """
    svg = _svg_header(width, height, f"0 0 {width} {height}")

    cx = width // 2
    cy = height // 2

    # E-stop button (mushroom head)
    svg += f'''
  <ellipse cx="{cx}" cy="{cy - 5}" rx="12" ry="6" class="primary" style="fill: #e74c3c;" />
  <rect x="{cx - 8}" y="{cy - 5}" width="16" height="10" class="primary" style="fill: #c0392b;" />
'''

    # NC contact representation (E-stops are typically NC)
    svg += f'''
  <line x1="5" y1="{cy + 8}" x2="{cx - 10}" y2="{cy + 8}" class="primary" />
  <line x1="{cx - 10}" y1="{cy + 8}" x2="{cx + 10}" y2="{cy + 8}" class="primary" />
  <line x1="{cx}" y1="{cy + 5}" x2="{cx}" y2="{cy + 11}" class="primary" />
  <line x1="{cx + 10}" y1="{cy + 8}" x2="{width - 5}" y2="{cy + 8}" class="primary" />
'''

    # Terminals
    svg += f'''
  <circle cx="5" cy="{cy + 8}" r="3" class="terminal" />
  <circle cx="{width - 5}" cy="{cy + 8}" r="3" class="terminal" />
'''

    # Designation
    svg += f'''
  <text x="{cx}" y="{height - 2}" text-anchor="middle" class="text" style="fill: #e74c3c; font-weight: bold;">{designation}</text>
'''

    svg += _svg_footer()
    return svg


def create_plc_io_symbol(
    width: int = 60,
    height: int = 80,
    designation: str = "A1",
    io_type: str = "input",
    num_channels: int = 8,
    **kwargs
) -> str:
    """Create PLC I/O module symbol.

    Args:
        width: Symbol width
        height: Symbol height
        designation: Module designation
        io_type: "input" or "output"
        num_channels: Number of I/O channels

    Returns:
        SVG string for PLC I/O module
    """
    svg = _svg_header(width, height, f"0 0 {width} {height}")

    cx = width // 2

    # Module body
    svg += f'''
  <rect x="10" y="10" width="{width - 20}" height="{height - 20}"
        rx="3" class="primary" style="fill: #ebedef;" />
  <text x="{cx}" y="25" text-anchor="middle" class="text" style="font-weight: bold;">{designation}</text>
  <text x="{cx}" y="35" text-anchor="middle" class="text-small">{io_type.upper()}</text>
'''

    # I/O channels
    channel_start_y = 40
    channel_spacing = (height - 50) // num_channels

    for i in range(min(num_channels, 8)):  # Limit display to 8 channels
        cy = channel_start_y + i * channel_spacing

        # Channel indicator
        svg += f'''
  <rect x="15" y="{cy - 3}" width="6" height="6" rx="1" class="primary" style="fill: #bdc3c7;" />
  <text x="25" y="{cy + 2}" class="text-small">{i}</text>
'''

        # Terminal on right side
        svg += f'''
  <line x1="{width - 15}" y1="{cy}" x2="{width - 5}" y2="{cy}" class="primary" />
  <circle cx="{width - 5}" cy="{cy}" r="2" class="terminal" />
'''

    svg += _svg_footer()
    return svg


def create_plc_input_state_symbol(
    width: int = 50,
    height: int = 40,
    designation: str = "I0.0",
    address: str = "I0.0",
    state: bool = False,
    **kwargs
) -> str:
    """Create PLC input state indicator symbol.

    A compact symbol showing PLC input state with LED indicator.
    Can be toggled ON/OFF for simulation.

    Args:
        width: Symbol width
        height: Symbol height
        designation: Component designation (e.g., "S1", "B1")
        address: PLC input address (e.g., "I0.0", "%IX0.0")
        state: Current state (True=ON/Green, False=OFF/Gray)

    Returns:
        SVG string for PLC input state indicator
    """
    svg = _svg_header(width, height, f"0 0 {width} {height}")

    cx = width // 2
    cy = height // 2

    # Body rectangle
    body_width = width - 10
    body_height = height - 10
    body_x = (width - body_width) // 2
    body_y = (height - body_height) // 2

    body_fill = '#f8f9fa'
    border_color = COLORS['primary']

    svg += f'''
  <rect x="{body_x}" y="{body_y}" width="{body_width}" height="{body_height}"
        rx="3" class="primary" style="fill: {body_fill}; stroke-width: 2;" />
'''

    # LED indicator (left side)
    led_x = body_x + 8
    led_y = cy
    led_radius = 5

    if state:
        # ON state - green LED
        led_color = COLORS['energized']
        led_stroke = '#1e8449'
    else:
        # OFF state - gray LED
        led_color = '#95a5a6'
        led_stroke = '#7f8c8d'

    svg += f'''
  <circle cx="{led_x}" cy="{led_y}" r="{led_radius}"
          style="fill: {led_color}; stroke: {led_stroke}; stroke-width: 1.5;" />
'''

    # Address label (center-right)
    text_x = led_x + led_radius + 5
    svg += f'''
  <text x="{text_x}" y="{cy + 3}" class="text" style="font-size: 9px; font-weight: bold;">{address}</text>
'''

    # Designation (bottom)
    svg += f'''
  <text x="{cx}" y="{body_y + body_height + 8}" text-anchor="middle" class="text-small">{designation}</text>
'''

    # Terminals (right side)
    terminal_x = body_x + body_width
    svg += f'''
  <line x1="{terminal_x}" y1="{cy}" x2="{width - 3}" y2="{cy}" class="primary" />
  <circle cx="{width - 3}" cy="{cy}" r="2" class="terminal" />
'''

    svg += _svg_footer()
    return svg


def create_indicator_light_symbol(
    width: int = 30,
    height: int = 30,
    designation: str = "H1",
    color: str = "green",
    **kwargs
) -> str:
    """Create indicator light symbol.

    Args:
        width: Symbol width
        height: Symbol height
        designation: Light designation
        color: Light color

    Returns:
        SVG string for indicator light
    """
    svg = _svg_header(width, height, f"0 0 {width} {height}")

    cx = width // 2
    cy = height // 2

    color_map = {
        'green': '#27ae60',
        'red': '#e74c3c',
        'yellow': '#f1c40f',
        'blue': '#3498db',
        'white': '#ecf0f1',
        'orange': '#e67e22'
    }
    fill = color_map.get(color.lower(), '#bdc3c7')

    # Light circle with X pattern (IEC symbol for lamp)
    svg += f'''
  <circle cx="{cx}" cy="{cy}" r="10" class="primary" style="fill: {fill};" />
  <line x1="{cx - 6}" y1="{cy - 6}" x2="{cx + 6}" y2="{cy + 6}" class="primary" />
  <line x1="{cx - 6}" y1="{cy + 6}" x2="{cx + 6}" y2="{cy - 6}" class="primary" />
'''

    # Terminals
    svg += f'''
  <line x1="{cx}" y1="{cy - 10}" x2="{cx}" y2="5" class="primary" />
  <circle cx="{cx}" cy="5" r="2" class="terminal" />
  <line x1="{cx}" y1="{cy + 10}" x2="{cx}" y2="{height - 5}" class="primary" />
  <circle cx="{cx}" cy="{height - 5}" r="2" class="terminal" />
'''

    # Designation
    svg += f'''
  <text x="{cx + 12}" y="{cy + 3}" class="text">{designation}</text>
'''

    svg += _svg_footer()
    return svg


def create_vfd_symbol(
    width: int = 70,
    height: int = 70,
    designation: str = "U1",
    voltage: str = "400VAC",
    **kwargs
) -> str:
    """Create Variable Frequency Drive (VFD) symbol.

    IEC Symbol: Rectangle with tilde (~) for AC input, equals (=) for DC bus,
    and tilde (~) for variable AC output.

    Args:
        width: Symbol width
        height: Symbol height
        designation: VFD designation
        voltage: Voltage rating

    Returns:
        SVG string for VFD symbol
    """
    svg = _svg_header(width, height, f"0 0 {width} {height}")

    cx = width // 2
    cy = height // 2

    # VFD body (rectangle)
    body_width = width - 16
    body_height = height - 20
    body_x = (width - body_width) // 2
    body_y = (height - body_height) // 2

    svg += f'''
  <rect x="{body_x}" y="{body_y}" width="{body_width}" height="{body_height}"
        rx="4" class="primary" style="fill: #eaf2f8;" />
'''

    # AC input indicator (tilde on left)
    svg += f'''
  <path d="M {body_x + 6} {cy - 8} Q {body_x + 10} {cy - 14} {body_x + 14} {cy - 8}
           Q {body_x + 18} {cy - 2} {body_x + 22} {cy - 8}"
        class="primary" style="fill: none; stroke-width: 1.5;" />
  <text x="{body_x + 14}" y="{cy + 4}" text-anchor="middle" class="text-small">AC</text>
'''

    # Separator line
    svg += f'''
  <line x1="{cx}" y1="{body_y + 4}" x2="{cx}" y2="{body_y + body_height - 4}"
        class="primary" style="stroke-width: 1; stroke-dasharray: 3,2;" />
'''

    # Variable AC output indicator (tilde with arrow on right)
    out_x = cx + 4
    svg += f'''
  <path d="M {out_x} {cy - 8} Q {out_x + 4} {cy - 14} {out_x + 8} {cy - 8}
           Q {out_x + 12} {cy - 2} {out_x + 16} {cy - 8}"
        class="primary" style="fill: none; stroke-width: 1.5;" />
  <text x="{out_x + 8}" y="{cy + 4}" text-anchor="middle" class="text-small">VAR</text>
'''

    # Designation (below body)
    svg += f'''
  <text x="{cx}" y="{body_y + body_height + 12}" text-anchor="middle" class="text" style="font-weight: bold;">{designation}</text>
'''

    # Input terminals (left side - 3 phase)
    terminal_spacing = 10
    for i, label in enumerate(["L1", "L2", "L3"]):
        ty = cy - terminal_spacing + i * terminal_spacing
        svg += f'''
  <line x1="3" y1="{ty}" x2="{body_x}" y2="{ty}" class="primary" />
  <circle cx="3" cy="{ty}" r="2" class="terminal" />
'''

    # Output terminals (right side - 3 phase to motor)
    for i, label in enumerate(["U", "V", "W"]):
        ty = cy - terminal_spacing + i * terminal_spacing
        svg += f'''
  <line x1="{body_x + body_width}" y1="{ty}" x2="{width - 3}" y2="{ty}" class="primary" />
  <circle cx="{width - 3}" cy="{ty}" r="2" class="terminal" />
'''

    svg += _svg_footer()
    return svg


# Mapping of component types to symbol generators
SYMBOL_GENERATORS = {
    'relay': create_relay_symbol,
    'contactor': create_relay_symbol,
    'motor': create_motor_symbol,
    'vfd': create_vfd_symbol,
    'proximity_sensor': lambda **kwargs: create_sensor_symbol(sensor_type='proximity', **kwargs),
    'photoelectric_sensor': lambda **kwargs: create_sensor_symbol(sensor_type='photoelectric', **kwargs),
    'limit_switch': lambda **kwargs: create_switch_symbol(switch_type='limit_switch', **kwargs),
    'push_button': lambda **kwargs: create_switch_symbol(switch_type='push_button', **kwargs),
    'emergency_stop': create_emergency_stop_symbol,
    'power_24vdc': create_power_supply_symbol,
    'power_400vac': lambda **kwargs: create_power_supply_symbol(voltage='400VAC', **kwargs),
    'power_230vac': lambda **kwargs: create_power_supply_symbol(voltage='230VAC', **kwargs),
    'fuse': create_fuse_symbol,
    'circuit_breaker': create_circuit_breaker_symbol,
    'plc_input': lambda **kwargs: create_plc_io_symbol(io_type='input', **kwargs),
    'plc_output': lambda **kwargs: create_plc_io_symbol(io_type='output', **kwargs),
    'plc_input_state': create_plc_input_state_symbol,
    'indicator_light': create_indicator_light_symbol,
}


def get_component_symbol(
    component_type: str,
    designation: str = "",
    contacts: Optional[List[ContactConfig]] = None,
    energized: bool = False,
    normally_open: bool = True,
    state: bool = False,
    address: str = "",
    **kwargs
) -> str:
    """Get SVG symbol for a component type.

    Args:
        component_type: Type of component (lowercase)
        designation: Component designation
        contacts: Contact configurations for relays/contactors
        energized: Energization state
        normally_open: NO/NC configuration for switches
        state: Component state (for PLC inputs, switches, etc.)
        address: PLC address (for PLC input state)
        **kwargs: Additional arguments for specific symbols

    Returns:
        SVG string for the component symbol
    """
    comp_type = component_type.lower().replace(' ', '_')

    generator = SYMBOL_GENERATORS.get(comp_type)

    if generator:
        try:
            if comp_type in ['relay', 'contactor']:
                return generator(
                    designation=designation,
                    contacts=contacts,
                    energized=energized,
                    **kwargs
                )
            elif comp_type in ['limit_switch', 'push_button']:
                return generator(
                    designation=designation,
                    normally_open=normally_open,
                    **kwargs
                )
            elif comp_type in ['proximity_sensor', 'photoelectric_sensor']:
                return generator(
                    designation=designation,
                    normally_open=normally_open,
                    **kwargs
                )
            elif comp_type == 'plc_input_state':
                # Use address if provided, otherwise use designation
                display_address = address if address else designation
                return generator(
                    designation=designation,
                    address=display_address,
                    state=state,
                    **kwargs
                )
            else:
                return generator(designation=designation, **kwargs)
        except Exception as e:
            print(f"Error generating symbol for {component_type}: {e}")

    # Default fallback: simple rectangle
    return _create_default_symbol(designation, component_type)


def _create_default_symbol(designation: str, component_type: str) -> str:
    """Create default symbol for unknown component types.

    Args:
        designation: Component designation
        component_type: Type name

    Returns:
        SVG string for default symbol
    """
    svg = _svg_header(60, 40, "0 0 60 40")
    svg += f'''
  <rect x="5" y="5" width="50" height="30" rx="3" class="primary" style="fill: #f8f9fa;" />
  <text x="30" y="18" text-anchor="middle" class="text">{designation or '?'}</text>
  <text x="30" y="28" text-anchor="middle" class="text-small">{component_type[:10]}</text>
  <circle cx="5" cy="20" r="3" class="terminal" />
  <circle cx="55" cy="20" r="3" class="terminal" />
'''
    svg += _svg_footer()
    return svg
