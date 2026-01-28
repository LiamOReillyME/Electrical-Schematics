"""DigiKey client that routes requests through local FastAPI proxy."""

import requests
from typing import Optional, List
from dataclasses import dataclass

from electrical_schematics.api.server_manager import ensure_server_running
from electrical_schematics.api.digikey_models import (
    DigiKeyProduct,
    DigiKeyProductDetails,
    DigiKeySearchResponse,
    DigiKeyParameter
)


class DigiKeyProxyError(Exception):
    """Error from DigiKey proxy."""
    pass


@dataclass
class DigiKeyProxyClient:
    """DigiKey client that uses local FastAPI proxy server."""

    _token: Optional[str] = None
    _base_url: Optional[str] = None

    def _ensure_server(self) -> str:
        """Ensure proxy server is running and return base URL."""
        if not self._base_url:
            self._base_url = ensure_server_running()
        return self._base_url

    def set_token(self, token: str) -> bool:
        """Set the DigiKey access token.

        Args:
            token: Bearer token from DigiKey

        Returns:
            True if token was set successfully
        """
        base_url = self._ensure_server()
        self._token = token

        try:
            response = requests.post(
                f"{base_url}/digikey/auth/token",
                params={"token": token},
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Failed to set token: {e}")
            return False

    def authenticate(self) -> bool:
        """Authenticate with DigiKey OAuth2.

        Returns:
            True if authentication successful
        """
        base_url = self._ensure_server()

        try:
            response = requests.post(
                f"{base_url}/digikey/auth",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            self._token = data.get("access_token")
            return True
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            try:
                error_detail = e.response.json().get("detail", "")
            except:
                error_detail = e.response.text
            raise DigiKeyProxyError(f"Authentication failed: {error_detail}")
        except Exception as e:
            raise DigiKeyProxyError(f"Authentication error: {e}")

    def search_products(self, query: str, limit: int = 10) -> DigiKeySearchResponse:
        """Search for products by keyword.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Search response with products
        """
        base_url = self._ensure_server()

        try:
            response = requests.post(
                f"{base_url}/digikey/search",
                json={"keywords": query, "limit": limit},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            products = []
            for prod in data.get("products", []):
                parameters = [
                    DigiKeyParameter(
                        parameter=p.get("parameter", ""),
                        value=p.get("value", "")
                    )
                    for p in prod.get("parameters", [])
                ]

                products.append(DigiKeyProduct(
                    part_number=prod.get("part_number", ""),
                    manufacturer=prod.get("manufacturer", ""),
                    manufacturer_part_number=prod.get("manufacturer_part_number", ""),
                    description=prod.get("description", ""),
                    detailed_description=prod.get("detailed_description"),
                    quantity_available=prod.get("quantity_available", 0),
                    unit_price=prod.get("unit_price"),
                    primary_photo=None,
                    primary_datasheet=prod.get("datasheet_url"),
                    product_url=prod.get("product_url"),
                    parameters=parameters,
                    category=prod.get("category"),
                    family=prod.get("family")
                ))

            return DigiKeySearchResponse(
                products=products,
                products_count=data.get("total_count", 0),
                exact_manufacturer_products_count=0
            )

        except requests.exceptions.HTTPError as e:
            error_detail = ""
            try:
                error_detail = e.response.json().get("detail", "")
            except:
                error_detail = e.response.text
            raise DigiKeyProxyError(f"Search failed: {error_detail}")
        except Exception as e:
            raise DigiKeyProxyError(f"Search error: {e}")

    def get_product_details(self, part_number: str) -> Optional[DigiKeyProductDetails]:
        """Get detailed product information.

        Args:
            part_number: DigiKey or manufacturer part number

        Returns:
            Product details if found
        """
        base_url = self._ensure_server()

        try:
            response = requests.get(
                f"{base_url}/digikey/product/{part_number}",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            return DigiKeyProductDetails(
                part_number=data.get("part_number", ""),
                manufacturer=data.get("manufacturer", ""),
                manufacturer_part_number=data.get("manufacturer_part_number", ""),
                description=data.get("description", ""),
                detailed_description=data.get("detailed_description", ""),
                primary_photo=data.get("primary_photo"),
                primary_datasheet=data.get("primary_datasheet"),
                datasheets=[data.get("primary_datasheet")] if data.get("primary_datasheet") else [],
                product_url=data.get("product_url", ""),
                parameters=data.get("parameters", {}),
                category=data.get("category", ""),
                family=data.get("family", ""),
                limited_taxonomy={},
                packaging=None,
                quantity_available=data.get("quantity_available", 0),
                minimum_order_quantity=data.get("minimum_order_quantity", 1),
                standard_pricing=data.get("pricing", [])
            )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            error_detail = ""
            try:
                error_detail = e.response.json().get("detail", "")
            except:
                error_detail = e.response.text
            raise DigiKeyProxyError(f"Product details failed: {error_detail}")
        except Exception as e:
            raise DigiKeyProxyError(f"Product details error: {e}")


# Global client instance
_proxy_client: Optional[DigiKeyProxyClient] = None


def get_digikey_client() -> DigiKeyProxyClient:
    """Get the global DigiKey proxy client."""
    global _proxy_client
    if _proxy_client is None:
        _proxy_client = DigiKeyProxyClient()
    return _proxy_client
