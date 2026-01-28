#!/usr/bin/env python3
"""Import parts from DigiKey with complete data validation and asset downloading.

This script:
1. Looks up parts in DigiKey API (with hyphen retry logic)
2. Validates complete data (all required fields)
3. Downloads photos and datasheets
4. Parses contact configuration from description
5. Generates dynamic IEC 60617 icons
6. Adds parts to library with all enrichments
"""

import sys
import logging
from pathlib import Path
from typing import List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from electrical_schematics.api.digikey_client import DigiKeyClient
from electrical_schematics.config.settings import DigiKeyConfig
from electrical_schematics.models.library_part import LibraryPart
from electrical_schematics.services.component_library import ComponentLibrary
from electrical_schematics.services.asset_downloader import AssetDownloader
from electrical_schematics.services.contact_parser import ContactConfigParser
from electrical_schematics.services.dynamic_icon_generator import DynamicIconGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Part numbers from DRAWER.pdf (example list - replace with actual parts)
DRAWER_PARTS = [
    "3RT2026-1DB40-1AAO",  # Siemens Contactor
    "6ES7 511-1AK02-0AB0",  # Siemens PLC
    "6ES7 521-1BH10-0AA0",  # Siemens DI Module
    "6ES7 522-1BH01-0AA0",  # Siemens DO Module
    "3RV2011-1JA10",        # Siemens Circuit Breaker
    "3RF2020-1AA02",        # Siemens Solid State Relay
    "6EP1332-1SH43",        # Siemens Power Supply
    "6AV2124-0MC01-0AX0",   # Siemens HMI
]


def import_part(
    part_number: str,
    digikey_client: DigiKeyClient,
    downloader: AssetDownloader,
    parser: ContactConfigParser,
    icon_gen: DynamicIconGenerator,
    library: ComponentLibrary
) -> bool:
    """Import a single part with complete enrichment.

    Args:
        part_number: Manufacturer part number
        digikey_client: DigiKey API client
        downloader: Asset downloader
        parser: Contact configuration parser
        icon_gen: Icon generator
        library: Component library

    Returns:
        True if part was successfully imported
    """
    logger.info(f"\n{'=' * 80}")
    logger.info(f"Processing part: {part_number}")
    logger.info(f"{'=' * 80}")

    # Step 1: DigiKey lookup with retry
    logger.info("Step 1: DigiKey lookup...")
    details = digikey_client.get_product_details_with_retry(part_number)

    if not details:
        logger.warning(f"Part not found in DigiKey: {part_number}")
        return False

    # Step 2: Validate complete data
    logger.info("Step 2: Validating data completeness...")
    if not digikey_client.validate_complete_data(details):
        logger.warning(f"Incomplete data for {part_number} - skipping")
        return False

    logger.info(f"  Manufacturer: {details.manufacturer}")
    logger.info(f"  Description: {details.description}")
    logger.info(f"  Category: {details.category}")
    logger.info(f"  DigiKey PN: {details.part_number}")

    # Step 3: Download assets
    logger.info("Step 3: Downloading assets...")
    photo_path, datasheet_path = downloader.download_both(
        photo_url=details.primary_photo,
        datasheet_url=details.primary_datasheet,
        part_number=details.manufacturer_part_number,
        force=False
    )

    if photo_path:
        logger.info(f"  Photo: {photo_path}")
    else:
        logger.warning(f"  Photo download failed")

    if datasheet_path:
        logger.info(f"  Datasheet: {datasheet_path}")
    else:
        logger.warning(f"  Datasheet download failed")

    # Step 4: Parse contact configuration
    logger.info("Step 4: Parsing contact configuration...")
    contact_config = parser.parse_description(details.description, details.category)

    logger.info(f"  Component type: {contact_config.component_type}")
    logger.info(f"  NO contacts: {contact_config.no_contacts}")
    logger.info(f"  NC contacts: {contact_config.nc_contacts}")
    logger.info(f"  Poles: {contact_config.poles}")

    # Step 5: Generate dynamic icon
    logger.info("Step 5: Generating dynamic icon...")
    icon_svg = icon_gen.generate_icon(contact_config)
    logger.info(f"  Icon SVG: {len(icon_svg)} characters")

    # Step 6: Extract unit price
    unit_price = None
    if details.standard_pricing:
        unit_price = details.standard_pricing[0].get('unit_price')
        logger.info(f"  Unit price: ${unit_price:.2f}")

    # Step 7: Create LibraryPart
    logger.info("Step 6: Creating library part...")
    part = LibraryPart(
        manufacturer_part_number=details.manufacturer_part_number,
        manufacturer=details.manufacturer,
        description=details.description,
        category=details.category,
        technical_data=details.detailed_description or "",
        digikey_part_number=details.part_number,
        digikey_description=details.description,
        digikey_url=details.product_url,
        datasheet_url=details.primary_datasheet,
        image_url=details.primary_photo,
        photo_path=str(photo_path) if photo_path else None,
        datasheet_path=str(datasheet_path) if datasheet_path else None,
        unit_price=unit_price,
        stock_quantity=details.quantity_available,
        parameters=details.parameters,
        contact_config=contact_config.to_dict(),
        icon_svg=icon_svg,
        digikey_lookup_attempted=True,
        digikey_lookup_success=True,
    )

    # Step 8: Add to library
    logger.info("Step 7: Adding to library...")
    is_new = library.add_part(part)

    if is_new:
        logger.info(f"✓ Successfully added new part: {part_number}")
    else:
        logger.info(f"✓ Successfully updated existing part: {part_number}")

    return True


def import_parts(part_numbers: List[str], config_path: Optional[Path] = None) -> None:
    """Import multiple parts from DigiKey.

    Args:
        part_numbers: List of manufacturer part numbers
        config_path: Optional path to DigiKey config
    """
    logger.info("=" * 80)
    logger.info("DIGIKEY PARTS IMPORT")
    logger.info("=" * 80)
    logger.info(f"Parts to import: {len(part_numbers)}")
    logger.info("")

    # Initialize services
    logger.info("Initializing services...")

    try:
        # DigiKey client
        if config_path and config_path.exists():
            config = DigiKeyConfig.from_file(config_path)
        else:
            config = DigiKeyConfig()

        digikey_client = DigiKeyClient(config)
        logger.info("  DigiKey client: OK")

        # Asset downloader
        downloader = AssetDownloader()
        logger.info(f"  Asset downloader: OK (assets: {downloader.assets_dir})")

        # Contact parser
        parser = ContactConfigParser()
        logger.info("  Contact parser: OK")

        # Icon generator
        icon_gen = DynamicIconGenerator()
        logger.info("  Icon generator: OK")

        # Component library
        library = ComponentLibrary()
        library.load()
        logger.info(f"  Component library: OK (loaded {len(library.get_all_parts())} parts)")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        return

    # Import parts
    logger.info("")
    logger.info("Starting import...")

    success_count = 0
    failed_count = 0
    skipped_count = 0

    for i, part_number in enumerate(part_numbers, 1):
        logger.info(f"\n[{i}/{len(part_numbers)}] {part_number}")

        # Check if already exists with complete data
        existing = library.get_part(part_number)
        if existing and existing.has_complete_digikey_data() and existing.has_local_assets():
            logger.info(f"  Part already exists with complete data - skipping")
            skipped_count += 1
            continue

        try:
            success = import_part(
                part_number=part_number,
                digikey_client=digikey_client,
                downloader=downloader,
                parser=parser,
                icon_gen=icon_gen,
                library=library
            )

            if success:
                success_count += 1
            else:
                failed_count += 1

        except Exception as e:
            logger.error(f"Error importing {part_number}: {e}", exc_info=True)
            failed_count += 1

    # Save library
    logger.info("")
    logger.info("Saving library...")
    library.save()
    logger.info(f"  Library saved: {library.library_path}")

    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("IMPORT COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Success: {success_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info(f"Skipped: {skipped_count}")
    logger.info(f"Total: {len(part_numbers)}")
    logger.info("")

    # Library stats
    stats = library.get_stats()
    logger.info("Library statistics:")
    logger.info(f"  Total parts: {stats.total_parts}")
    logger.info(f"  With DigiKey data: {stats.parts_with_digikey}")
    logger.info(f"  Without DigiKey data: {stats.parts_without_digikey}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Import parts from DigiKey with complete enrichment"
    )
    parser.add_argument(
        '--config',
        type=Path,
        help="Path to DigiKey config file"
    )
    parser.add_argument(
        '--parts',
        nargs='+',
        help="Part numbers to import (space-separated)"
    )
    parser.add_argument(
        '--file',
        type=Path,
        help="File with part numbers (one per line)"
    )

    args = parser.parse_args()

    # Get part numbers
    part_numbers = []

    if args.parts:
        part_numbers.extend(args.parts)

    if args.file and args.file.exists():
        with open(args.file, 'r') as f:
            for line in f:
                part_num = line.strip()
                if part_num and not part_num.startswith('#'):
                    part_numbers.append(part_num)

    # Use default list if none provided
    if not part_numbers:
        logger.info("No parts specified, using default DRAWER parts list")
        part_numbers = DRAWER_PARTS

    # Import
    import_parts(part_numbers, config_path=args.config)


if __name__ == '__main__':
    main()
