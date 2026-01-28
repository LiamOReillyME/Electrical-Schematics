"""Dynamic SVG icon generator for terminal strips.

Generates scalable SVG icons for DIN rail terminal blocks that
expand based on the number of terminal positions.
"""

from typing import Optional
from electrical_schematics.models.terminal_strip import (
    TerminalStrip,
    TerminalStripType,
    TerminalColor
)


class TerminalStripIconGenerator:
    """Generates SVG icons for terminal strips."""

    # Standard dimensions (in SVG units)
    POSITION_WIDTH = 20      # Width per terminal position
    TERMINAL_HEIGHT = 60     # Total height of terminal
    DIN_RAIL_HEIGHT = 8      # Height of DIN rail mounting
    TERMINAL_BODY_HEIGHT = 40  # Height of terminal body
    TERMINAL_PAD_SIZE = 6    # Size of connection pad
    SCREW_SIZE = 4           # Size of terminal screw

    # Color mappings
    COLOR_MAP = {
        TerminalColor.GRAY: "#808080",
        TerminalColor.BLUE: "#0066CC",
        TerminalColor.GREEN_YELLOW: "#CCFF00",
        TerminalColor.RED: "#CC0000",
        TerminalColor.ORANGE: "#FF8800",
        TerminalColor.BROWN: "#8B4513",
        TerminalColor.BLACK: "#000000"
    }

    @classmethod
    def generate_svg(cls, terminal_strip: TerminalStrip, width: int = 200, height: int = 80) -> str:
        """Generate SVG icon for a terminal strip.

        The icon dynamically expands based on position_count and includes:
        - DIN rail mounting representation
        - Terminal positions with connection points
        - Terminal numbering
        - Color coding
        - Special indicators (LED, fuse, disconnect)

        Args:
            terminal_strip: TerminalStrip instance to render
            width: Desired SVG width
            height: Desired SVG height

        Returns:
            SVG markup as string
        """
        # Calculate actual width based on position count
        actual_width = cls.POSITION_WIDTH * terminal_strip.position_count
        viewbox_width = actual_width
        viewbox_height = cls.TERMINAL_HEIGHT

        # Get body color
        body_color = cls.COLOR_MAP.get(terminal_strip.color, "#808080")

        # Build SVG
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {viewbox_width} {viewbox_height}" '
            f'width="{width}" height="{height}">',
        ]

        # Add DIN rail
        svg_parts.append(cls._draw_din_rail(viewbox_width))

        # Add terminal body
        svg_parts.append(cls._draw_terminal_body(
            terminal_strip, viewbox_width, body_color
        ))

        # Add terminal positions
        for i in range(terminal_strip.position_count):
            x_pos = i * cls.POSITION_WIDTH + cls.POSITION_WIDTH / 2
            svg_parts.append(cls._draw_terminal_position(
                x_pos, i + 1, terminal_strip
            ))

        # Add special features
        if terminal_strip.has_led:
            svg_parts.append(cls._draw_led_indicators(terminal_strip))

        if terminal_strip.has_fuse:
            svg_parts.append(cls._draw_fuse_indicators(terminal_strip))

        # Add designation label
        svg_parts.append(cls._draw_designation_label(
            terminal_strip.designation, viewbox_width
        ))

        svg_parts.append('</svg>')

        return '\n'.join(svg_parts)

    @classmethod
    def _draw_din_rail(cls, width: float) -> str:
        """Draw DIN rail mounting at top.

        Args:
            width: Total width of the terminal strip

        Returns:
            SVG markup for DIN rail
        """
        rail_y = 0
        return f'''
        <g id="din-rail">
            <rect x="0" y="{rail_y}" width="{width}" height="{cls.DIN_RAIL_HEIGHT}"
                  fill="#C0C0C0" stroke="#808080" stroke-width="0.5"/>
            <line x1="0" y1="{rail_y + 2}" x2="{width}" y2="{rail_y + 2}"
                  stroke="#E0E0E0" stroke-width="1"/>
        </g>
        '''

    @classmethod
    def _draw_terminal_body(cls, terminal_strip: TerminalStrip, width: float, color: str) -> str:
        """Draw main terminal body.

        Args:
            terminal_strip: Terminal strip instance
            width: Total width
            color: Body color

        Returns:
            SVG markup for terminal body
        """
        body_y = cls.DIN_RAIL_HEIGHT
        body_height = cls.TERMINAL_BODY_HEIGHT

        # Multi-level terminals have stacked appearance
        if terminal_strip.level_count > 1:
            level_height = body_height / terminal_strip.level_count
            levels = []
            for level in range(terminal_strip.level_count):
                level_y = body_y + (level * level_height)
                level_shade = 1.0 - (level * 0.15)  # Darker for each level
                levels.append(f'''
                <rect x="0" y="{level_y}" width="{width}" height="{level_height}"
                      fill="{color}" opacity="{level_shade}"
                      stroke="#404040" stroke-width="0.5"/>
                ''')
            return '<g id="terminal-body">' + ''.join(levels) + '</g>'
        else:
            return f'''
            <g id="terminal-body">
                <rect x="0" y="{body_y}" width="{width}" height="{body_height}"
                      fill="{color}" stroke="#404040" stroke-width="1"/>
            </g>
            '''

    @classmethod
    def _draw_terminal_position(cls, x_center: float, position: int,
                                terminal_strip: TerminalStrip) -> str:
        """Draw a single terminal position with connection points.

        Args:
            x_center: X center position
            position: Terminal position number (1-indexed)
            terminal_strip: Parent terminal strip

        Returns:
            SVG markup for terminal position
        """
        body_y = cls.DIN_RAIL_HEIGHT
        body_height = cls.TERMINAL_BODY_HEIGHT

        parts = [f'<g id="position-{position}">']

        # Draw connection points for each level
        level_height = body_height / terminal_strip.level_count
        for level in range(terminal_strip.level_count):
            level_y = body_y + (level * level_height) + level_height / 2

            # Top connection pad
            top_y = level_y - 8
            parts.append(f'''
            <circle cx="{x_center}" cy="{top_y}" r="{cls.TERMINAL_PAD_SIZE}"
                    fill="#FFD700" stroke="#B8860B" stroke-width="0.5"/>
            ''')

            # Terminal screw (decorative)
            parts.append(f'''
            <circle cx="{x_center}" cy="{level_y}" r="{cls.SCREW_SIZE}"
                    fill="#606060" stroke="#404040" stroke-width="0.5"/>
            <line x1="{x_center - 2}" y1="{level_y}" x2="{x_center + 2}" y2="{level_y}"
                  stroke="#808080" stroke-width="0.5"/>
            ''')

            # Bottom connection pad
            bottom_y = level_y + 8
            parts.append(f'''
            <circle cx="{x_center}" cy="{bottom_y}" r="{cls.TERMINAL_PAD_SIZE}"
                    fill="#FFD700" stroke="#B8860B" stroke-width="0.5"/>
            ''')

        # Terminal number label
        label_y = body_y + body_height + 8
        terminal = terminal_strip.get_terminal(position)
        label_text = terminal.terminal_number if terminal else str(position)

        parts.append(f'''
        <text x="{x_center}" y="{label_y}"
              font-family="Arial, sans-serif" font-size="6"
              text-anchor="middle" fill="#000000">{label_text}</text>
        ''')

        # Disconnect indicator (knife symbol)
        if terminal_strip.has_disconnect:
            disconnect_y = body_y + body_height / 2
            parts.append(f'''
            <line x1="{x_center - 3}" y1="{disconnect_y}"
                  x2="{x_center + 3}" y2="{disconnect_y}"
                  stroke="#FF0000" stroke-width="1.5" stroke-dasharray="2,1"/>
            ''')

        parts.append('</g>')
        return '\n'.join(parts)

    @classmethod
    def _draw_led_indicators(cls, terminal_strip: TerminalStrip) -> str:
        """Draw LED indicators if present.

        Args:
            terminal_strip: Terminal strip instance

        Returns:
            SVG markup for LED indicators
        """
        parts = ['<g id="led-indicators">']

        for i, terminal in enumerate(terminal_strip.terminals):
            if terminal.has_led:
                x_pos = i * cls.POSITION_WIDTH + cls.POSITION_WIDTH / 2
                led_y = cls.DIN_RAIL_HEIGHT + 5

                led_color = terminal.led_color or "red"
                parts.append(f'''
                <circle cx="{x_pos + 5}" cy="{led_y}" r="2.5"
                        fill="{led_color}" stroke="#404040" stroke-width="0.3"
                        opacity="0.7"/>
                ''')

        parts.append('</g>')
        return '\n'.join(parts)

    @classmethod
    def _draw_fuse_indicators(cls, terminal_strip: TerminalStrip) -> str:
        """Draw fuse holder indicators.

        Args:
            terminal_strip: Terminal strip instance

        Returns:
            SVG markup for fuse indicators
        """
        parts = ['<g id="fuse-indicators">']

        body_y = cls.DIN_RAIL_HEIGHT
        body_height = cls.TERMINAL_BODY_HEIGHT

        for i in range(terminal_strip.position_count):
            x_pos = i * cls.POSITION_WIDTH + cls.POSITION_WIDTH / 2
            fuse_y = body_y + body_height / 2

            # Draw fuse outline
            parts.append(f'''
            <rect x="{x_pos - 3}" y="{fuse_y - 8}" width="6" height="16"
                  fill="none" stroke="#FF6600" stroke-width="1"
                  stroke-dasharray="1,1" rx="1"/>
            <text x="{x_pos}" y="{fuse_y + 2}"
                  font-family="Arial, sans-serif" font-size="4"
                  text-anchor="middle" fill="#FF6600">F</text>
            ''')

        parts.append('</g>')
        return '\n'.join(parts)

    @classmethod
    def _draw_designation_label(cls, designation: str, width: float) -> str:
        """Draw designation label.

        Args:
            designation: Terminal strip designation
            width: Total width

        Returns:
            SVG markup for designation label
        """
        label_y = cls.TERMINAL_HEIGHT - 5
        return f'''
        <g id="designation-label">
            <text x="{width / 2}" y="{label_y}"
                  font-family="Arial, sans-serif" font-size="8" font-weight="bold"
                  text-anchor="middle" fill="#000000">{designation}</text>
        </g>
        '''

    @classmethod
    def generate_for_library(cls, terminal_strip: TerminalStrip) -> str:
        """Generate library preview icon (standard size).

        Args:
            terminal_strip: Terminal strip to render

        Returns:
            SVG markup optimized for library display
        """
        # Calculate optimal width based on position count
        if terminal_strip.position_count <= 2:
            width = 60
        elif terminal_strip.position_count <= 4:
            width = 100
        elif terminal_strip.position_count <= 10:
            width = 150
        else:
            width = 200

        return cls.generate_svg(terminal_strip, width=width, height=60)

    @classmethod
    def generate_for_schematic(cls, terminal_strip: TerminalStrip,
                               scale: float = 1.0) -> str:
        """Generate icon for schematic placement (scalable).

        Args:
            terminal_strip: Terminal strip to render
            scale: Scale factor for icon size

        Returns:
            SVG markup for schematic placement
        """
        base_width = terminal_strip.position_count * 30  # More space in schematics
        base_height = 100

        width = int(base_width * scale)
        height = int(base_height * scale)

        return cls.generate_svg(terminal_strip, width=width, height=height)


def generate_preview_grid(terminal_strips: list) -> str:
    """Generate preview grid showing multiple terminal strips.

    Args:
        terminal_strips: List of TerminalStrip instances

    Returns:
        HTML with SVG previews in a grid layout
    """
    html_parts = [
        '<html><head><style>',
        'body { font-family: Arial, sans-serif; padding: 20px; }',
        '.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }',
        '.item { border: 1px solid #ccc; padding: 10px; border-radius: 5px; }',
        '.item h3 { margin: 0 0 5px 0; font-size: 14px; }',
        '.item .specs { font-size: 11px; color: #666; margin: 5px 0; }',
        '</style></head><body>',
        '<h1>Terminal Strip Library</h1>',
        '<div class="grid">'
    ]

    for ts in terminal_strips:
        svg = TerminalStripIconGenerator.generate_for_library(ts)
        html_parts.append(f'''
        <div class="item">
            <h3>{ts.get_display_name()}</h3>
            <div class="specs">{ts.get_specification_summary()}</div>
            {svg}
        </div>
        ''')

    html_parts.append('</div></body></html>')
    return '\n'.join(html_parts)
