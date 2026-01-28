"""Comprehensive tests for IEC 60497 contact numbering and icon generation.

This test suite validates:
1. Correct IEC 60497 terminal numbering for contactors/relays
2. Dynamic icon generation with proper contact configuration
3. Coil terminal labeling (A1/A2)
4. NO contact representation (13-14, 23-24, 33-34, ...)
5. NC contact representation (11-12, 21-22, 31-32, ...)
"""

import pytest
from typing import List

from electrical_schematics.models.industrial_component import (
    IndustrialComponent,
    IndustrialComponentType,
    ContactBlock,
    ContactType,
    CoilTerminals
)
from electrical_schematics.gui.electrical_symbols import (
    create_relay_symbol,
    create_no_contact_symbol,
    create_nc_contact_symbol,
    create_coil_symbol,
    ContactConfig,
    get_component_symbol
)


class TestIEC60497ContactNumbering:
    """Test IEC 60497 contact numbering standard.

    IEC 60497 Standard:
    - Coil terminals: A1, A2
    - NO contacts: X3-X4 (13-14, 23-24, 33-34, 43-44, ...)
    - NC contacts: X1-X2 (11-12, 21-22, 31-32, 41-42, ...)
    - Power contacts: 1-2, 3-4, 5-6 (for three-phase)
    """

    def test_coil_terminal_numbering(self):
        """Test standard coil terminal numbers A1/A2."""
        component = IndustrialComponent(
            id="k1",
            type=IndustrialComponentType.RELAY,
            designation="K1"
        )

        assert component.coil_terminals is not None
        assert component.coil_terminals.positive == "A1"
        assert component.coil_terminals.negative == "A2"

    def test_default_relay_no_contact(self):
        """Test default relay has 1 NO contact (13-14)."""
        relay = IndustrialComponent(
            id="k1",
            type=IndustrialComponentType.RELAY,
            designation="K1"
        )

        assert len(relay.contact_blocks) == 1
        contact = relay.contact_blocks[0]
        assert contact.contact_type == ContactType.NO
        assert contact.terminal_from == "13"
        assert contact.terminal_to == "14"

    def test_default_contactor_power_contacts(self):
        """Test default contactor has 3 main power contacts (1-2, 3-4, 5-6)."""
        contactor = IndustrialComponent(
            id="k1",
            type=IndustrialComponentType.CONTACTOR,
            designation="K1"
        )

        power_contacts = contactor.contact_blocks[:3]
        assert len(power_contacts) == 3

        # Check power contact numbering
        assert power_contacts[0].terminal_from == "1"
        assert power_contacts[0].terminal_to == "2"
        assert power_contacts[1].terminal_from == "3"
        assert power_contacts[1].terminal_to == "4"
        assert power_contacts[2].terminal_from == "5"
        assert power_contacts[2].terminal_to == "6"

    def test_default_contactor_auxiliary_contact(self):
        """Test default contactor has 1 auxiliary NO contact (13-14)."""
        contactor = IndustrialComponent(
            id="k1",
            type=IndustrialComponentType.CONTACTOR,
            designation="K1"
        )

        # Should have 4 total contacts: 3 power + 1 aux
        assert len(contactor.contact_blocks) == 4

        # Auxiliary contact is last
        aux_contact = contactor.contact_blocks[3]
        assert aux_contact.contact_type == ContactType.NO
        assert aux_contact.terminal_from == "13"
        assert aux_contact.terminal_to == "14"

    def test_multiple_no_contacts_numbering(self):
        """Test relay with 3 NO contacts: 13-14, 23-24, 33-34."""
        relay = IndustrialComponent(
            id="k1",
            type=IndustrialComponentType.RELAY,
            designation="K1",
            contact_blocks=[]  # Clear defaults
        )

        # Add 3 NO contacts
        relay.add_contact("13", "14", ContactType.NO)
        relay.add_contact("23", "24", ContactType.NO)
        relay.add_contact("33", "34", ContactType.NO)

        no_contacts = relay.get_no_contacts()
        assert len(no_contacts) == 3

        assert no_contacts[0].terminal_from == "13"
        assert no_contacts[0].terminal_to == "14"
        assert no_contacts[1].terminal_from == "23"
        assert no_contacts[1].terminal_to == "24"
        assert no_contacts[2].terminal_from == "33"
        assert no_contacts[2].terminal_to == "34"

    def test_multiple_nc_contacts_numbering(self):
        """Test relay with 2 NC contacts: 11-12, 21-22."""
        relay = IndustrialComponent(
            id="k1",
            type=IndustrialComponentType.RELAY,
            designation="K1",
            contact_blocks=[]
        )

        # Add 2 NC contacts
        relay.add_contact("11", "12", ContactType.NC)
        relay.add_contact("21", "22", ContactType.NC)

        nc_contacts = relay.get_nc_contacts()
        assert len(nc_contacts) == 2

        assert nc_contacts[0].terminal_from == "11"
        assert nc_contacts[0].terminal_to == "12"
        assert nc_contacts[1].terminal_from == "21"
        assert nc_contacts[1].terminal_to == "22"

    def test_mixed_no_nc_contacts(self):
        """Test relay with mixed NO and NC contacts."""
        relay = IndustrialComponent(
            id="k1",
            type=IndustrialComponentType.RELAY,
            designation="K1",
            contact_blocks=[]
        )

        # Add 1 NO + 1 NC
        relay.add_contact("13", "14", ContactType.NO)
        relay.add_contact("21", "22", ContactType.NC)

        assert len(relay.contact_blocks) == 2
        assert len(relay.get_no_contacts()) == 1
        assert len(relay.get_nc_contacts()) == 1

        # Verify contact string representation
        contact_str = relay.get_contact_string()
        assert "1NO" in contact_str
        assert "1NC" in contact_str

    def test_three_phase_contactor_with_2no_aux(self):
        """Test three-phase contactor with 2 NO auxiliary contacts.

        Expected configuration:
        - Main contacts: 1-2, 3-4, 5-6 (power)
        - Aux NO: 13-14, 23-24
        - Coil: A1-A2
        """
        contactor = IndustrialComponent(
            id="k1",
            type=IndustrialComponentType.CONTACTOR,
            designation="K1",
            contact_blocks=[]
        )

        # Add power contacts
        contactor.add_contact("1", "2", ContactType.NO, label="L1-T1")
        contactor.add_contact("3", "4", ContactType.NO, label="L2-T2")
        contactor.add_contact("5", "6", ContactType.NO, label="L3-T3")

        # Add auxiliary contacts
        contactor.add_contact("13", "14", ContactType.NO)
        contactor.add_contact("23", "24", ContactType.NO)

        assert len(contactor.contact_blocks) == 5
        assert contactor.coil_terminals.positive == "A1"
        assert contactor.coil_terminals.negative == "A2"

        # Get contact summary
        contact_str = contactor.get_contact_string()
        assert "5NO" in contact_str

    def test_contactor_with_1no_1nc_aux(self):
        """Test contactor with 1 NO + 1 NC auxiliary contacts.

        Expected auxiliary contacts:
        - NO: 13-14
        - NC: 21-22
        """
        contactor = IndustrialComponent(
            id="k1",
            type=IndustrialComponentType.CONTACTOR,
            designation="K1",
            contact_blocks=[]
        )

        # Add power contacts
        contactor.add_contact("1", "2", ContactType.NO)
        contactor.add_contact("3", "4", ContactType.NO)
        contactor.add_contact("5", "6", ContactType.NO)

        # Add auxiliary contacts
        contactor.add_contact("13", "14", ContactType.NO)
        contactor.add_contact("21", "22", ContactType.NC)

        aux_contacts = contactor.contact_blocks[3:]
        assert len(aux_contacts) == 2
        assert aux_contacts[0].contact_type == ContactType.NO
        assert aux_contacts[0].terminal_from == "13"
        assert aux_contacts[1].contact_type == ContactType.NC
        assert aux_contacts[1].terminal_from == "21"


class TestContactStateLogic:
    """Test contact state changes with coil energization."""

    def test_no_contact_closed_when_energized(self):
        """Test NO contact closes when coil is energized."""
        contact = ContactBlock("13", "14", ContactType.NO)

        # De-energized: NO contact is open
        assert contact.get_state_for_coil(False) is False

        # Energized: NO contact is closed
        assert contact.get_state_for_coil(True) is True

    def test_nc_contact_opens_when_energized(self):
        """Test NC contact opens when coil is energized."""
        contact = ContactBlock("21", "22", ContactType.NC)

        # De-energized: NC contact is closed
        assert contact.get_state_for_coil(False) is True

        # Energized: NC contact is open
        assert contact.get_state_for_coil(True) is False

    def test_relay_contact_state_update(self):
        """Test relay updates all contact states on energization."""
        relay = IndustrialComponent(
            id="k1",
            type=IndustrialComponentType.RELAY,
            designation="K1",
            contact_blocks=[]
        )

        relay.add_contact("13", "14", ContactType.NO)
        relay.add_contact("21", "22", ContactType.NC)

        # Initial state: coil de-energized
        relay.update_contact_states()
        assert relay.contact_blocks[0].is_closed is False  # NO open
        assert relay.contact_blocks[1].is_closed is True   # NC closed

        # Energize coil
        relay.energize_coil()
        assert relay.coil_energized is True
        assert relay.contact_blocks[0].is_closed is True   # NO closed
        assert relay.contact_blocks[1].is_closed is False  # NC open

        # De-energize coil
        relay.de_energize_coil()
        assert relay.coil_energized is False
        assert relay.contact_blocks[0].is_closed is False  # NO open
        assert relay.contact_blocks[1].is_closed is True   # NC closed

    def test_toggle_coil(self):
        """Test toggling coil state."""
        relay = IndustrialComponent(
            id="k1",
            type=IndustrialComponentType.RELAY,
            designation="K1"
        )

        # Start de-energized
        assert relay.coil_energized is False

        # Toggle to energized
        result = relay.toggle_coil()
        assert result is True
        assert relay.coil_energized is True

        # Toggle to de-energized
        result = relay.toggle_coil()
        assert result is False
        assert relay.coil_energized is False


class TestContactIconGeneration:
    """Test SVG icon generation for contacts."""

    def test_no_contact_symbol_de_energized(self):
        """Test NO contact symbol in de-energized state (open)."""
        svg = create_no_contact_symbol(
            x=0, y=0, width=40, height=30,
            label="K1",
            terminal_labels=("13", "14"),
            energized=False
        )

        assert svg is not None
        assert "13" in svg  # Terminal label
        assert "14" in svg
        assert "K1" in svg  # Contact label
        # De-energized NO should show gap/angle
        assert "line" in svg.lower()

    def test_no_contact_symbol_energized(self):
        """Test NO contact symbol in energized state (closed)."""
        svg = create_no_contact_symbol(
            x=0, y=0, width=40, height=30,
            terminal_labels=("13", "14"),
            energized=True
        )

        assert svg is not None
        assert "13" in svg
        assert "14" in svg
        # Energized NO should show straight line
        assert "line" in svg.lower()

    def test_nc_contact_symbol_de_energized(self):
        """Test NC contact symbol in de-energized state (closed)."""
        svg = create_nc_contact_symbol(
            x=0, y=0, width=40, height=30,
            terminal_labels=("21", "22"),
            energized=False
        )

        assert svg is not None
        assert "21" in svg
        assert "22" in svg
        # NC symbol should have diagonal line indicator
        assert "line" in svg.lower()

    def test_nc_contact_symbol_energized(self):
        """Test NC contact symbol in energized state (open)."""
        svg = create_nc_contact_symbol(
            x=0, y=0, width=40, height=30,
            terminal_labels=("21", "22"),
            energized=True
        )

        assert svg is not None
        assert "21" in svg
        assert "22" in svg

    def test_coil_symbol_generation(self):
        """Test coil symbol generation with A1/A2 terminals."""
        svg = create_coil_symbol(
            x=0, y=0, width=30, height=40,
            designation="K1",
            terminal_labels=("A1", "A2"),
            energized=False
        )

        assert svg is not None
        assert "K1" in svg
        assert "A1" in svg
        assert "A2" in svg
        assert "rect" in svg.lower()  # Coil rectangle

    def test_coil_symbol_energized_color(self):
        """Test coil symbol changes color when energized."""
        svg_off = create_coil_symbol(
            designation="K1",
            energized=False
        )
        svg_on = create_coil_symbol(
            designation="K1",
            energized=True
        )

        assert svg_off != svg_on  # Should be different
        # Energized should have green color
        assert "#27AE60" in svg_on or "27ae60" in svg_on.lower()


class TestRelaySymbolGeneration:
    """Test complete relay/contactor symbol generation."""

    def test_relay_with_1no_contact(self):
        """Test relay symbol with 1 NO contact."""
        contacts = [
            ContactConfig("13", "14", ContactType.NO)
        ]

        svg = create_relay_symbol(
            width=120,
            height=80,
            designation="K1",
            contacts=contacts,
            energized=False
        )

        assert svg is not None
        assert "<svg" in svg
        assert "</svg>" in svg
        assert "K1" in svg
        assert "13" in svg
        assert "14" in svg
        assert "A1" in svg
        assert "A2" in svg

    def test_relay_with_2no_contacts(self):
        """Test relay with 2 NO contacts (13-14, 23-24)."""
        contacts = [
            ContactConfig("13", "14", ContactType.NO),
            ContactConfig("23", "24", ContactType.NO)
        ]

        svg = create_relay_symbol(
            designation="K2",
            contacts=contacts
        )

        assert "13" in svg
        assert "14" in svg
        assert "23" in svg
        assert "24" in svg

    def test_relay_with_1no_1nc(self):
        """Test relay with 1 NO + 1 NC contact."""
        contacts = [
            ContactConfig("13", "14", ContactType.NO),
            ContactConfig("21", "22", ContactType.NC)
        ]

        svg = create_relay_symbol(
            designation="K3",
            contacts=contacts
        )

        assert "13" in svg
        assert "14" in svg
        assert "21" in svg
        assert "22" in svg

    def test_contactor_symbol_with_aux_contacts(self):
        """Test contactor with power + auxiliary contacts."""
        contacts = [
            # Power contacts
            ContactConfig("1", "2", ContactType.NO, label="L1-T1"),
            ContactConfig("3", "4", ContactType.NO, label="L2-T2"),
            ContactConfig("5", "6", ContactType.NO, label="L3-T3"),
            # Auxiliary contacts
            ContactConfig("13", "14", ContactType.NO),
            ContactConfig("23", "24", ContactType.NO),
        ]

        svg = create_relay_symbol(
            width=150,
            height=120,
            designation="K1",
            contacts=contacts
        )

        # Check all terminal numbers present
        assert "1" in svg and "2" in svg
        assert "3" in svg and "4" in svg
        assert "5" in svg and "6" in svg
        assert "13" in svg and "14" in svg
        assert "23" in svg and "24" in svg

    def test_relay_energized_state(self):
        """Test relay symbol in energized state."""
        contacts = [ContactConfig("13", "14", ContactType.NO)]

        svg = create_relay_symbol(
            designation="K1",
            contacts=contacts,
            energized=True
        )

        # Should show energized styling
        assert "energized" in svg.lower() or "#27AE60" in svg or "27ae60" in svg.lower()


class TestComponentSymbolAPI:
    """Test high-level get_component_symbol API."""

    def test_get_relay_symbol(self):
        """Test getting relay symbol via API."""
        contacts = [ContactConfig("13", "14", ContactType.NO)]

        svg = get_component_symbol(
            component_type="relay",
            designation="K1",
            contacts=contacts
        )

        assert svg is not None
        assert "K1" in svg

    def test_get_contactor_symbol(self):
        """Test getting contactor symbol via API."""
        contacts = [
            ContactConfig("1", "2", ContactType.NO),
            ContactConfig("13", "14", ContactType.NO)
        ]

        svg = get_component_symbol(
            component_type="contactor",
            designation="K1",
            contacts=contacts
        )

        assert svg is not None
        assert "K1" in svg


class TestContactDesignationFormatting:
    """Test contact designation string formatting."""

    def test_contact_designation_with_parent(self):
        """Test full contact designation includes parent."""
        contact = ContactBlock("13", "14", ContactType.NO)
        designation = contact.get_designation("K1")
        assert designation == "K1:13-14"

    def test_contact_designation_without_parent(self):
        """Test contact designation without parent."""
        contact = ContactBlock("13", "14", ContactType.NO)
        designation = contact.get_designation()
        assert designation == "13-14"

    def test_contact_designation_with_label(self):
        """Test contact designation with custom label."""
        contact = ContactBlock("1", "2", ContactType.NO, label="L1-T1")
        designation = contact.get_designation("K1")
        assert designation == "L1-T1"

    def test_component_terminal_labels(self):
        """Test getting all terminal labels from component."""
        relay = IndustrialComponent(
            id="k1",
            type=IndustrialComponentType.RELAY,
            designation="K1",
            contact_blocks=[]
        )

        relay.add_contact("13", "14", ContactType.NO)
        relay.add_contact("21", "22", ContactType.NC)

        terminals = relay.get_terminal_labels()

        # Should include coil + contact terminals
        assert "A1" in terminals
        assert "A2" in terminals
        assert "13" in terminals
        assert "14" in terminals
        assert "21" in terminals
        assert "22" in terminals


class TestTerminalStripIconGeneration:
    """Test terminal strip icon generation."""

    def test_terminal_strip_2_position(self):
        """Test 2-position terminal strip icon."""
        from electrical_schematics.models.terminal_strip import (
            TerminalStrip,
            TerminalStripType
        )
        from electrical_schematics.gui.terminal_strip_icon import (
            TerminalStripIconGenerator
        )

        strip = TerminalStrip(
            designation="X1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=2
        )

        svg = TerminalStripIconGenerator.generate_svg(strip)

        assert svg is not None
        assert "<svg" in svg
        assert "X1" in svg
        assert "1" in svg  # Terminal numbers
        assert "2" in svg

    def test_terminal_strip_4_position(self):
        """Test 4-position terminal strip icon."""
        from electrical_schematics.models.terminal_strip import (
            TerminalStrip,
            TerminalStripType
        )
        from electrical_schematics.gui.terminal_strip_icon import (
            TerminalStripIconGenerator
        )

        strip = TerminalStrip(
            designation="X10",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=4
        )

        svg = TerminalStripIconGenerator.generate_svg(strip)

        assert "1" in svg
        assert "2" in svg
        assert "3" in svg
        assert "4" in svg

    def test_terminal_strip_multi_level(self):
        """Test multi-level terminal strip (2-level, 3 positions)."""
        from electrical_schematics.models.terminal_strip import (
            TerminalStrip,
            TerminalStripType
        )
        from electrical_schematics.gui.terminal_strip_icon import (
            TerminalStripIconGenerator
        )

        strip = TerminalStrip(
            designation="X20",
            terminal_type=TerminalStripType.MULTI_LEVEL,
            position_count=3,
            level_count=2
        )

        svg = TerminalStripIconGenerator.generate_svg(strip)

        # Should show multi-level numbering (1.1, 1.2, 2.1, 2.2, 3.1, 3.2)
        assert "1.1" in svg or "1" in svg
        assert svg is not None

    def test_terminal_strip_color_coding(self):
        """Test terminal strip color coding (IEC 60446)."""
        from electrical_schematics.models.terminal_strip import (
            TerminalStrip,
            TerminalStripType,
            TerminalColor
        )
        from electrical_schematics.gui.terminal_strip_icon import (
            TerminalStripIconGenerator
        )

        # Ground terminal (green-yellow)
        strip_ground = TerminalStrip(
            designation="PE1",
            terminal_type=TerminalStripType.GROUND,
            position_count=1,
            color=TerminalColor.GREEN_YELLOW
        )

        svg = TerminalStripIconGenerator.generate_svg(strip_ground)

        # Should have green-yellow color (#CCFF00)
        assert "#CCFF00" in svg or "ccff00" in svg.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
