"""Unit tests for terminal strip functionality."""

import pytest
from datetime import datetime

from electrical_schematics.models.terminal_strip import (
    TerminalStrip,
    TerminalStripType,
    TerminalColor,
    TerminalPosition
)
from electrical_schematics.gui.terminal_strip_icon import TerminalStripIconGenerator


class TestTerminalPosition:
    """Test TerminalPosition data model."""

    def test_create_single_level_position(self):
        """Test creating a single-level terminal position."""
        pos = TerminalPosition(position=1, level=1)
        assert pos.position == 1
        assert pos.level == 1
        assert pos.terminal_number == "1"

    def test_create_multi_level_position(self):
        """Test creating a multi-level terminal position."""
        pos = TerminalPosition(position=2, level=3)
        assert pos.position == 2
        assert pos.level == 3
        assert pos.terminal_number == "2.3"

    def test_custom_terminal_number(self):
        """Test custom terminal numbering."""
        pos = TerminalPosition(position=1, level=1, terminal_number="N")
        assert pos.terminal_number == "N"

    def test_get_full_designation(self):
        """Test getting full terminal designation."""
        pos = TerminalPosition(position=1, level=1)
        assert pos.get_full_designation("X1") == "X1:1"
        assert pos.get_full_designation() == "1"

    def test_terminal_with_led(self):
        """Test terminal with LED indicator."""
        pos = TerminalPosition(
            position=1,
            level=1,
            has_led=True,
            led_color="red"
        )
        assert pos.has_led is True
        assert pos.led_color == "red"


class TestTerminalStrip:
    """Test TerminalStrip data model."""

    def test_create_basic_feed_through(self):
        """Test creating a basic feed-through terminal."""
        strip = TerminalStrip(
            designation="X1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=4,
            manufacturer="Phoenix Contact",
            part_number="PTFIX 6/6X2.5 GY"
        )

        assert strip.designation == "X1"
        assert strip.terminal_type == TerminalStripType.FEED_THROUGH
        assert strip.position_count == 4
        assert strip.level_count == 1
        assert len(strip.terminals) == 4

    def test_auto_generate_terminals(self):
        """Test automatic terminal position generation."""
        strip = TerminalStrip(
            designation="X1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=6
        )

        assert len(strip.terminals) == 6
        for i, terminal in enumerate(strip.terminals, 1):
            assert terminal.position == i
            assert terminal.level == 1
            assert terminal.terminal_number == str(i)

    def test_multi_level_terminal_generation(self):
        """Test multi-level terminal generation."""
        strip = TerminalStrip(
            designation="X20",
            terminal_type=TerminalStripType.MULTI_LEVEL,
            position_count=2,
            level_count=3
        )

        assert len(strip.terminals) == 6  # 2 positions * 3 levels
        assert strip.get_terminal_count() == 6

        # Check first position, all levels
        term_1_1 = strip.get_terminal(1, 1)
        assert term_1_1 is not None
        assert term_1_1.terminal_number == "1.1"

        term_1_2 = strip.get_terminal(1, 2)
        assert term_1_2.terminal_number == "1.2"

        term_1_3 = strip.get_terminal(1, 3)
        assert term_1_3.terminal_number == "1.3"

    def test_ground_terminal_creation(self):
        """Test ground/PE terminal creation."""
        strip = TerminalStrip(
            designation="PE1",
            terminal_type=TerminalStripType.GROUND,
            position_count=1,
            color=TerminalColor.GREEN_YELLOW,
            manufacturer="Phoenix Contact",
            part_number="PT 2.5-PE"
        )

        assert strip.terminal_type == TerminalStripType.GROUND
        assert strip.color == TerminalColor.GREEN_YELLOW
        assert len(strip.terminals) == 1

    def test_fuse_terminal_creation(self):
        """Test fuse terminal block creation."""
        strip = TerminalStrip(
            designation="F1",
            terminal_type=TerminalStripType.FUSE,
            position_count=1,
            manufacturer="Phoenix Contact",
            part_number="ST 4-HESILED 24"
        )

        assert strip.terminal_type == TerminalStripType.FUSE
        assert strip.has_fuse is True
        assert strip.fuse_type == "5x20mm"  # Auto-set default

    def test_disconnect_terminal_creation(self):
        """Test disconnect terminal creation."""
        strip = TerminalStrip(
            designation="X10",
            terminal_type=TerminalStripType.DISCONNECT,
            position_count=1,
            has_disconnect=True
        )

        assert strip.has_disconnect is True
        assert strip.terminals[0].has_test_point is True

    def test_led_indicator_terminal(self):
        """Test LED indicator terminal creation."""
        strip = TerminalStrip(
            designation="X40",
            terminal_type=TerminalStripType.LED_INDICATOR,
            position_count=1,
            led_voltage="24VDC"
        )

        assert strip.has_led is True
        assert strip.led_voltage == "24VDC"

    def test_get_terminal_by_position(self):
        """Test getting terminal by position and level."""
        strip = TerminalStrip(
            designation="X1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=4
        )

        terminal = strip.get_terminal(2)
        assert terminal is not None
        assert terminal.position == 2
        assert terminal.terminal_number == "2"

    def test_get_terminal_by_number(self):
        """Test getting terminal by number string."""
        strip = TerminalStrip(
            designation="X20",
            terminal_type=TerminalStripType.MULTI_LEVEL,
            position_count=2,
            level_count=2
        )

        terminal = strip.get_terminal_by_number("2.2")
        assert terminal is not None
        assert terminal.position == 2
        assert terminal.level == 2

    def test_get_display_name(self):
        """Test display name generation."""
        strip = TerminalStrip(
            designation="X1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=6,
            manufacturer="Phoenix Contact",
            part_number="PTFIX 6/6X2.5 GY"
        )

        display_name = strip.get_display_name()
        assert "Phoenix Contact" in display_name
        assert "PTFIX 6/6X2.5 GY" in display_name
        assert "6-pos" in display_name

    def test_get_specification_summary(self):
        """Test specification summary generation."""
        strip = TerminalStrip(
            designation="X1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=4,
            current_rating="24A",
            voltage_rating="500V",
            wire_size_min_mm2=0.5,
            wire_size_max_mm2=2.5
        )

        summary = strip.get_specification_summary()
        assert "24A" in summary
        assert "500V" in summary
        assert "0.5-2.5mm²" in summary

    def test_digikey_integration_fields(self):
        """Test DigiKey integration fields."""
        strip = TerminalStrip(
            designation="X1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=2,
            digikey_part_number="277-1284-ND",
            digikey_url="https://www.digikey.com/...",
            unit_price=1.50,
            stock_quantity=1000
        )

        assert strip.digikey_part_number == "277-1284-ND"
        assert strip.unit_price == 1.50
        assert strip.stock_quantity == 1000

    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        strip = TerminalStrip(
            designation="X1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=2,
            manufacturer="Phoenix Contact",
            part_number="TEST-123"
        )

        data = strip.to_dict()

        assert data["designation"] == "X1"
        assert data["terminal_type"] == "feed_through"
        assert data["position_count"] == 2
        assert data["manufacturer"] == "Phoenix Contact"
        assert data["part_number"] == "TEST-123"
        assert len(data["terminals"]) == 2

    def test_from_dict_deserialization(self):
        """Test deserialization from dictionary."""
        data = {
            "designation": "X1",
            "terminal_type": "feed_through",
            "position_count": 4,
            "level_count": 1,
            "manufacturer": "Phoenix Contact",
            "part_number": "TEST-456",
            "voltage_rating": "500V",
            "current_rating": "24A",
            "color": "gray",
            "terminals": []
        }

        strip = TerminalStrip.from_dict(data)

        assert strip.designation == "X1"
        assert strip.terminal_type == TerminalStripType.FEED_THROUGH
        assert strip.position_count == 4
        assert strip.manufacturer == "Phoenix Contact"

    def test_round_trip_serialization(self):
        """Test round-trip serialization/deserialization."""
        original = TerminalStrip(
            designation="X10",
            terminal_type=TerminalStripType.MULTI_LEVEL,
            position_count=2,
            level_count=3,
            manufacturer="Wago",
            part_number="2002-2204",
            has_disconnect=True
        )

        data = original.to_dict()
        restored = TerminalStrip.from_dict(data)

        assert restored.designation == original.designation
        assert restored.terminal_type == original.terminal_type
        assert restored.position_count == original.position_count
        assert restored.level_count == original.level_count
        assert len(restored.terminals) == len(original.terminals)

    def test_string_representation(self):
        """Test string representation."""
        strip = TerminalStrip(
            designation="X1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=4,
            manufacturer="Phoenix Contact",
            part_number="PTFIX-TEST"
        )

        str_repr = str(strip)
        assert "X1" in str_repr
        assert "24A" in str_repr  # Default current rating


class TestTerminalStripIconGenerator:
    """Test SVG icon generation for terminal strips."""

    def test_generate_basic_svg(self):
        """Test generating basic SVG icon."""
        strip = TerminalStrip(
            designation="X1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=4
        )

        svg = TerminalStripIconGenerator.generate_svg(strip)

        assert svg.startswith('<svg')
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg
        assert '</svg>' in svg
        assert 'X1' in svg  # Designation should be in SVG

    def test_svg_expands_with_position_count(self):
        """Test that SVG width expands with more positions."""
        strip_2pos = TerminalStrip(
            designation="X1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=2
        )

        strip_10pos = TerminalStrip(
            designation="X2",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=10
        )

        svg_2 = TerminalStripIconGenerator.generate_svg(strip_2pos)
        svg_10 = TerminalStripIconGenerator.generate_svg(strip_10pos)

        # Extract viewBox width (approximate check)
        assert 'viewBox="0 0 40' in svg_2  # 2 * 20 = 40
        assert 'viewBox="0 0 200' in svg_10  # 10 * 20 = 200

    def test_svg_includes_din_rail(self):
        """Test that SVG includes DIN rail representation."""
        strip = TerminalStrip(
            designation="X1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=2
        )

        svg = TerminalStripIconGenerator.generate_svg(strip)
        assert 'id="din-rail"' in svg

    def test_svg_includes_terminal_positions(self):
        """Test that SVG includes terminal positions."""
        strip = TerminalStrip(
            designation="X1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=4
        )

        svg = TerminalStripIconGenerator.generate_svg(strip)

        # Should have position markers for each terminal
        assert 'id="position-1"' in svg
        assert 'id="position-2"' in svg
        assert 'id="position-3"' in svg
        assert 'id="position-4"' in svg

    def test_svg_color_coding(self):
        """Test color coding in SVG."""
        # Gray terminal
        strip_gray = TerminalStrip(
            designation="X1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=2,
            color=TerminalColor.GRAY
        )
        svg_gray = TerminalStripIconGenerator.generate_svg(strip_gray)
        assert "#808080" in svg_gray

        # PE (green-yellow) terminal
        strip_pe = TerminalStrip(
            designation="PE1",
            terminal_type=TerminalStripType.GROUND,
            position_count=1,
            color=TerminalColor.GREEN_YELLOW
        )
        svg_pe = TerminalStripIconGenerator.generate_svg(strip_pe)
        assert "#CCFF00" in svg_pe

        # Blue neutral terminal
        strip_blue = TerminalStrip(
            designation="N1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=1,
            color=TerminalColor.BLUE
        )
        svg_blue = TerminalStripIconGenerator.generate_svg(strip_blue)
        assert "#0066CC" in svg_blue

    def test_svg_led_indicators(self):
        """Test LED indicators in SVG."""
        strip = TerminalStrip(
            designation="X40",
            terminal_type=TerminalStripType.LED_INDICATOR,
            position_count=2,
            has_led=True
        )

        svg = TerminalStripIconGenerator.generate_svg(strip)
        assert 'id="led-indicators"' in svg

    def test_svg_fuse_indicators(self):
        """Test fuse indicators in SVG."""
        strip = TerminalStrip(
            designation="F1",
            terminal_type=TerminalStripType.FUSE,
            position_count=1,
            has_fuse=True
        )

        svg = TerminalStripIconGenerator.generate_svg(strip)
        assert 'id="fuse-indicators"' in svg

    def test_svg_disconnect_indicators(self):
        """Test disconnect knife indicators in SVG."""
        strip = TerminalStrip(
            designation="X10",
            terminal_type=TerminalStripType.DISCONNECT,
            position_count=2,
            has_disconnect=True
        )

        svg = TerminalStripIconGenerator.generate_svg(strip)
        # Disconnect shown as dashed line
        assert 'stroke-dasharray' in svg

    def test_multi_level_terminal_svg(self):
        """Test multi-level terminal rendering."""
        strip = TerminalStrip(
            designation="X20",
            terminal_type=TerminalStripType.MULTI_LEVEL,
            position_count=2,
            level_count=3
        )

        svg = TerminalStripIconGenerator.generate_svg(strip)
        assert 'id="terminal-body"' in svg
        # Multi-level should have opacity variations
        assert 'opacity=' in svg

    def test_generate_for_library(self):
        """Test library preview generation."""
        strip = TerminalStrip(
            designation="X1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=4
        )

        svg = TerminalStripIconGenerator.generate_for_library(strip)
        assert '<svg' in svg
        assert '</svg>' in svg

    def test_generate_for_schematic(self):
        """Test schematic placement generation."""
        strip = TerminalStrip(
            designation="X1",
            terminal_type=TerminalStripType.FEED_THROUGH,
            position_count=4
        )

        svg = TerminalStripIconGenerator.generate_for_schematic(strip, scale=1.5)
        assert '<svg' in svg
        assert '</svg>' in svg


class TestTerminalStripLibrary:
    """Test terminal strip library integration."""

    def test_load_library_from_json(self):
        """Test loading terminal strip library from JSON."""
        import json
        from pathlib import Path

        config_path = Path(__file__).parent.parent / "electrical_schematics" / "config"
        library_file = config_path / "terminal_strips_library.json"

        if library_file.exists():
            with open(library_file, 'r') as f:
                data = json.load(f)

            assert "terminal_strips" in data
            assert len(data["terminal_strips"]) >= 15  # Should have at least 15 parts

            # Verify first entry has required fields
            first_strip = data["terminal_strips"][0]
            assert "designation" in first_strip
            assert "terminal_type" in first_strip
            assert "position_count" in first_strip
            assert "manufacturer" in first_strip
            assert "part_number" in first_strip
            assert "digikey_part_number" in first_strip

    def test_library_digikey_integration(self):
        """Test that library includes DigiKey part numbers."""
        import json
        from pathlib import Path

        config_path = Path(__file__).parent.parent / "electrical_schematics" / "config"
        library_file = config_path / "terminal_strips_library.json"

        if library_file.exists():
            with open(library_file, 'r') as f:
                data = json.load(f)

            # Verify all parts have DigiKey numbers
            for strip_data in data["terminal_strips"]:
                assert strip_data.get("digikey_part_number") is not None
                assert strip_data.get("digikey_url") is not None
                assert strip_data.get("unit_price") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
