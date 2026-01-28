"""Tests for the ComponentLibrary service."""

import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from electrical_schematics.models import LibraryPart, ProjectComponent
from electrical_schematics.services import ComponentLibrary


class TestComponentLibrary:
    """Tests for the ComponentLibrary service."""

    def test_create_library(self) -> None:
        """Test creating a new library."""
        library = ComponentLibrary()

        assert library.get_all_parts() == []
        assert library.get_all_projects() == []
        assert not library.is_modified

    def test_add_part(self) -> None:
        """Test adding a part to the library."""
        library = ComponentLibrary()

        part = LibraryPart(
            manufacturer_part_number="3RT2026-1DB40-1AAO",
            manufacturer="Siemens",
            description="Contactor AC-3 11KW/400V",
        )

        result = library.add_part(part)

        assert result is True  # New part
        assert library.part_exists("3RT2026-1DB40-1AAO")
        assert library.is_modified

    def test_add_part_update_existing(self) -> None:
        """Test that adding an existing part updates it."""
        library = ComponentLibrary()

        part1 = LibraryPart(
            manufacturer_part_number="3RT2026-1DB40-1AAO",
            description="Original description",
        )
        part2 = LibraryPart(
            manufacturer_part_number="3RT2026-1DB40-1AAO",
            description="Updated description",
        )

        library.add_part(part1)
        result = library.add_part(part2)

        assert result is False  # Updated, not new
        retrieved = library.get_part("3RT2026-1DB40-1AAO")
        assert retrieved is not None
        assert retrieved.description == "Updated description"

    def test_add_part_preserves_digikey_data(self) -> None:
        """Test that updating a part preserves existing DigiKey data."""
        library = ComponentLibrary()

        part1 = LibraryPart(manufacturer_part_number="TEST-PART")
        part1.update_from_digikey({
            "digi_key_part_number": "123-ND",
            "unit_price": 10.50,
        })
        library.add_part(part1)

        # Add same part without DigiKey data
        part2 = LibraryPart(
            manufacturer_part_number="TEST-PART",
            description="New description",
        )
        library.add_part(part2)

        retrieved = library.get_part("TEST-PART")
        assert retrieved is not None
        assert retrieved.digikey_part_number == "123-ND"
        assert retrieved.unit_price == 10.50
        assert retrieved.description == "New description"

    def test_get_part(self) -> None:
        """Test getting a part by part number."""
        library = ComponentLibrary()
        part = LibraryPart(manufacturer_part_number="3RT2026-1DB40-1AAO")
        library.add_part(part)

        # Exact match
        retrieved = library.get_part("3RT2026-1DB40-1AAO")
        assert retrieved is not None
        assert retrieved.manufacturer_part_number == "3RT2026-1DB40-1AAO"

        # Case-insensitive with whitespace
        retrieved2 = library.get_part("  3rt2026-1db40-1aao  ")
        assert retrieved2 is not None

        # Non-existent
        assert library.get_part("NONEXISTENT") is None

    def test_remove_part(self) -> None:
        """Test removing a part."""
        library = ComponentLibrary()
        part = LibraryPart(manufacturer_part_number="3RT2026-1DB40-1AAO")
        library.add_part(part)

        result = library.remove_part("3RT2026-1DB40-1AAO")

        assert result is True
        assert not library.part_exists("3RT2026-1DB40-1AAO")

        # Removing non-existent part
        assert library.remove_part("NONEXISTENT") is False

    def test_search_parts(self) -> None:
        """Test searching for parts."""
        library = ComponentLibrary()

        library.add_part(LibraryPart(
            manufacturer_part_number="3RT2026-1DB40-1AAO",
            manufacturer="Siemens",
            description="Contactor AC-3",
        ))
        library.add_part(LibraryPart(
            manufacturer_part_number="3RV2011-1AA10",
            manufacturer="Siemens",
            description="Circuit breaker",
        ))
        library.add_part(LibraryPart(
            manufacturer_part_number="6SL3210-1PE21-8AL0",
            manufacturer="Siemens",
            description="VFD Drive",
        ))

        # Search by part number
        results = library.search_parts("3RT")
        assert len(results) == 1
        assert results[0].manufacturer_part_number == "3RT2026-1DB40-1AAO"

        # Search by description
        results = library.search_parts("contactor")
        assert len(results) == 1

        # Search by manufacturer
        results = library.search_parts("siemens")
        assert len(results) == 3

        # No matches
        results = library.search_parts("nonexistent")
        assert len(results) == 0

        # Empty query returns all
        results = library.search_parts("")
        assert len(results) == 3

    def test_add_project_component(self) -> None:
        """Test adding a project component."""
        library = ComponentLibrary()

        component = ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="3RT2026-1DB40-1AAO",
        )

        result = library.add_project_component(component)

        assert result is True  # New component
        assert "DRAWER.pdf" in library.get_all_projects()
        assert library.is_modified

    def test_add_project_component_update_existing(self) -> None:
        """Test that adding an existing component updates it."""
        library = ComponentLibrary()

        comp1 = ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART1",
            designation="Original",
        )
        comp2 = ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART2",  # Different part
            designation="Updated",
        )

        library.add_project_component(comp1)
        result = library.add_project_component(comp2)

        assert result is False  # Updated, not new
        retrieved = library.get_project_component("DRAWER.pdf", "-K1")
        assert retrieved is not None
        assert retrieved.designation == "Updated"
        assert retrieved.manufacturer_part_number == "PART2"

    def test_get_project_component(self) -> None:
        """Test getting a project component."""
        library = ComponentLibrary()
        component = ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART",
        )
        library.add_project_component(component)

        # Found
        retrieved = library.get_project_component("DRAWER.pdf", "-K1")
        assert retrieved is not None
        assert retrieved.device_tag == "-K1"

        # Not found - wrong project
        assert library.get_project_component("OTHER.pdf", "-K1") is None

        # Not found - wrong tag
        assert library.get_project_component("DRAWER.pdf", "-K2") is None

    def test_get_project_components(self) -> None:
        """Test getting all components for a project."""
        library = ComponentLibrary()

        library.add_project_component(ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART1",
        ))
        library.add_project_component(ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K2",
            manufacturer_part_number="PART1",
        ))
        library.add_project_component(ProjectComponent(
            project_id="OTHER.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART2",
        ))

        drawer_components = library.get_project_components("DRAWER.pdf")
        assert len(drawer_components) == 2

        other_components = library.get_project_components("OTHER.pdf")
        assert len(other_components) == 1

        nonexistent = library.get_project_components("NONEXISTENT.pdf")
        assert len(nonexistent) == 0

    def test_remove_project_component(self) -> None:
        """Test removing a project component."""
        library = ComponentLibrary()
        library.add_project_component(ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART",
        ))

        result = library.remove_project_component("DRAWER.pdf", "-K1")

        assert result is True
        assert library.get_project_component("DRAWER.pdf", "-K1") is None

        # Removing non-existent
        assert library.remove_project_component("DRAWER.pdf", "-K99") is False

    def test_remove_project(self) -> None:
        """Test removing all components for a project."""
        library = ComponentLibrary()
        library.add_project_component(ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART",
        ))
        library.add_project_component(ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K2",
            manufacturer_part_number="PART",
        ))

        result = library.remove_project("DRAWER.pdf")

        assert result is True
        assert "DRAWER.pdf" not in library.get_all_projects()

        # Removing non-existent
        assert library.remove_project("NONEXISTENT.pdf") is False

    def test_get_components_for_part(self) -> None:
        """Test finding all components that use a specific part."""
        library = ComponentLibrary()

        # Same part used in multiple places
        library.add_project_component(ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="3RT2026",
        ))
        library.add_project_component(ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K2",
            manufacturer_part_number="3RT2026",
        ))
        library.add_project_component(ProjectComponent(
            project_id="OTHER.pdf",
            device_tag="-K5",
            manufacturer_part_number="3RT2026",
        ))
        library.add_project_component(ProjectComponent(
            project_id="OTHER.pdf",
            device_tag="-K6",
            manufacturer_part_number="DIFFERENT-PART",
        ))

        components = library.get_components_for_part("3RT2026")

        assert len(components) == 3
        device_tags = {c.device_tag for c in components}
        assert device_tags == {"-K1", "-K2", "-K5"}

    def test_get_part_with_usage(self) -> None:
        """Test getting a part with all its usages."""
        library = ComponentLibrary()

        library.add_part(LibraryPart(
            manufacturer_part_number="3RT2026",
            description="Contactor",
        ))
        library.add_project_component(ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="3RT2026",
        ))
        library.add_project_component(ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K2",
            manufacturer_part_number="3RT2026",
        ))

        part, components = library.get_part_with_usage("3RT2026")

        assert part is not None
        assert part.description == "Contactor"
        assert len(components) == 2

    def test_get_component_with_part(self) -> None:
        """Test getting a component with its associated part."""
        library = ComponentLibrary()

        library.add_part(LibraryPart(
            manufacturer_part_number="3RT2026",
            manufacturer="Siemens",
        ))
        library.add_project_component(ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="3RT2026",
        ))

        component, part = library.get_component_with_part("DRAWER.pdf", "-K1")

        assert component is not None
        assert component.device_tag == "-K1"
        assert part is not None
        assert part.manufacturer == "Siemens"

    def test_get_stats(self) -> None:
        """Test getting library statistics."""
        library = ComponentLibrary()

        library.add_part(LibraryPart(manufacturer_part_number="PART1"))
        library.add_part(LibraryPart(manufacturer_part_number="PART2"))
        part3 = LibraryPart(manufacturer_part_number="PART3")
        part3.update_from_digikey({"digi_key_part_number": "123-ND"})
        library.add_part(part3)

        library.add_project_component(ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART1",
        ))
        library.add_project_component(ProjectComponent(
            project_id="DRAWER.pdf",
            device_tag="-K2",
            manufacturer_part_number="PART1",
        ))
        library.add_project_component(ProjectComponent(
            project_id="OTHER.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART2",
        ))

        stats = library.get_stats()

        assert stats.total_parts == 3
        assert stats.total_projects == 2
        assert stats.total_components == 3
        assert stats.parts_with_digikey == 1
        assert stats.parts_without_digikey == 2

    def test_get_parts_needing_digikey_lookup(self) -> None:
        """Test finding parts that need DigiKey lookup."""
        library = ComponentLibrary()

        library.add_part(LibraryPart(manufacturer_part_number="PART1"))
        part2 = LibraryPart(manufacturer_part_number="PART2")
        part2.update_from_digikey({})  # Failed lookup
        library.add_part(part2)
        part3 = LibraryPart(manufacturer_part_number="PART3")
        part3.update_from_digikey({"digi_key_part_number": "123-ND"})
        library.add_part(part3)

        needing_lookup = library.get_parts_needing_digikey_lookup()

        assert len(needing_lookup) == 1
        assert needing_lookup[0].manufacturer_part_number == "PART1"

    def test_save_and_load(self) -> None:
        """Test saving and loading the library."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "library.json"
            library = ComponentLibrary(path)

            # Add data
            library.add_part(LibraryPart(
                manufacturer_part_number="3RT2026",
                manufacturer="Siemens",
            ))
            library.add_project_component(ProjectComponent(
                project_id="DRAWER.pdf",
                device_tag="-K1",
                manufacturer_part_number="3RT2026",
            ))

            # Save
            library.save()
            assert not library.is_modified

            # Verify file exists
            assert path.exists()

            # Load into new library
            library2 = ComponentLibrary(path)
            library2.load()

            # Verify data
            part = library2.get_part("3RT2026")
            assert part is not None
            assert part.manufacturer == "Siemens"

            component = library2.get_project_component("DRAWER.pdf", "-K1")
            assert component is not None
            assert component.manufacturer_part_number == "3RT2026"

    def test_load_nonexistent_file(self) -> None:
        """Test loading from a non-existent file."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nonexistent.json"
            library = ComponentLibrary(path)

            # Should not raise, just start with empty library
            library.load()

            assert library.get_all_parts() == []
            assert library.get_all_projects() == []

    def test_migrate_v1_to_v2(self) -> None:
        """Test migration from v1.0 format to v2.0."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "library.json"

            # Create v1.0 format file
            v1_data = {
                "version": "1.0",
                "components": [
                    {
                        "manufacturer_part_number": "3RT2026",
                        "manufacturer": "Siemens",
                        "description": "Contactor",
                        "voltage_rating": "400VAC",
                    }
                ],
            }
            with open(path, "w") as f:
                json.dump(v1_data, f)

            # Load and verify migration
            library = ComponentLibrary(path)
            library.load()

            part = library.get_part("3RT2026")
            assert part is not None
            assert part.manufacturer == "Siemens"
            assert part.description == "Contactor"

            # Library should be marked as modified (needs saving in new format)
            assert library.is_modified

    def test_clear(self) -> None:
        """Test clearing the library."""
        library = ComponentLibrary()
        library.add_part(LibraryPart(manufacturer_part_number="PART"))
        library.add_project_component(ProjectComponent(
            project_id="test.pdf",
            device_tag="-K1",
            manufacturer_part_number="PART",
        ))

        library.clear()

        assert library.get_all_parts() == []
        assert library.get_all_projects() == []
        assert library.is_modified

    def test_iter_parts(self) -> None:
        """Test iterating over parts."""
        library = ComponentLibrary()
        library.add_part(LibraryPart(manufacturer_part_number="PART1"))
        library.add_part(LibraryPart(manufacturer_part_number="PART2"))
        library.add_part(LibraryPart(manufacturer_part_number="PART3"))

        part_numbers = {part.manufacturer_part_number for part in library.iter_parts()}

        assert part_numbers == {"PART1", "PART2", "PART3"}
