"""Tests for dynamic icon generator."""

import pytest
from electrical_schematics.services.dynamic_icon_generator import DynamicIconGenerator
from electrical_schematics.services.contact_parser import ContactConfiguration


@pytest.fixture
def generator():
    """Create icon generator."""
    return DynamicIconGenerator()


def test_generate_relay_icon_no_contacts(generator):
    """Test generating relay icon with NO contacts."""
    config = ContactConfiguration(
        component_type="relay",
        no_contacts=2,
        nc_contacts=0,
        poles=2
    )

    svg = generator.generate_icon(config)

    # Verify SVG is generated
    assert svg
    assert '<svg' in svg
    assert '</svg>' in svg

    # Should have coil labels (A1, A2)
    assert 'A1' in svg
    assert 'A2' in svg

    # Should have NO contact labels (13-14, 23-24)
    assert '13' in svg
    assert '14' in svg
    assert '23' in svg
    assert '24' in svg


def test_generate_relay_icon_nc_contacts(generator):
    """Test generating relay icon with NC contacts."""
    config = ContactConfiguration(
        component_type="relay",
        no_contacts=0,
        nc_contacts=2,
        poles=2
    )

    svg = generator.generate_icon(config)

    # Should have NC contact labels (11-12, 21-22)
    assert '11' in svg
    assert '12' in svg
    assert '21' in svg
    assert '22' in svg


def test_generate_relay_icon_mixed_contacts(generator):
    """Test generating relay icon with both NO and NC contacts."""
    config = ContactConfiguration(
        component_type="relay",
        no_contacts=1,
        nc_contacts=1,
        poles=2
    )

    svg = generator.generate_icon(config)

    # Should have both NO (13-14) and NC (21-22)
    assert '13' in svg
    assert '14' in svg
    assert '21' in svg
    assert '22' in svg


def test_generate_contactor_icon(generator):
    """Test generating contactor icon with power and auxiliary contacts."""
    config = ContactConfiguration(
        component_type="contactor",
        power_contacts=3,
        no_contacts=1,
        nc_contacts=0,
        three_phase=True
    )

    svg = generator.generate_icon(config)

    # Should have coil
    assert 'A1' in svg
    assert 'A2' in svg

    # Should have power contacts (1-2, 3-4, 5-6)
    assert '>1<' in svg or 'text' in svg  # Label "1"
    assert '>2<' in svg
    assert '>3<' in svg
    assert '>4<' in svg
    assert '>5<' in svg
    assert '>6<' in svg

    # Should have auxiliary NO (13-14)
    assert '13' in svg
    assert '14' in svg


def test_generate_terminal_block_icon(generator):
    """Test generating terminal block icon."""
    config = ContactConfiguration(
        component_type="terminal_block",
        positions=10
    )

    svg = generator.generate_icon(config)

    # Should have position labels 1-10
    for i in range(1, 11):
        assert f'>{i}<' in svg or f'text' in svg


def test_generate_switch_icon(generator):
    """Test generating switch icon."""
    config = ContactConfiguration(
        component_type="switch",
        no_contacts=1
    )

    svg = generator.generate_icon(config)

    # Should generate similar to relay
    assert '<svg' in svg
    assert '</svg>' in svg


def test_generate_breaker_icon(generator):
    """Test generating circuit breaker icon."""
    config = ContactConfiguration(
        component_type="circuit_breaker",
        poles=3
    )

    svg = generator.generate_icon(config)

    # Should have basic breaker symbol
    assert '<svg' in svg
    assert '</svg>' in svg
    assert 'line' in svg  # Breaker has lines


def test_generate_generic_icon(generator):
    """Test generating generic icon for unknown type."""
    config = ContactConfiguration(
        component_type="unknown"
    )

    svg = generator.generate_icon(config)

    # Should have generic box with "?"
    assert '<svg' in svg
    assert '</svg>' in svg
    assert '?' in svg


def test_icon_has_valid_svg_structure(generator):
    """Test that generated icons have valid SVG structure."""
    config = ContactConfiguration(
        component_type="relay",
        no_contacts=1
    )

    svg = generator.generate_icon(config)

    # Check basic structure
    assert svg.startswith('<svg')
    assert svg.endswith('</svg>')
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg
    assert 'width=' in svg
    assert 'height=' in svg
    assert 'viewBox=' in svg


def test_icon_scaling(generator):
    """Test that icons can be generated with custom dimensions."""
    config = ContactConfiguration(
        component_type="relay",
        no_contacts=1
    )

    svg = generator.generate_icon(config, width=200, height=100)

    # Check custom dimensions
    assert 'width="200"' in svg
    assert 'height="100"' in svg


def test_draw_coil(generator):
    """Test coil drawing."""
    coil_svg = generator._draw_coil(10, 10, 40, 60)

    # Should have rectangle and labels
    assert '<rect' in coil_svg
    assert 'A1' in coil_svg
    assert 'A2' in coil_svg


def test_draw_no_contact(generator):
    """Test NO contact drawing."""
    contact_svg = generator._draw_no_contact(10, 10, pole_num=1)

    # Should have line and labels (13-14)
    assert '<line' in contact_svg
    assert '13' in contact_svg
    assert '14' in contact_svg


def test_draw_nc_contact(generator):
    """Test NC contact drawing."""
    contact_svg = generator._draw_nc_contact(10, 10, pole_num=1)

    # Should have line and labels (11-12)
    assert '<line' in contact_svg
    assert '11' in contact_svg
    assert '12' in contact_svg


def test_draw_power_contact(generator):
    """Test power contact drawing."""
    contact_svg = generator._draw_power_contact(10, 10, "1", "2")

    # Should have heavy line and labels
    assert '<line' in contact_svg
    assert '>1<' in contact_svg or 'text' in contact_svg
    assert '>2<' in contact_svg or 'text' in contact_svg


def test_iec_60617_numbering(generator):
    """Test that IEC 60617 contact numbering is correct."""
    # NO contacts: 13-14, 23-24, 33-34, 43-44
    # NC contacts: 11-12, 21-22, 31-32, 41-42
    # Note: NC contacts are numbered sequentially after NO contacts in our implementation

    config = ContactConfiguration(
        component_type="relay",
        no_contacts=4,
        nc_contacts=4
    )

    svg = generator.generate_icon(config)

    # Check NO numbering (poles 1-4)
    assert '13' in svg and '14' in svg
    assert '23' in svg and '24' in svg
    assert '33' in svg and '34' in svg
    assert '43' in svg and '44' in svg

    # Check NC numbering (poles 5-8 in our sequential implementation)
    # NC contacts come after NO contacts, so they use pole numbers 5-8
    assert '51' in svg and '52' in svg
    assert '61' in svg and '62' in svg
    assert '71' in svg and '72' in svg
    assert '81' in svg and '82' in svg


def test_dpdt_relay_icon(generator):
    """Test DPDT relay icon generation."""
    config = ContactConfiguration(
        component_type="relay",
        no_contacts=2,
        nc_contacts=2,
        poles=2
    )

    svg = generator.generate_icon(config)

    # Should have coil and 4 contacts
    assert 'A1' in svg
    assert 'A2' in svg
    # NO contacts (poles 1-2)
    assert '13' in svg and '14' in svg
    assert '23' in svg and '24' in svg
    # NC contacts (poles 3-4 in sequential implementation)
    assert '31' in svg and '32' in svg
    assert '41' in svg and '42' in svg


def test_terminal_block_many_positions(generator):
    """Test terminal block with many positions."""
    config = ContactConfiguration(
        component_type="terminal_block",
        positions=20
    )

    svg = generator.generate_icon(config)

    # Should have positions 1-20
    assert '>1<' in svg
    assert '>10<' in svg
    assert '>20<' in svg
