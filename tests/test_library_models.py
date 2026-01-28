"""Tests for the new library data models (LibraryPart and ProjectComponent)."""

import pytest
from datetime import datetime

from electrical_schematics.models import LibraryPart, ProjectComponent


class TestLibraryPart:
    """Tests for the LibraryPart model."""

    def test_create_minimal_part(self) -> None:
        """Test creating a part with only required fields."""
        part = LibraryPart(manufacturer_part_number="3RT2026-1DB40-1AAO")

        assert part.manufacturer_part_number == "3RT2026-1DB40-1AAO"
        assert part.manufacturer == ""
        assert part.description == ""
        assert part.digikey_lookup_attempted is False
        assert part.digikey_lookup_success is False

    def test_create_full_part(self) -> None:
        """Test creating a part with all fields."""
        part = LibraryPart(
            manufacturer_part_number="3RT2026-1DB40-1AAO",
            manufacturer="Siemens",
            description="Contactor AC-3 11KW/400V",
            category="Contactors",
            subcategory="AC Contactors",
            technical_data="11kW, 400VAC, 25A",
            voltage_rating="400VAC",
            current_rating="25A",
            power_rating="11kW",
            component_type="contactor",
        )

        assert part.manufacturer_part_number == "3RT2026-1DB40-1AAO"
        assert part.manufacturer == "Siemens"
        assert part.description == "Contactor AC-3 11KW/400V"
        assert part.category == "Contactors"
        assert part.voltage_rating == "400VAC"
        assert part.current_rating == "25A"

    def test_part_number_normalization(self) -> None:
        """Test that part numbers are normalized (uppercase, trimmed)."""
        part = LibraryPart(manufacturer_part_number="  3rt2026-1db40  ")

        assert part.manufacturer_part_number == "3RT2026-1DB40"

    def test_part_number_required(self) -> None:
        """Test that empty part number raises ValueError."""
        with pytest.raises(ValueError, match="manufacturer_part_number is required"):
            LibraryPart(manufacturer_part_number="")

    def test_update_from_digikey(self) -> None:
        """Test updating part with DigiKey data."""
        part = LibraryPart(manufacturer_part_number="3RT2026-1DB40-1AAO")

        digikey_data = {
            "digi_key_part_number": "277-14958-ND",
            "product_description": "CONTACTOR AC-3 11KW 400V",
            "product_url": "https://www.digikey.com/product/277-14958",
            "datasheet_url": "https://example.com/datasheet.pdf",
            "primary_photo": "https://example.com/photo.jpg",
            "unit_price": 125.50,
            "quantity_available": 500,
            "manufacturer": {"name": "Siemens"},
            "parameters": [
                {"parameter_name": "Voltage", "value": "400V"},
                {"parameter_name": "Current", "value": "25A"},
            ],
        }

        part.update_from_digikey(digikey_data)

        assert part.digikey_lookup_attempted is True
        assert part.digikey_lookup_success is True
        assert part.digikey_part_number == "277-14958-ND"
        assert part.digikey_description == "CONTACTOR AC-3 11KW 400V"
        assert part.unit_price == 125.50
        assert part.stock_quantity == 500
        assert part.manufacturer == "Siemens"
        assert part.parameters["Voltage"] == "400V"
        assert part.parameters["Current"] == "25A"

    def test_update_from_empty_digikey(self) -> None:
        """Test updating part with empty DigiKey response."""
        part = LibraryPart(manufacturer_part_number="UNKNOWN-PART")

        part.update_from_digikey({})

        assert part.digikey_lookup_attempted is True
        assert part.digikey_lookup_success is False

    def test_to_dict_and_from_dict(self) -> None:
        """Test serialization and deserialization."""
        part = LibraryPart(
            manufacturer_part_number="3RT2026-1DB40-1AAO",
            manufacturer="Siemens",
            description="Contactor",
            voltage_rating="400VAC",
            tags=["power", "motor control"],
            notes="Main contactor for motor M1",
        )

        # Serialize
        data = part.to_dict()

        assert data["manufacturer_part_number"] == "3RT2026-1DB40-1AAO"
        assert data["manufacturer"] == "Siemens"
        assert "Contactor" in data["description"]
        assert data["tags"] == ["power", "motor control"]

        # Deserialize
        part2 = LibraryPart.from_dict(data)

        assert part2.manufacturer_part_number == part.manufacturer_part_number
        assert part2.manufacturer == part.manufacturer
        assert part2.description == part.description
        assert part2.tags == part.tags

    def test_equality_based_on_part_number(self) -> None:
        """Test that equality is based on manufacturer part number."""
        part1 = LibraryPart(
            manufacturer_part_number="3RT2026-1DB40-1AAO",
            description="Description 1",
        )
        part2 = LibraryPart(
            manufacturer_part_number="3RT2026-1DB40-1AAO",
            description="Description 2",
        )
        part3 = LibraryPart(
            manufacturer_part_number="DIFFERENT-PART",
            description="Description 1",
        )

        assert part1 == part2
        assert part1 != part3
        assert hash(part1) == hash(part2)

    def test_get_display_name(self) -> None:
        """Test display name generation."""
        part1 = LibraryPart(
            manufacturer_part_number="3RT2026-1DB40-1AAO",
            manufacturer="Siemens",
        )
        part2 = LibraryPart(manufacturer_part_number="3RT2026-1DB40-1AAO")

        assert part1.get_display_name() == "Siemens 3RT2026-1DB40-1AAO"
        assert part2.get_display_name() == "3RT2026-1DB40-1AAO"

    def test_str_representation(self) -> None:
        """Test string representation."""
        part = LibraryPart(
            manufacturer_part_number="3RT2026-1DB40-1AAO",
            manufacturer="Siemens",
            description="Contactor AC-3",
        )

        str_repr = str(part)

        assert "3RT2026-1DB40-1AAO" in str_repr
        assert "Siemens" in str_repr
        assert "Contactor AC-3" in str_repr


class TestProjectComponent:
    """Tests for the ProjectComponent model."""

    def test_create_minimal_component(self) -> None:
        """Test creating a component with only required fields."""
        component = ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="3RT2026-1DB40-1AAO",
        )

        assert component.project_id == "DRAWER.pdf"
        assert component.device_tag == "-K1"
        assert component.manufacturer_part_number == "3RT2026-1DB40-1AAO"
        assert component.page == 0
        assert component.x == 0.0

    def test_create_full_component(self) -> None:
        """Test creating a component with all fields."""
        component = ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="3RT2026-1DB40-1AAO",
            page=5,
            x=100.0,
            y=200.0,
            width=50.0,
            height=40.0,
            designation="Main Contactor",
            technical_data="11kW, 400VAC",
            function_description="Controls motor M1",
            circuit_type="power",
            voltage_level="400VAC",
            initial_state="de-energized",
        )

        assert component.page == 5
        assert component.x == 100.0
        assert component.designation == "Main Contactor"
        assert component.circuit_type == "power"

    def test_required_fields(self) -> None:
        """Test that required fields are validated."""
        with pytest.raises(ValueError, match="project_id is required"):
            ProjectComponent(
                project_id="",
                device_tag="-K1",
                manufacturer_part_number="PART",
            )

        with pytest.raises(ValueError, match="device_tag is required"):
            ProjectComponent(
                project_id="test.pdf",
                device_tag="",
                manufacturer_part_number="PART",
            )

        with pytest.raises(ValueError, match="manufacturer_part_number is required"):
            ProjectComponent(
                project_id="test.pdf",
                device_tag="-K1",
                manufacturer_part_number="",
            )

    def test_device_tag_normalization(self) -> None:
        """Test that device tags are trimmed but case preserved."""
        component = ProjectComponent(
            project_id="test.pdf",
            device_tag="  -K1  ",
            manufacturer_part_number="PART",
        )

        # Trimmed but case preserved (industrial tags are case-sensitive)
        assert component.device_tag == "-K1"

    def test_part_number_normalization(self) -> None:
        """Test that part numbers are normalized."""
        component = ProjectComponent(
            project_id="test.pdf",
            device_tag="-K1",
            manufacturer_part_number="  3rt2026  ",
        )

        assert component.manufacturer_part_number == "3RT2026"

    def test_add_position(self) -> None:
        """Test adding additional positions."""
        component = ProjectComponent(
            project_id="test.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART",
            page=5,
            x=100.0,
            y=200.0,
        )

        component.add_position(page=10, x=150.0, y=250.0, confidence=0.9)

        assert len(component.additional_positions) == 1
        assert component.additional_positions[0]["page"] == 10
        assert component.additional_positions[0]["x"] == 150.0
        assert component.additional_positions[0]["confidence"] == 0.9

    def test_get_all_pages(self) -> None:
        """Test getting all pages where component appears."""
        component = ProjectComponent(
            project_id="test.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART",
            page=5,
            x=100.0,
            y=200.0,
        )
        component.add_position(page=10, x=150.0, y=250.0)
        component.add_position(page=3, x=50.0, y=100.0)

        pages = component.get_all_pages()

        assert pages == [3, 5, 10]  # Sorted

    def test_get_position_for_page(self) -> None:
        """Test getting position for a specific page."""
        component = ProjectComponent(
            project_id="test.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART",
            page=5,
            x=100.0,
            y=200.0,
        )
        component.add_position(page=10, x=150.0, y=250.0)

        # Primary position
        pos5 = component.get_position_for_page(5)
        assert pos5 is not None
        assert pos5["x"] == 100.0

        # Additional position
        pos10 = component.get_position_for_page(10)
        assert pos10 is not None
        assert pos10["x"] == 150.0

        # Non-existent page
        pos99 = component.get_position_for_page(99)
        assert pos99 is None

    def test_assign_terminal(self) -> None:
        """Test terminal assignment."""
        component = ProjectComponent(
            project_id="test.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART",
        )

        component.assign_terminal("A1", "+24V")
        component.assign_terminal("A2", "0V")
        component.assign_terminal("13-14", "K2 coil")

        assert component.terminal_assignments["A1"] == "+24V"
        assert component.terminal_assignments["A2"] == "0V"
        assert component.terminal_assignments["13-14"] == "K2 coil"

    def test_to_dict_and_from_dict(self) -> None:
        """Test serialization and deserialization."""
        component = ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="3RT2026-1DB40-1AAO",
            page=5,
            x=100.0,
            y=200.0,
            designation="Main Contactor",
            circuit_type="power",
            notes="Test component",
        )
        component.assign_terminal("A1", "+24V")
        component.add_position(page=10, x=150.0, y=250.0)

        # Serialize
        data = component.to_dict()

        assert data["project_id"] == "DRAWER.pdf"
        assert data["device_tag"] == "-K1"
        assert data["terminal_assignments"]["A1"] == "+24V"
        assert len(data["additional_positions"]) == 1

        # Deserialize
        component2 = ProjectComponent.from_dict(data)

        assert component2.project_id == component.project_id
        assert component2.device_tag == component.device_tag
        assert component2.terminal_assignments == component.terminal_assignments
        assert len(component2.additional_positions) == 1

    def test_get_unique_id(self) -> None:
        """Test unique ID generation."""
        component = ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART",
        )

        assert component.get_unique_id() == "DRAWER.pdf::-K1"

    def test_equality_based_on_project_and_tag(self) -> None:
        """Test that equality is based on project_id and device_tag."""
        comp1 = ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART1",
        )
        comp2 = ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART2",  # Different part
        )
        comp3 = ProjectComponent(
            project_id="OTHER.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART1",
        )

        assert comp1 == comp2  # Same project and tag
        assert comp1 != comp3  # Different project
        assert hash(comp1) == hash(comp2)

    def test_str_representation(self) -> None:
        """Test string representation."""
        component = ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="3RT2026-1DB40-1AAO",
            designation="Main Contactor",
            circuit_type="power",
        )

        str_repr = str(component)

        assert "-K1" in str_repr
        assert "Main Contactor" in str_repr
        assert "3RT2026-1DB40-1AAO" in str_repr
        assert "power" in str_repr
