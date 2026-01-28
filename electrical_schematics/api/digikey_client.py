"""DigiKey API client with OAuth2 authentication."""

import time
import logging
import requests
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient

from electrical_schematics.api.digikey_models import (
    DigiKeyProduct,
    DigiKeyProductDetails,
    DigiKeySearchResponse,
    DigiKeyParameter
)
from electrical_schematics.config.settings import DigiKeyConfig

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, calls_per_second: int = 10):
        """Initialize rate limiter.

        Args:
            calls_per_second: Maximum API calls per second
        """
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0

    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limit."""
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()


class DigiKeyAPIError(Exception):
    """DigiKey API error."""
    pass


class DigiKeyClient:
    """Client for DigiKey Product Search API v4."""

    def __init__(self, config: DigiKeyConfig):
        """Initialize DigiKey API client.

        Args:
            config: DigiKey API configuration with credentials
        """
        self.config = config
        self.rate_limiter = RateLimiter(calls_per_second=10)
        self._oauth_session: Optional[OAuth2Session] = None
        self._token_expires_at: Optional[float] = None

    def authenticate(self) -> bool:
        """Authenticate with DigiKey OAuth2.

        Returns:
            True if authentication successful

        Raises:
            DigiKeyAPIError: If authentication fails
        """
        try:
            # Use client credentials flow (backend application)
            client = BackendApplicationClient(client_id=self.config.client_id)
            oauth = OAuth2Session(client=client)

            # Fetch token
            token = oauth.fetch_token(
                token_url=self.config.token_url,
                client_id=self.config.client_id,
                client_secret=self.config.client_secret
            )

            # Store token and expiration
            self.config.access_token = token['access_token']
            self._token_expires_at = time.time() + token.get('expires_in', 3600)
            self._oauth_session = oauth

            return True

        except Exception as e:
            raise DigiKeyAPIError(f"Authentication failed: {e}")

    def _ensure_authenticated(self) -> None:
        """Ensure client is authenticated, refresh if needed."""
        if not self.config.access_token or not self._oauth_session:
            self.authenticate()
        elif self._token_expires_at and time.time() >= self._token_expires_at - 300:
            # Refresh if token expires in less than 5 minutes
            self.authenticate()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON request body

        Returns:
            JSON response as dictionary

        Raises:
            DigiKeyAPIError: If request fails
        """
        self._ensure_authenticated()
        self.rate_limiter.wait_if_needed()

        url = urljoin(self.config.api_base_url, endpoint)
        headers = {
            'Authorization': f'Bearer {self.config.access_token}',
            'X-DIGIKEY-Client-Id': self.config.client_id
        }

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            error_msg = f"API request failed: {e}"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg += f" - {error_data}"
                except:
                    error_msg += f" - {e.response.text}"
            raise DigiKeyAPIError(error_msg)

        except Exception as e:
            raise DigiKeyAPIError(f"Request error: {e}")

    def get_product_details(self, part_number: str) -> Optional[DigiKeyProductDetails]:
        """Get detailed product information by part number.

        Args:
            part_number: DigiKey or manufacturer part number

        Returns:
            Product details if found, None otherwise

        Raises:
            DigiKeyAPIError: If API request fails
        """
        endpoint = f"/products/v4/search/{part_number}/productdetails"

        try:
            data = self._make_request('GET', endpoint)

            # Parse response
            product = data.get('Product', {})

            if not product:
                return None

            # Extract parameters as dictionary
            parameters = {}
            for param in product.get('Parameters', []):
                param_name = param.get('Parameter', '')
                param_value = param.get('Value', '')
                if param_name and param_value:
                    parameters[param_name] = param_value

            # Extract pricing
            standard_pricing = []
            for price in product.get('StandardPricing', []):
                standard_pricing.append({
                    'break_quantity': price.get('BreakQuantity', 0),
                    'unit_price': price.get('UnitPrice', 0.0)
                })

            # Get taxonomy info
            taxonomy = product.get('LimitedTaxonomy', {})

            return DigiKeyProductDetails(
                part_number=product.get('DigiKeyPartNumber', ''),
                manufacturer=product.get('Manufacturer', {}).get('Name', ''),
                manufacturer_part_number=product.get('ManufacturerPartNumber', ''),
                description=product.get('ProductDescription', ''),
                detailed_description=product.get('DetailedDescription', ''),
                primary_photo=product.get('PrimaryPhoto', ''),
                primary_datasheet=product.get('PrimaryDatasheet', ''),
                datasheets=[ds.get('Url', '') for ds in product.get('DatasheetUrl', [])],
                product_url=product.get('ProductUrl', ''),
                parameters=parameters,
                category=taxonomy.get('CategoryName', ''),
                family=taxonomy.get('FamilyName', ''),
                limited_taxonomy=taxonomy,
                packaging=product.get('Packaging', {}).get('Value', ''),
                quantity_available=product.get('QuantityAvailable', 0),
                minimum_order_quantity=product.get('MinimumOrderQuantity', 1),
                standard_pricing=standard_pricing
            )

        except DigiKeyAPIError:
            raise
        except Exception as e:
            raise DigiKeyAPIError(f"Error parsing product details: {e}")

    def get_product_details_with_retry(self, part_number: str) -> Optional[DigiKeyProductDetails]:
        """Get product details with retry logic for hyphenated part numbers.

        First tries the original part number. If that fails, retries without hyphens.

        Args:
            part_number: Manufacturer part number (may contain hyphens)

        Returns:
            Product details if found, None otherwise
        """
        # Try original part number first
        logger.info(f"Looking up part: {part_number}")
        try:
            result = self.get_product_details(part_number)
            if result:
                logger.info(f"Found part: {part_number}")
                return result
        except DigiKeyAPIError as e:
            logger.debug(f"Initial lookup failed for {part_number}: {e}")

        # Retry without hyphens if original had hyphens
        if '-' in part_number:
            part_no_hyphens = part_number.replace('-', '')
            logger.info(f"Retrying without hyphens: {part_no_hyphens}")
            try:
                result = self.get_product_details(part_no_hyphens)
                if result:
                    logger.info(f"Found part without hyphens: {part_no_hyphens}")
                    return result
            except DigiKeyAPIError as e:
                logger.debug(f"Retry lookup failed for {part_no_hyphens}: {e}")

        logger.warning(f"Part not found: {part_number}")
        return None

    def validate_complete_data(self, details: Optional[DigiKeyProductDetails]) -> bool:
        """Validate that product details contain all required fields.

        Required fields:
        - Manufacturer part number
        - DigiKey part number
        - Description
        - Category
        - Photo URL
        - Datasheet URL
        - Unit price

        Args:
            details: DigiKey product details to validate

        Returns:
            True if all required fields are present and non-empty
        """
        if not details:
            return False

        # Check required fields
        required_checks = [
            details.manufacturer_part_number,
            details.part_number,
            details.description,
            details.category,
            details.primary_photo,
            details.primary_datasheet,
        ]

        # All required fields must be non-empty strings
        if not all(field for field in required_checks):
            logger.warning(f"Missing required fields for {details.manufacturer_part_number}")
            return False

        # Must have pricing
        if not details.standard_pricing or len(details.standard_pricing) == 0:
            logger.warning(f"No pricing data for {details.manufacturer_part_number}")
            return False

        return True

    def search_products(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 50
    ) -> DigiKeySearchResponse:
        """Search for products by keyword.

        Args:
            query: Search query (part number, manufacturer, keywords)
            category: Optional category filter
            limit: Maximum number of results (default 50)

        Returns:
            Search response with matching products

        Raises:
            DigiKeyAPIError: If search fails
        """
        endpoint = "/products/v4/search/keyword"

        # Build search request
        request_data = {
            'Keywords': query,
            'RecordCount': limit,
            'RecordStartPosition': 0,
            'Sort': {
                'Option': 'SortByQuantityAvailable',
                'Direction': 'Descending'
            }
        }

        if category:
            request_data['Filters'] = {
                'CategoryIds': [category]
            }

        try:
            data = self._make_request('POST', endpoint, json_data=request_data)

            # Parse response
            products = []
            for prod_data in data.get('Products', []):
                # Extract parameters
                parameters = []
                for param in prod_data.get('Parameters', []):
                    parameters.append(DigiKeyParameter(
                        parameter=param.get('Parameter', ''),
                        value=param.get('Value', '')
                    ))

                # Get primary photo
                primary_photo = None
                media_links = prod_data.get('MediaLinks', [])
                if media_links:
                    primary_photo = media_links[0].get('Url')

                # Get pricing
                unit_price = None
                pricing = prod_data.get('UnitPrice')
                if pricing:
                    unit_price = pricing

                product = DigiKeyProduct(
                    part_number=prod_data.get('DigiKeyPartNumber', ''),
                    manufacturer=prod_data.get('Manufacturer', {}).get('Name', ''),
                    manufacturer_part_number=prod_data.get('ManufacturerPartNumber', ''),
                    description=prod_data.get('ProductDescription', ''),
                    detailed_description=prod_data.get('DetailedDescription'),
                    quantity_available=prod_data.get('QuantityAvailable', 0),
                    unit_price=unit_price,
                    primary_photo=primary_photo,
                    primary_datasheet=prod_data.get('DatasheetUrl'),
                    product_url=prod_data.get('ProductUrl'),
                    parameters=parameters,
                    category=prod_data.get('Category', {}).get('Name'),
                    family=prod_data.get('Family', {}).get('Name')
                )
                products.append(product)

            return DigiKeySearchResponse(
                products=products,
                products_count=data.get('ProductsCount', 0),
                exact_manufacturer_products_count=data.get('ExactManufacturerProductsCount', 0)
            )

        except DigiKeyAPIError:
            raise
        except Exception as e:
            raise DigiKeyAPIError(f"Error parsing search results: {e}")

    def download_product_image(self, image_url: str) -> Optional[bytes]:
        """Download product image from URL.

        Args:
            image_url: URL to product image

        Returns:
            Image data as bytes, or None if download fails
        """
        try:
            self.rate_limiter.wait_if_needed()
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Failed to download image from {image_url}: {e}")
            return None

    def get_datasheet_url(self, part_number: str) -> Optional[str]:
        """Get datasheet URL for a product.

        Args:
            part_number: DigiKey or manufacturer part number

        Returns:
            Datasheet URL if available
        """
        try:
            details = self.get_product_details(part_number)
            if details:
                return details.primary_datasheet
        except Exception as e:
            logger.error(f"Failed to get datasheet URL: {e}")
        return None
