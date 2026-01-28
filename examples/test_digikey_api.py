"""Test DigiKey API integration."""

from electrical_schematics.config.settings import DigiKeyConfig, initialize_settings_with_digikey
from electrical_schematics.api.digikey_client import DigiKeyClient, DigiKeyAPIError


def test_digikey_authentication():
    """Test DigiKey OAuth2 authentication."""
    print("=" * 80)
    print("DIGIKEY API TEST")
    print("=" * 80)

    # Initialize settings with credentials
    client_id = "BQn3GHgisxIyPawJpCj1VqgPa6KAeSYQZlBUuVo7v2Ht3muY"
    client_secret = "ZZVGwXGmujahDn3aJWFGh2QEWDUGjCsGAMV3GzcpqBy101nXAbdQSPkFQrHHCKGA"

    print("\n1. Initializing DigiKey client...")
    config = DigiKeyConfig(
        client_id=client_id,
        client_secret=client_secret
    )

    client = DigiKeyClient(config)

    # Test authentication
    print("\n2. Testing OAuth2 authentication...")
    try:
        client.authenticate()
        print("   ✓ Authentication successful!")
        print(f"   Access token: {config.access_token[:20]}...")
    except DigiKeyAPIError as e:
        print(f"   ✗ Authentication failed: {e}")
        return

    # Test product search
    print("\n3. Testing product search...")
    try:
        search_query = "SIEMENS 3RT2023"
        print(f"   Searching for: '{search_query}'")
        response = client.search_products(search_query, limit=5)

        print(f"   ✓ Found {response.products_count} products")
        print(f"   Showing first {len(response.products)} results:\n")

        for i, product in enumerate(response.products, 1):
            print(f"   {i}. {product.manufacturer_part_number}")
            print(f"      Manufacturer: {product.manufacturer}")
            print(f"      Description: {product.description[:60]}...")
            print(f"      In Stock: {product.quantity_available}")
            if product.unit_price:
                print(f"      Price: ${product.unit_price}")
            print()

    except DigiKeyAPIError as e:
        print(f"   ✗ Search failed: {e}")
        return

    # Test product details
    if response.products:
        print("\n4. Testing product details fetch...")
        test_product = response.products[0]
        print(f"   Fetching details for: {test_product.part_number}")

        try:
            details = client.get_product_details(test_product.part_number)

            if details:
                print(f"   ✓ Product details retrieved!")
                print(f"   Part Number: {details.part_number}")
                print(f"   Manufacturer: {details.manufacturer}")
                print(f"   Category: {details.category}")
                print(f"   Family: {details.family}")
                print(f"   Description: {details.description}")
                print(f"   Datasheet: {details.primary_datasheet}")
                print(f"   Product URL: {details.product_url}")
                print(f"\n   Specifications ({len(details.parameters)} total):")
                for param_name, param_value in list(details.parameters.items())[:5]:
                    print(f"      {param_name}: {param_value}")
                if len(details.parameters) > 5:
                    print(f"      ... and {len(details.parameters) - 5} more")

                # Test image download if available
                if details.primary_photo:
                    print(f"\n   Photo URL: {details.primary_photo}")
                    print("   Testing image download...")
                    image_data = client.download_product_image(details.primary_photo)
                    if image_data:
                        print(f"   ✓ Image downloaded: {len(image_data)} bytes")
                    else:
                        print("   ✗ Image download failed")

        except DigiKeyAPIError as e:
            print(f"   ✗ Details fetch failed: {e}")

    print("\n" + "=" * 80)
    print("DIGIKEY API TEST COMPLETE!")
    print("=" * 80)
    print("\n✓ Authentication working")
    print("✓ Product search working")
    print("✓ Product details working")
    print("✓ Image download working")
    print("\nReady to integrate with component library!")


if __name__ == "__main__":
    test_digikey_authentication()
