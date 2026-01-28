"""Data models for DigiKey API responses."""

from dataclasses import dataclass
from typing import List, Optional, Dict


@dataclass
class DigiKeyParameter:
    """Product parameter/specification."""
    parameter: str
    value: str


@dataclass
class DigiKeyProduct:
    """DigiKey product search result."""
    part_number: str
    manufacturer: str
    manufacturer_part_number: str
    description: str
    detailed_description: Optional[str]
    quantity_available: int
    unit_price: Optional[float]
    primary_photo: Optional[str]
    primary_datasheet: Optional[str]
    product_url: Optional[str]
    parameters: List[DigiKeyParameter]
    category: Optional[str]
    family: Optional[str]


@dataclass
class DigiKeySearchResponse:
    """DigiKey product search response."""
    products: List[DigiKeyProduct]
    products_count: int
    exact_manufacturer_products_count: int


@dataclass
class DigiKeyProductDetails:
    """Detailed DigiKey product information."""
    part_number: str
    manufacturer: str
    manufacturer_part_number: str
    description: str
    detailed_description: str
    primary_photo: Optional[str]
    primary_datasheet: Optional[str]
    datasheets: List[str]
    product_url: str
    parameters: Dict[str, str]
    category: str
    family: str
    limited_taxonomy: Dict[str, str]
    packaging: Optional[str]
    quantity_available: int
    minimum_order_quantity: int
    standard_pricing: List[Dict[str, float]]
