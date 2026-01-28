"""Test DigiKey API with specific part number."""

from electrical_schematics.config.settings import DigiKeyConfig
from electrical_schematics.api.digikey_client import DigiKeyClient, DigiKeyAPIError


def test_specific_part():
    """Test DigiKey API with part number 3RT2017-1UB42-1AA0."""
    print("=" * 70)
    print("TESTING DIGIKEY API WITH PART: 3RT2017-1UB42-1AA0")
    print("=" * 70)

    # DigiKey credentials from test file
    client_id = "BQn3GHgisxIyPawJpCj1VqgPa6KAeSYQZlBUuVo7v2Ht3muY"
    client_secret = "ZZVGwXGmujahDn3aJWFGh2QEWDUGjCsGAMV3GzcpqBy101nXAbdQSPkFQrHHCKGA"

    config = DigiKeyConfig(
        client_id=client_id,
        client_secret=client_secret
    )

    client = DigiKeyClient(config)

    # Step 1: Authenticate
    print("\n1. Authenticating with DigiKey...")
    try:
        client.authenticate()
        print(f"   ✓ Authentication successful!")
        print(f"   Token: {config.access_token[:30]}...")
    except DigiKeyAPIError as e:
        print(f"   ✗ Authentication failed: {e}")
        return

    # Step 2: Search for the specific part
    part_number = "3RT2017-1UB42-1AA0"
    print(f"\n2. Searching for part: {part_number}")

    try:
        response = client.search_products(part_number, limit=10)
        print(f"   ✓ Search completed!")
        print(f"   Total results: {response.products_count}")

        if response.products:
            print(f"\n   Found {len(response.products)} products:")
            for i, product in enumerate(response.products, 1):
                print(f"\n   --- Product {i} ---")
                print(f"   DigiKey PN: {product.part_number}")
                print(f"   Mfr PN: {product.manufacturer_part_number}")
                print(f"   Manufacturer: {product.manufacturer}")
                print(f"   Description: {product.description}")
                print(f"   In Stock: {product.quantity_available}")
                if product.unit_price:
                    print(f"   Unit Price: ${product.unit_price}")
                if product.category:
                    print(f"   Category: {product.category}")
        else:
            print("   No products found in search results")

    except DigiKeyAPIError as e:
        print(f"   ✗ Search failed: {e}")
        return

    # Step 3: Get detailed product info
    print(f"\n3. Getting product details...")

    try:
        details = client.get_product_details(part_number)

        if details:
            print(f"   ✓ Product details retrieved!")
            print(f"\n   === PRODUCT DETAILS ===")
            print(f"   DigiKey Part Number: {details.part_number}")
            print(f"   Manufacturer: {details.manufacturer}")
            print(f"   Manufacturer PN: {details.manufacturer_part_number}")
            print(f"   Description: {details.description}")
            print(f"   Detailed Description: {details.detailed_description}")
            print(f"   Category: {details.category}")
            print(f"   Family: {details.family}")
            print(f"   Packaging: {details.packaging}")
            print(f"   Quantity Available: {details.quantity_available}")
            print(f"   Min Order Qty: {details.minimum_order_quantity}")
            print(f"   Product URL: {details.product_url}")
            print(f"   Datasheet: {details.primary_datasheet}")
            print(f"   Photo: {details.primary_photo}")

            if details.standard_pricing:
                print(f"\n   Pricing:")
                for price in details.standard_pricing[:3]:
                    print(f"      Qty {price['break_quantity']}: ${price['unit_price']}")

            if details.parameters:
                print(f"\n   Specifications ({len(details.parameters)} parameters):")
                for param_name, param_value in list(details.parameters.items())[:10]:
                    print(f"      {param_name}: {param_value}")
                if len(details.parameters) > 10:
                    print(f"      ... and {len(details.parameters) - 10} more")
        else:
            print("   Product details not found")

    except DigiKeyAPIError as e:
        print(f"   ✗ Details fetch failed: {e}")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    test_specific_part()
