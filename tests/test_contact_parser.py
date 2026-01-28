"""Tests for contact configuration parser."""

import pytest
from electrical_schematics.services.contact_parser import (
    ContactConfigParser,
    ContactConfiguration
)


@pytest.fixture
def parser():
    """Create contact parser."""
    return ContactConfigParser()


def test_parse_relay_with_no_contacts(parser):
    """Test parsing relay with NO contacts."""
    config = parser.parse_description("Relay 2 NO contacts 24VDC", "Relays")

    assert config.component_type == "relay"
    assert config.no_contacts == 2
    assert config.nc_contacts == 0
    assert config.poles == 0


def test_parse_relay_with_nc_contacts(parser):
    """Test parsing relay with NC contacts."""
    config = parser.parse_description("Relay 1 NC contact 12VDC", "Relays")

    assert config.component_type == "relay"
    assert config.no_contacts == 0
    assert config.nc_contacts == 1


def test_parse_relay_with_mixed_contacts(parser):
    """Test parsing relay with both NO and NC contacts."""
    config = parser.parse_description("Relay 2 NO and 2 NC contacts", "Relays")

    assert config.component_type == "relay"
    assert config.no_contacts == 2
    assert config.nc_contacts == 2


def test_parse_contactor_three_phase(parser):
    """Test parsing 3-phase contactor."""
    config = parser.parse_description(
        "Contactor AC-3 11KW/400V 3-phase with 1 NO auxiliary",
        "Contactors"
    )

    assert config.component_type == "contactor"
    assert config.three_phase is True
    assert config.power_contacts == 3
    assert config.no_contacts == 1
    assert config.auxiliary_contacts is True


def test_parse_dpdt_relay(parser):
    """Test parsing DPDT relay."""
    config = parser.parse_description("Relay DPDT 5A 24VDC", "Relays")

    assert config.component_type == "relay"
    assert config.poles == 2
    assert config.no_contacts == 2
    assert config.nc_contacts == 2


def test_parse_spdt_relay(parser):
    """Test parsing SPDT relay."""
    config = parser.parse_description("Relay SPDT 10A 12VDC", "Relays")

    assert config.component_type == "relay"
    assert config.poles == 1
    assert config.no_contacts == 1
    assert config.nc_contacts == 1


def test_parse_terminal_block(parser):
    """Test parsing terminal block."""
    config = parser.parse_description(
        "Terminal Block 10 position screw",
        "Terminal Blocks"
    )

    assert config.component_type == "terminal_block"
    assert config.positions == 10


def test_parse_terminal_block_way(parser):
    """Test parsing terminal block with 'way' terminology."""
    config = parser.parse_description(
        "Terminal Block 12-way DIN rail",
        "Terminal Blocks"
    )

    assert config.component_type == "terminal_block"
    assert config.positions == 12


def test_parse_switch(parser):
    """Test parsing switch."""
    config = parser.parse_description("Selector switch 3 position", "Switches")

    assert config.component_type == "switch"
    assert config.positions == 3


def test_parse_circuit_breaker(parser):
    """Test parsing circuit breaker."""
    config = parser.parse_description("Circuit breaker 3 pole 16A", "Circuit Breakers")

    assert config.component_type == "circuit_breaker"
    assert config.poles == 3


def test_parse_motor_starter(parser):
    """Test parsing motor starter."""
    config = parser.parse_description(
        "Motor starter 3-phase 11KW DOL",
        "Motor Starters"
    )

    assert config.component_type == "contactor"  # Motor starter classified as contactor
    assert config.three_phase is True


def test_parse_poles_only(parser):
    """Test parsing description with poles but no explicit NO/NC."""
    config = parser.parse_description("Relay 4 pole 5A", "Relays")

    assert config.component_type == "relay"
    assert config.poles == 4
    # Should default to NO contacts equal to poles
    assert config.no_contacts == 4


def test_parse_empty_description(parser):
    """Test parsing empty description."""
    config = parser.parse_description("", "")

    assert config.component_type == "unknown"
    assert config.no_contacts == 0
    assert config.nc_contacts == 0


def test_parse_no_pattern_match(parser):
    """Test description with no recognizable patterns."""
    config = parser.parse_description("Unknown component XYZ123", "")

    assert config.component_type == "unknown"


def test_parse_3pdt_relay(parser):
    """Test parsing 3PDT relay."""
    config = parser.parse_description("Relay 3PDT 10A", "Relays")

    assert config.component_type == "relay"
    assert config.poles == 3
    assert config.no_contacts == 3
    assert config.nc_contacts == 3


def test_parse_4pdt_relay(parser):
    """Test parsing 4PDT relay."""
    config = parser.parse_description("Relay 4PDT 5A", "Relays")

    assert config.component_type == "relay"
    assert config.poles == 4
    assert config.no_contacts == 4
    assert config.nc_contacts == 4


def test_parse_category_hint(parser):
    """Test that category hint helps classification."""
    # Without category, might be ambiguous
    config1 = parser.parse_description("DPDT 24VDC", "")

    # With category, clear classification
    config2 = parser.parse_description("DPDT 24VDC", "Relays")

    assert config2.component_type == "relay"


def test_validate_config_defaults(parser):
    """Test that validation sets reasonable defaults."""
    # Create config with just component type
    config = ContactConfiguration(component_type="relay")

    # Parse with empty description to trigger validation
    parser._validate_config(config)

    # Should have default values
    assert config.no_contacts == 1
    assert config.poles == 1


def test_validate_contactor_defaults(parser):
    """Test that contactor gets reasonable defaults."""
    config = ContactConfiguration(component_type="contactor")

    parser._validate_config(config)

    assert config.power_contacts == 3  # 3-phase default
    assert config.no_contacts == 1  # 1 auxiliary


def test_contact_configuration_to_dict():
    """Test ContactConfiguration serialization."""
    config = ContactConfiguration(
        no_contacts=2,
        nc_contacts=1,
        poles=2,
        component_type="relay",
        description="Test relay"
    )

    data = config.to_dict()

    assert data['no_contacts'] == 2
    assert data['nc_contacts'] == 1
    assert data['poles'] == 2
    assert data['component_type'] == "relay"
    assert data['description'] == "Test relay"


def test_contact_configuration_from_dict():
    """Test ContactConfiguration deserialization."""
    data = {
        'no_contacts': 2,
        'nc_contacts': 1,
        'poles': 2,
        'component_type': 'relay',
        'description': 'Test relay'
    }

    config = ContactConfiguration.from_dict(data)

    assert config.no_contacts == 2
    assert config.nc_contacts == 1
    assert config.poles == 2
    assert config.component_type == "relay"
    assert config.description == "Test relay"


def test_parse_variations_no_contacts(parser):
    """Test various NO contact description formats."""
    descriptions = [
        "2 NO",
        "2NO",
        "2-NO",
        "2 N.O.",
        "2 normally open",
        "2 Normally Open contacts"
    ]

    for desc in descriptions:
        config = parser.parse_description(desc, "Relays")
        assert config.no_contacts == 2, f"Failed to parse: {desc}"


def test_parse_variations_nc_contacts(parser):
    """Test various NC contact description formats."""
    descriptions = [
        "2 NC",
        "2NC",
        "2-NC",
        "2 N.C.",
        "2 normally closed",
        "2 Normally Closed contacts"
    ]

    for desc in descriptions:
        config = parser.parse_description(desc, "Relays")
        assert config.nc_contacts == 2, f"Failed to parse: {desc}"
