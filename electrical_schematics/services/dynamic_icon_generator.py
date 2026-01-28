"""Dynamic SVG icon generator for electrical components based on IEC 60617 standards."""

import logging
from typing import Optional
from electrical_schematics.services.contact_parser import ContactConfiguration

logger = logging.getLogger(__name__)


class DynamicIconGenerator:
    """Generates IEC 60617 compliant SVG icons for electrical components.

    Creates schematic symbols with correct contact numbering:
    - NO contacts: 13-14, 23-24, 33-34, 43-44...
    - NC contacts: 11-12, 21-22, 31-32, 41-42...
    - Coil terminals: A1, A2
    - Power contacts: 1-2, 3-4, 5-6 (for contactors)
    """

    # SVG styling
    STROKE_WIDTH = 2
    STROKE_COLOR = "#000000"
    FILL_COLOR = "none"
    TEXT_COLOR = "#000000"
    FONT_SIZE = 12
    FONT_FAMILY = "Arial, sans-serif"

    # Component dimensions
    CONTACT_HEIGHT = 40
    CONTACT_WIDTH = 30
    CONTACT_SPACING = 20
    COIL_HEIGHT = 60
    COIL_WIDTH = 40
    TERMINAL_SIZE = 15
    PADDING = 10

    def generate_icon(
        self,
        config: ContactConfiguration,
        width: Optional[int] = None,
        height: Optional[int] = None
    ) -> str:
        """Generate SVG icon based on contact configuration.

        Args:
            config: Contact configuration parsed from description
            width: Optional fixed width (auto-calculated if None)
            height: Optional fixed height (auto-calculated if None)

        Returns:
            SVG markup as string
        """
        if config.component_type == 'relay':
            return self._generate_relay_icon(config, width, height)
        elif config.component_type == 'contactor':
            return self._generate_contactor_icon(config, width, height)
        elif config.component_type == 'terminal_block':
            return self._generate_terminal_block_icon(config, width, height)
        elif config.component_type == 'switch':
            return self._generate_switch_icon(config, width, height)
        elif config.component_type == 'circuit_breaker':
            return self._generate_breaker_icon(config, width, height)
        else:
            return self._generate_generic_icon(config, width, height)

    def _generate_relay_icon(
        self,
        config: ContactConfiguration,
        width: Optional[int],
        height: Optional[int]
    ) -> str:
        """Generate relay icon with coil and contacts.

        Args:
            config: Contact configuration
            width: Optional fixed width
            height: Optional fixed height

        Returns:
            SVG markup
        """
        total_contacts = config.no_contacts + config.nc_contacts

        # Calculate dimensions
        if width is None:
            width = (self.COIL_WIDTH + self.CONTACT_WIDTH * total_contacts +
                     self.CONTACT_SPACING * (total_contacts + 1) + self.PADDING * 2)
        if height is None:
            height = self.COIL_HEIGHT + self.PADDING * 2

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<rect width="{width}" height="{height}" fill="white" stroke="none"/>',
        ]

        # Draw coil on the left (A1, A2)
        coil_x = self.PADDING
        coil_y = self.PADDING
        svg_parts.append(self._draw_coil(coil_x, coil_y, self.COIL_WIDTH, self.COIL_HEIGHT))

        # Draw contacts to the right of coil
        contact_x = coil_x + self.COIL_WIDTH + self.CONTACT_SPACING
        contact_y = coil_y + (self.COIL_HEIGHT - self.CONTACT_HEIGHT) // 2

        # Draw NO contacts first (13-14, 23-24, ...)
        for i in range(config.no_contacts):
            pole_num = i + 1
            svg_parts.append(self._draw_no_contact(
                contact_x, contact_y, pole_num
            ))
            contact_x += self.CONTACT_WIDTH + self.CONTACT_SPACING

        # Draw NC contacts (11-12, 21-22, ...)
        for i in range(config.nc_contacts):
            pole_num = config.no_contacts + i + 1
            svg_parts.append(self._draw_nc_contact(
                contact_x, contact_y, pole_num
            ))
            contact_x += self.CONTACT_WIDTH + self.CONTACT_SPACING

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    def _generate_contactor_icon(
        self,
        config: ContactConfiguration,
        width: Optional[int],
        height: Optional[int]
    ) -> str:
        """Generate contactor icon with power and auxiliary contacts.

        Args:
            config: Contact configuration
            width: Optional fixed width
            height: Optional fixed height

        Returns:
            SVG markup
        """
        # Contactors have main power contacts (1-2, 3-4, 5-6) and auxiliary contacts
        total_contacts = config.power_contacts + config.no_contacts + config.nc_contacts

        if width is None:
            width = (self.COIL_WIDTH + self.CONTACT_WIDTH * total_contacts +
                     self.CONTACT_SPACING * (total_contacts + 1) + self.PADDING * 2)
        if height is None:
            height = self.COIL_HEIGHT + self.PADDING * 2

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<rect width="{width}" height="{height}" fill="white" stroke="none"/>',
        ]

        # Draw coil
        coil_x = self.PADDING
        coil_y = self.PADDING
        svg_parts.append(self._draw_coil(coil_x, coil_y, self.COIL_WIDTH, self.COIL_HEIGHT))

        # Draw contacts
        contact_x = coil_x + self.COIL_WIDTH + self.CONTACT_SPACING
        contact_y = coil_y + (self.COIL_HEIGHT - self.CONTACT_HEIGHT) // 2

        # Draw power contacts (1-2, 3-4, 5-6)
        for i in range(config.power_contacts):
            top_label = str(2 * i + 1)
            bottom_label = str(2 * i + 2)
            svg_parts.append(self._draw_power_contact(
                contact_x, contact_y, top_label, bottom_label
            ))
            contact_x += self.CONTACT_WIDTH + self.CONTACT_SPACING

        # Draw auxiliary NO contacts
        for i in range(config.no_contacts):
            pole_num = i + 1
            svg_parts.append(self._draw_no_contact(
                contact_x, contact_y, pole_num
            ))
            contact_x += self.CONTACT_WIDTH + self.CONTACT_SPACING

        # Draw auxiliary NC contacts
        for i in range(config.nc_contacts):
            pole_num = config.no_contacts + i + 1
            svg_parts.append(self._draw_nc_contact(
                contact_x, contact_y, pole_num
            ))
            contact_x += self.CONTACT_WIDTH + self.CONTACT_SPACING

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    def _generate_terminal_block_icon(
        self,
        config: ContactConfiguration,
        width: Optional[int],
        height: Optional[int]
    ) -> str:
        """Generate terminal block icon with numbered positions.

        Args:
            config: Contact configuration
            width: Optional fixed width
            height: Optional fixed height

        Returns:
            SVG markup
        """
        positions = config.positions if config.positions > 0 else 10

        if width is None:
            width = self.TERMINAL_SIZE * positions + self.CONTACT_SPACING * (positions - 1) + self.PADDING * 2
        if height is None:
            height = self.TERMINAL_SIZE * 3 + self.PADDING * 2

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<rect width="{width}" height="{height}" fill="white" stroke="none"/>',
        ]

        # Draw terminal positions
        x = self.PADDING
        y = self.PADDING + self.TERMINAL_SIZE

        for i in range(positions):
            # Terminal circle
            cx = x + self.TERMINAL_SIZE // 2
            cy = y
            svg_parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="{self.TERMINAL_SIZE // 2}" '
                f'fill="none" stroke="{self.STROKE_COLOR}" stroke-width="{self.STROKE_WIDTH}"/>'
            )

            # Position number
            text_y = y + self.TERMINAL_SIZE + self.FONT_SIZE
            svg_parts.append(
                f'<text x="{cx}" y="{text_y}" text-anchor="middle" '
                f'font-family="{self.FONT_FAMILY}" font-size="{self.FONT_SIZE}" '
                f'fill="{self.TEXT_COLOR}">{i + 1}</text>'
            )

            x += self.TERMINAL_SIZE + self.CONTACT_SPACING

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    def _generate_switch_icon(
        self,
        config: ContactConfiguration,
        width: Optional[int],
        height: Optional[int]
    ) -> str:
        """Generate switch icon.

        Args:
            config: Contact configuration
            width: Optional fixed width
            height: Optional fixed height

        Returns:
            SVG markup
        """
        # Similar to relay contacts but without coil
        return self._generate_relay_icon(config, width, height)

    def _generate_breaker_icon(
        self,
        config: ContactConfiguration,
        width: Optional[int],
        height: Optional[int]
    ) -> str:
        """Generate circuit breaker icon.

        Args:
            config: Contact configuration
            width: Optional fixed width
            height: Optional fixed height

        Returns:
            SVG markup
        """
        if width is None:
            width = 60
        if height is None:
            height = 80

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<rect width="{width}" height="{height}" fill="white" stroke="none"/>',
        ]

        # Simple breaker symbol
        center_x = width // 2
        center_y = height // 2

        # Vertical line
        svg_parts.append(
            f'<line x1="{center_x}" y1="{self.PADDING}" x2="{center_x}" y2="{height - self.PADDING}" '
            f'stroke="{self.STROKE_COLOR}" stroke-width="{self.STROKE_WIDTH * 2}"/>'
        )

        # Square in middle
        square_size = 20
        square_x = center_x - square_size // 2
        square_y = center_y - square_size // 2
        svg_parts.append(
            f'<rect x="{square_x}" y="{square_y}" width="{square_size}" height="{square_size}" '
            f'fill="white" stroke="{self.STROKE_COLOR}" stroke-width="{self.STROKE_WIDTH}"/>'
        )

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    def _generate_generic_icon(
        self,
        config: ContactConfiguration,
        width: Optional[int],
        height: Optional[int]
    ) -> str:
        """Generate generic component icon.

        Args:
            config: Contact configuration
            width: Optional fixed width
            height: Optional fixed height

        Returns:
            SVG markup
        """
        if width is None:
            width = 60
        if height is None:
            height = 60

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<rect width="{width}" height="{height}" fill="white" stroke="none"/>',
        ]

        # Generic box
        box_margin = self.PADDING
        svg_parts.append(
            f'<rect x="{box_margin}" y="{box_margin}" '
            f'width="{width - 2 * box_margin}" height="{height - 2 * box_margin}" '
            f'fill="white" stroke="{self.STROKE_COLOR}" stroke-width="{self.STROKE_WIDTH}"/>'
        )

        # "?" in center
        text_x = width // 2
        text_y = height // 2 + self.FONT_SIZE // 2
        svg_parts.append(
            f'<text x="{text_x}" y="{text_y}" text-anchor="middle" '
            f'font-family="{self.FONT_FAMILY}" font-size="{self.FONT_SIZE * 2}" '
            f'fill="{self.TEXT_COLOR}">?</text>'
        )

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    # Helper methods for drawing components

    def _draw_coil(self, x: float, y: float, width: float, height: float) -> str:
        """Draw coil symbol (rectangle with zigzag).

        Args:
            x, y: Top-left corner
            width, height: Dimensions

        Returns:
            SVG markup
        """
        parts = []

        # Coil rectangle
        parts.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
            f'fill="none" stroke="{self.STROKE_COLOR}" stroke-width="{self.STROKE_WIDTH}"/>'
        )

        # Terminal labels
        parts.append(
            f'<text x="{x + width // 2}" y="{y - 5}" text-anchor="middle" '
            f'font-family="{self.FONT_FAMILY}" font-size="{self.FONT_SIZE}" '
            f'fill="{self.TEXT_COLOR}">A1</text>'
        )
        parts.append(
            f'<text x="{x + width // 2}" y="{y + height + self.FONT_SIZE + 2}" text-anchor="middle" '
            f'font-family="{self.FONT_FAMILY}" font-size="{self.FONT_SIZE}" '
            f'fill="{self.TEXT_COLOR}">A2</text>'
        )

        return '\n'.join(parts)

    def _draw_no_contact(self, x: float, y: float, pole_num: int) -> str:
        """Draw normally open contact (IEC 60617).

        Args:
            x, y: Top-left corner
            pole_num: Pole number (1, 2, 3, ...)

        Returns:
            SVG markup
        """
        parts = []

        # Contact line (with gap for NO)
        mid_x = x + self.CONTACT_WIDTH // 2
        top_y = y
        bottom_y = y + self.CONTACT_HEIGHT
        gap_y1 = y + self.CONTACT_HEIGHT // 3
        gap_y2 = y + 2 * self.CONTACT_HEIGHT // 3

        # Top line
        parts.append(
            f'<line x1="{mid_x}" y1="{top_y}" x2="{mid_x}" y2="{gap_y1}" '
            f'stroke="{self.STROKE_COLOR}" stroke-width="{self.STROKE_WIDTH}"/>'
        )

        # Gap (angled line showing contact open)
        parts.append(
            f'<line x1="{mid_x}" y1="{gap_y1}" x2="{mid_x + 5}" y2="{gap_y2 - 5}" '
            f'stroke="{self.STROKE_COLOR}" stroke-width="{self.STROKE_WIDTH}"/>'
        )

        # Bottom line
        parts.append(
            f'<line x1="{mid_x}" y1="{gap_y2}" x2="{mid_x}" y2="{bottom_y}" '
            f'stroke="{self.STROKE_COLOR}" stroke-width="{self.STROKE_WIDTH}"/>'
        )

        # Terminal labels (IEC: 13-14, 23-24, ...)
        top_label = f"{pole_num}3"
        bottom_label = f"{pole_num}4"

        parts.append(
            f'<text x="{mid_x - 8}" y="{top_y + 5}" text-anchor="end" '
            f'font-family="{self.FONT_FAMILY}" font-size="{self.FONT_SIZE - 2}" '
            f'fill="{self.TEXT_COLOR}">{top_label}</text>'
        )
        parts.append(
            f'<text x="{mid_x - 8}" y="{bottom_y}" text-anchor="end" '
            f'font-family="{self.FONT_FAMILY}" font-size="{self.FONT_SIZE - 2}" '
            f'fill="{self.TEXT_COLOR}">{bottom_label}</text>'
        )

        return '\n'.join(parts)

    def _draw_nc_contact(self, x: float, y: float, pole_num: int) -> str:
        """Draw normally closed contact (IEC 60617).

        Args:
            x, y: Top-left corner
            pole_num: Pole number (1, 2, 3, ...)

        Returns:
            SVG markup
        """
        parts = []

        # Contact line (closed with slash)
        mid_x = x + self.CONTACT_WIDTH // 2
        top_y = y
        bottom_y = y + self.CONTACT_HEIGHT

        # Continuous line
        parts.append(
            f'<line x1="{mid_x}" y1="{top_y}" x2="{mid_x}" y2="{bottom_y}" '
            f'stroke="{self.STROKE_COLOR}" stroke-width="{self.STROKE_WIDTH}"/>'
        )

        # Slash through line (indicates NC)
        slash_y = y + self.CONTACT_HEIGHT // 2
        parts.append(
            f'<line x1="{mid_x - 8}" y1="{slash_y - 8}" x2="{mid_x + 8}" y2="{slash_y + 8}" '
            f'stroke="{self.STROKE_COLOR}" stroke-width="{self.STROKE_WIDTH}"/>'
        )

        # Terminal labels (IEC: 11-12, 21-22, ...)
        top_label = f"{pole_num}1"
        bottom_label = f"{pole_num}2"

        parts.append(
            f'<text x="{mid_x - 10}" y="{top_y + 5}" text-anchor="end" '
            f'font-family="{self.FONT_FAMILY}" font-size="{self.FONT_SIZE - 2}" '
            f'fill="{self.TEXT_COLOR}">{top_label}</text>'
        )
        parts.append(
            f'<text x="{mid_x - 10}" y="{bottom_y}" text-anchor="end" '
            f'font-family="{self.FONT_FAMILY}" font-size="{self.FONT_SIZE - 2}" '
            f'fill="{self.TEXT_COLOR}">{bottom_label}</text>'
        )

        return '\n'.join(parts)

    def _draw_power_contact(
        self,
        x: float,
        y: float,
        top_label: str,
        bottom_label: str
    ) -> str:
        """Draw power contact for contactor (heavier line).

        Args:
            x, y: Top-left corner
            top_label: Top terminal label (e.g., "1")
            bottom_label: Bottom terminal label (e.g., "2")

        Returns:
            SVG markup
        """
        parts = []

        mid_x = x + self.CONTACT_WIDTH // 2
        top_y = y
        bottom_y = y + self.CONTACT_HEIGHT

        # Heavy line for power contact
        parts.append(
            f'<line x1="{mid_x}" y1="{top_y}" x2="{mid_x}" y2="{bottom_y}" '
            f'stroke="{self.STROKE_COLOR}" stroke-width="{self.STROKE_WIDTH * 2}"/>'
        )

        # Terminal labels
        parts.append(
            f'<text x="{mid_x - 8}" y="{top_y + 5}" text-anchor="end" '
            f'font-family="{self.FONT_FAMILY}" font-size="{self.FONT_SIZE - 2}" '
            f'fill="{self.TEXT_COLOR}">{top_label}</text>'
        )
        parts.append(
            f'<text x="{mid_x - 8}" y="{bottom_y}" text-anchor="end" '
            f'font-family="{self.FONT_FAMILY}" font-size="{self.FONT_SIZE - 2}" '
            f'fill="{self.TEXT_COLOR}">{bottom_label}</text>'
        )

        return '\n'.join(parts)
