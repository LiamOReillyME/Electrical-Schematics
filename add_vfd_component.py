"""Script to add VFD component to library by fetching from DigiKey."""

from pathlib import Path
from electrical_schematics.database import initialize_database_with_defaults
from electrical_schematics.config import get_settings
from electrical_schematics.api.digikey_client import DigiKeyClient, DigiKeyAPIError


def add_vfd_from_digikey(part_number: str = "sk520E-751-340-a"):
    """Add VFD component from DigiKey API.

    Args:
        part_number: DigiKey or manufacturer part number
    """
    print(f"Fetching VFD component: {part_number}")

    # Initialize database
    settings = get_settings()
    db_path = settings.get_database_path()
    db_manager = initialize_database_with_defaults(db_path)

    # Get DigiKey configuration
    digikey_config = settings.get_digikey_config()

    if not digikey_config.client_id or not digikey_config.client_secret:
        print("ERROR: DigiKey API credentials not configured.")
        print("Please set up your Client ID and Client Secret in the config.")
        return False

    try:
        # Fetch product from DigiKey
        print("Connecting to DigiKey API...")
        client = DigiKeyClient(digikey_config)
        product = client.get_product_details(part_number)

        if not product:
            print(f"ERROR: Product not found: {part_number}")
            return False

        print(f"\nProduct found:")
        print(f"  Manufacturer: {product.manufacturer}")
        print(f"  Part Number: {product.manufacturer_part_number}")
        print(f"  Description: {product.description}")
        print(f"  Category: {product.category}")
        print(f"  Family: {product.family}")

        # Extract voltage from parameters
        voltage = ""
        if product.parameters:
            for key in ['Voltage - Rated', 'Voltage Rating', 'Voltage - Supply', 'Input Voltage']:
                if key in product.parameters:
                    voltage = product.parameters[key]
                    break

        print(f"  Voltage: {voltage}")

        # Save to database
        print("\nSaving to component library...")
        conn = db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO component_library (
                category, subcategory, name, designation_prefix,
                component_type, default_voltage, manufacturer,
                part_number, datasheet_url, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "VFD",  # category
            product.family or "",  # subcategory
            f"{product.manufacturer} {product.manufacturer_part_number}",  # name
            "VFD",  # designation_prefix
            "vfd",  # component_type
            voltage,  # default_voltage
            product.manufacturer,
            product.manufacturer_part_number,
            product.primary_datasheet or "",
            product.description
        ))

        component_id = cursor.lastrowid

        # Save technical specifications
        if product.parameters:
            print(f"\nSaving {len(product.parameters)} technical specifications...")
            for param_name, param_value in product.parameters.items():
                cursor.execute("""
                    INSERT INTO component_specs (component_id, spec_name, spec_value)
                    VALUES (?, ?, ?)
                """, (component_id, param_name, str(param_value)))

        # Download and save image if available
        if product.primary_photo:
            print("\nDownloading product image...")
            image_data = client.download_product_image(product.primary_photo)

            if image_data:
                # Save to database
                cursor.execute("""
                    INSERT INTO component_images (
                        component_id, image_type, image_data, format
                    ) VALUES (?, ?, ?, ?)
                """, (component_id, 'photo', image_data, 'jpg'))
                print("  Image saved to database")

        conn.commit()

        print(f"\n✓ SUCCESS: VFD component added to library (ID: {component_id})")
        print(f"  Category: VFD")
        print(f"  Name: {product.manufacturer} {product.manufacturer_part_number}")

        return True

    except DigiKeyAPIError as e:
        print(f"\nERROR: DigiKey API error: {e}")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys

    part_number = "sk520E-751-340-a"
    if len(sys.argv) > 1:
        part_number = sys.argv[1]

    success = add_vfd_from_digikey(part_number)
    sys.exit(0 if success else 1)
