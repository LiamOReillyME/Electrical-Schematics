#!/usr/bin/env python3
"""Clean up component library by removing generic templates and E-code components.

This script removes:
1. All "generic template" components from library_parts
2. All components with E-code part numbers (starting with 'E')
3. Keeps only real DigiKey parts with complete data
"""

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def cleanup_library(library_path: Path, backup: bool = True) -> None:
    """Clean up the component library.

    Args:
        library_path: Path to default_library.json
        backup: If True, create backup before modifying
    """
    if not library_path.exists():
        logger.error(f"Library file not found: {library_path}")
        return

    # Load library
    logger.info(f"Loading library from {library_path}")
    with open(library_path, 'r', encoding='utf-8') as f:
        library = json.load(f)

    # Create backup
    if backup:
        backup_path = library_path.with_suffix('.json.backup')
        logger.info(f"Creating backup at {backup_path}")
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(library, f, indent=2, ensure_ascii=False)

    # Count original entries
    original_parts = len(library.get('library_parts', []))
    original_projects = sum(
        len(components) for components in library.get('projects', {}).values()
    )

    logger.info(f"Original library: {original_parts} parts, {original_projects} project components")

    # Clean library_parts
    cleaned_parts = []
    removed_parts = []

    for part in library.get('library_parts', []):
        part_number = part.get('manufacturer_part_number', '')

        # Remove if missing part number
        if not part_number:
            removed_parts.append(f"(no part number)")
            continue

        # Remove if generic template
        if 'generic' in part.get('description', '').lower() or \
           'template' in part.get('description', '').lower():
            removed_parts.append(f"{part_number} (generic template)")
            continue

        # Remove if E-code
        if part_number.startswith('E'):
            removed_parts.append(f"{part_number} (E-code)")
            continue

        # Keep part
        cleaned_parts.append(part)

    library['library_parts'] = cleaned_parts

    # Clean project components (remove E-codes)
    cleaned_projects = {}
    for project_id, components in library.get('projects', {}).items():
        cleaned_components = {}
        for device_tag, component in components.items():
            part_number = component.get('manufacturer_part_number', '')

            # Skip E-codes
            if part_number and part_number.startswith('E'):
                removed_parts.append(f"{project_id}::{device_tag} -> {part_number} (E-code)")
                continue

            # Skip if no part number
            if not part_number:
                removed_parts.append(f"{project_id}::{device_tag} (no part number)")
                continue

            cleaned_components[device_tag] = component

        if cleaned_components:
            cleaned_projects[project_id] = cleaned_components

    library['projects'] = cleaned_projects

    # Count cleaned entries
    cleaned_parts_count = len(library['library_parts'])
    cleaned_projects_count = sum(
        len(components) for components in library['projects'].values()
    )

    # Save cleaned library
    logger.info(f"Saving cleaned library to {library_path}")
    with open(library_path, 'w', encoding='utf-8') as f:
        json.dump(library, f, indent=2, ensure_ascii=False)

    # Report
    logger.info("")
    logger.info("=" * 60)
    logger.info("CLEANUP COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Parts: {original_parts} -> {cleaned_parts_count} "
                f"(removed {original_parts - cleaned_parts_count})")
    logger.info(f"Project components: {original_projects} -> {cleaned_projects_count} "
                f"(removed {original_projects - cleaned_projects_count})")
    logger.info("")

    if removed_parts:
        logger.info(f"Removed {len(removed_parts)} items:")
        for item in removed_parts[:20]:  # Show first 20
            logger.info(f"  - {item}")
        if len(removed_parts) > 20:
            logger.info(f"  ... and {len(removed_parts) - 20} more")


def main():
    """Main entry point."""
    # Get library path
    library_path = Path(__file__).parent / "electrical_schematics" / "config" / "default_library.json"

    if not library_path.exists():
        logger.error(f"Library not found: {library_path}")
        return

    # Confirm action
    print("=" * 60)
    print("COMPONENT LIBRARY CLEANUP")
    print("=" * 60)
    print(f"Library: {library_path}")
    print("")
    print("This will remove:")
    print("  - All generic template components")
    print("  - All E-code components")
    print("")
    print("A backup will be created at default_library.json.backup")
    print("")
    response = input("Continue? (y/n): ")

    if response.lower() != 'y':
        print("Cancelled.")
        return

    # Run cleanup
    cleanup_library(library_path, backup=True)


if __name__ == '__main__':
    main()
