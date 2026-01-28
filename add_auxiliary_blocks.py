"""Add Auxiliary Blocks to existing component library."""

from pathlib import Path
from electrical_schematics.config.settings import get_settings
from electrical_schematics.database.manager import DatabaseManager, ComponentTemplate


def add_auxiliary_blocks():
    """Add Auxiliary Block components to the library."""
    print("=" * 60)
    print("ADDING AUXILIARY BLOCKS TO COMPONENT LIBRARY")
    print("=" * 60)

    # Get database path
    settings = get_settings()
    db_path = settings.get_database_path()
    print(f"\nDatabase path: {db_path}")

    db = DatabaseManager(db_path)

    # Check if Auxiliary Blocks already exist
    existing = db.search_templates("Auxiliary Block")
    if existing:
        print(f"\nAuxiliary Blocks already exist ({len(existing)} found):")
        for comp in existing:
            print(f"  - {comp.name}")
        db.close()
        return

    # Define the new Auxiliary Block components
    auxiliary_blocks = [
        {
            "category": "Contactors/Relays",
            "subcategory": "Auxiliary Blocks",
            "name": "Auxiliary Block 2NO+2NC",
            "designation_prefix": "K",
            "component_type": "contactor",
            "default_voltage": "400VAC",
            "description": "Front-mount auxiliary contact block, 2NO+2NC",
            "manufacturer": "Siemens",
            "part_number": "3RH2911-1XA22"
        },
        {
            "category": "Contactors/Relays",
            "subcategory": "Auxiliary Blocks",
            "name": "Auxiliary Block 4NO",
            "designation_prefix": "K",
            "component_type": "contactor",
            "default_voltage": "400VAC",
            "description": "Front-mount auxiliary contact block, 4NO",
            "manufacturer": "Siemens",
            "part_number": "3RH2911-1XA40"
        },
        {
            "category": "Contactors/Relays",
            "subcategory": "Auxiliary Blocks",
            "name": "Auxiliary Block 1NO+1NC",
            "designation_prefix": "K",
            "component_type": "contactor",
            "default_voltage": "400VAC",
            "description": "Front-mount auxiliary contact block, 1NO+1NC",
            "manufacturer": "Siemens",
            "part_number": "3RH2911-1XA11"
        },
        {
            "category": "Contactors/Relays",
            "subcategory": "Auxiliary Blocks",
            "name": "Auxiliary Block Side Mount 2NO",
            "designation_prefix": "K",
            "component_type": "contactor",
            "default_voltage": "400VAC",
            "description": "Side-mount auxiliary contact block, 2NO",
            "manufacturer": "Siemens",
            "part_number": "3RH2921-1HA20"
        },
        {
            "category": "Contactors/Relays",
            "subcategory": "Auxiliary Blocks",
            "name": "Auxiliary Block Side Mount 2NC",
            "designation_prefix": "K",
            "component_type": "contactor",
            "default_voltage": "400VAC",
            "description": "Side-mount auxiliary contact block, 2NC",
            "manufacturer": "Siemens",
            "part_number": "3RH2921-1HA02"
        },
        {
            "category": "Contactors/Relays",
            "subcategory": "Auxiliary Blocks",
            "name": "Auxiliary Block Instantaneous 4NO",
            "designation_prefix": "K",
            "component_type": "contactor",
            "default_voltage": "400VAC",
            "description": "Instantaneous auxiliary contact block, 4NO, 10A",
            "manufacturer": "ABB",
            "part_number": "CA5-40"
        },
    ]

    print(f"\nAdding {len(auxiliary_blocks)} Auxiliary Block components...")

    for comp_data in auxiliary_blocks:
        template = ComponentTemplate(
            id=None,
            category=comp_data["category"],
            subcategory=comp_data["subcategory"],
            name=comp_data["name"],
            designation_prefix=comp_data["designation_prefix"],
            component_type=comp_data["component_type"],
            default_voltage=comp_data["default_voltage"],
            description=comp_data["description"],
            manufacturer=comp_data["manufacturer"],
            part_number=comp_data["part_number"],
            datasheet_url=None,
            image_path=None,
            symbol_svg=None
        )

        component_id = db.add_component_template(template)
        print(f"  Added: {comp_data['name']} (ID: {component_id})")

    db.close()

    print(f"\n✓ Successfully added {len(auxiliary_blocks)} Auxiliary Block components!")
    print("\nRestart the application to see them in the Component Library.")


if __name__ == "__main__":
    add_auxiliary_blocks()
