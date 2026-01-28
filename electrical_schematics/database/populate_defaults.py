"""Populate database with default component library."""

import json
from pathlib import Path
from electrical_schematics.database.manager import DatabaseManager, ComponentTemplate


def load_default_library(db_manager: DatabaseManager) -> int:
    """Load default component library from JSON file.

    Args:
        db_manager: Database manager instance

    Returns:
        Number of components loaded
    """
    # Find default library JSON file
    config_dir = Path(__file__).parent.parent / "config"
    library_file = config_dir / "default_library.json"

    if not library_file.exists():
        print(f"Error: Default library not found at {library_file}")
        return 0

    # Load JSON
    with open(library_file, 'r') as f:
        data = json.load(f)

    components = data.get('components', [])
    loaded_count = 0

    print(f"Loading {len(components)} components from default library...")

    with db_manager.transaction():
        for comp_data in components:
            template = ComponentTemplate(
                id=None,
                category=comp_data.get('category'),
                subcategory=comp_data.get('subcategory'),
                name=comp_data.get('name'),
                designation_prefix=comp_data.get('designation_prefix'),
                component_type=comp_data.get('component_type'),
                default_voltage=comp_data.get('default_voltage'),
                description=comp_data.get('description'),
                manufacturer=comp_data.get('manufacturer'),
                part_number=comp_data.get('part_number'),
                datasheet_url=None,
                image_path=None,
                symbol_svg=None
            )

            db_manager.add_component_template(template)
            loaded_count += 1

    print(f"✓ Successfully loaded {loaded_count} components")
    return loaded_count


def initialize_database_with_defaults(db_path: Path) -> DatabaseManager:
    """Initialize database and populate with default library.

    Args:
        db_path: Path to database file

    Returns:
        Initialized DatabaseManager instance
    """
    # Create database manager (this creates schema)
    db_manager = DatabaseManager(db_path)

    # Check if library is already populated
    existing_count = len(db_manager.get_component_templates())

    if existing_count > 0:
        print(f"Database already contains {existing_count} components")
        return db_manager

    # Load defaults
    load_default_library(db_manager)

    return db_manager


if __name__ == "__main__":
    # For testing: create database in current directory
    test_db_path = Path("test_components.db")
    print(f"Creating test database: {test_db_path}")

    db = initialize_database_with_defaults(test_db_path)

    # Verify
    categories = db.get_categories()
    print(f"\nCategories in database: {categories}")

    for category in categories:
        templates = db.get_component_templates(category)
        print(f"  {category}: {len(templates)} components")

    db.close()
    print(f"\n✓ Test database created successfully at {test_db_path}")
