"""FastAPI server for DigiKey API proxy and component library services."""

import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# Create FastAPI application
app = FastAPI(
    title="Electrical Schematics API",
    description="API proxy for DigiKey and component library services",
    version="1.0.0"
)

# Add CORS middleware for local GUI access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DigiKey API configuration
DIGIKEY_API_BASE = "https://api.digikey.com"
DIGIKEY_CLIENT_ID = os.environ.get("DIGIKEY_CLIENT_ID", "BQn3GHgisxIyPawJpCj1VqgPa6KAeSYQZlBUuVo7v2Ht3muY")
DIGIKEY_CLIENT_SECRET = os.environ.get("DIGIKEY_CLIENT_SECRET", "ZZVGwXGmujahDn3aJWFGh2QEWDUGjCsGAMV3GzcpqBy101nXAbdQSPkFQrHHCKGA")

# Token storage (in production, use proper token management)
_access_token: Optional[str] = None


# Pydantic models for request/response
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class ProductSearchRequest(BaseModel):
    keywords: str
    limit: int = 10


class ProductParameter(BaseModel):
    parameter: str
    value: str


class ProductResult(BaseModel):
    part_number: str
    manufacturer: str
    manufacturer_part_number: str
    description: str
    quantity_available: int
    unit_price: Optional[float] = None
    product_url: Optional[str] = None
    datasheet_url: Optional[str] = None
    category: Optional[str] = None
    family: Optional[str] = None
    parameters: List[ProductParameter] = []


class ProductSearchResponse(BaseModel):
    products: List[ProductResult]
    total_count: int


class ProductDetailsResponse(BaseModel):
    part_number: str
    manufacturer: str
    manufacturer_part_number: str
    description: str
    detailed_description: Optional[str] = None
    quantity_available: int
    minimum_order_quantity: int = 1
    unit_price: Optional[float] = None
    product_url: Optional[str] = None
    primary_datasheet: Optional[str] = None
    primary_photo: Optional[str] = None
    category: Optional[str] = None
    family: Optional[str] = None
    parameters: dict = {}
    pricing: List[dict] = []


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "electrical-schematics-api"}


# DigiKey Authentication
@app.post("/digikey/auth", response_model=TokenResponse)
async def digikey_authenticate():
    """Authenticate with DigiKey OAuth2 and get access token."""
    global _access_token

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{DIGIKEY_API_BASE}/v1/oauth2/token",
                data={
                    "client_id": DIGIKEY_CLIENT_ID,
                    "client_secret": DIGIKEY_CLIENT_SECRET,
                    "grant_type": "client_credentials"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0
            )
            response.raise_for_status()
            token_data = response.json()

            _access_token = token_data.get("access_token")

            return TokenResponse(
                access_token=_access_token,
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in", 3600)
            )

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"DigiKey authentication failed: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to connect to DigiKey API: {str(e)}"
            )


@app.post("/digikey/auth/token")
async def set_digikey_token(token: str = Query(..., description="Bearer token from DigiKey")):
    """Manually set DigiKey access token (for tokens obtained externally)."""
    global _access_token
    _access_token = token
    return {"status": "success", "message": "Token set successfully"}


# DigiKey Product Search
@app.post("/digikey/search", response_model=ProductSearchResponse)
async def digikey_search(request: ProductSearchRequest):
    """Search DigiKey for products by keyword."""
    if not _access_token:
        raise HTTPException(status_code=401, detail="Not authenticated. Call /digikey/auth first or set token.")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{DIGIKEY_API_BASE}/products/v4/search/keyword",
                json={
                    "Keywords": request.keywords,
                    "RecordCount": request.limit,
                    "RecordStartPosition": 0
                },
                headers={
                    "Authorization": f"Bearer {_access_token}",
                    "X-DIGIKEY-Client-Id": DIGIKEY_CLIENT_ID,
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            products = []
            for prod in data.get("Products", []):
                parameters = [
                    ProductParameter(
                        parameter=p.get("Parameter", ""),
                        value=p.get("Value", "")
                    )
                    for p in prod.get("Parameters", [])
                ]

                products.append(ProductResult(
                    part_number=prod.get("DigiKeyPartNumber", ""),
                    manufacturer=prod.get("Manufacturer", {}).get("Name", ""),
                    manufacturer_part_number=prod.get("ManufacturerPartNumber", ""),
                    description=prod.get("ProductDescription", ""),
                    quantity_available=prod.get("QuantityAvailable", 0),
                    unit_price=prod.get("UnitPrice"),
                    product_url=prod.get("ProductUrl"),
                    datasheet_url=prod.get("DatasheetUrl"),
                    category=prod.get("Category", {}).get("Name"),
                    family=prod.get("Family", {}).get("Name"),
                    parameters=parameters
                ))

            return ProductSearchResponse(
                products=products,
                total_count=data.get("ProductsCount", 0)
            )

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"DigiKey search failed: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to connect to DigiKey API: {str(e)}"
            )


# DigiKey Product Details
@app.get("/digikey/product/{part_number}", response_model=ProductDetailsResponse)
async def digikey_product_details(part_number: str):
    """Get detailed product information from DigiKey."""
    if not _access_token:
        raise HTTPException(status_code=401, detail="Not authenticated. Call /digikey/auth first or set token.")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{DIGIKEY_API_BASE}/products/v4/search/{part_number}/productdetails",
                headers={
                    "Authorization": f"Bearer {_access_token}",
                    "X-DIGIKEY-Client-Id": DIGIKEY_CLIENT_ID,
                    "X-DIGIKEY-Locale-Language": "en",
                    "X-DIGIKEY-Locale-Currency": "usd",
                    "X-DIGIKEY-Locale-Site": "us"
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            product = data.get("Product", {})

            # Extract parameters as dict
            parameters = {}
            for param in product.get("Parameters", []):
                param_name = param.get("Parameter", "")
                param_value = param.get("Value", "")
                if param_name and param_value:
                    parameters[param_name] = param_value

            # Extract pricing
            pricing = []
            for price in product.get("StandardPricing", []):
                pricing.append({
                    "break_quantity": price.get("BreakQuantity", 0),
                    "unit_price": price.get("UnitPrice", 0.0)
                })

            taxonomy = product.get("LimitedTaxonomy", {})

            return ProductDetailsResponse(
                part_number=product.get("DigiKeyPartNumber", ""),
                manufacturer=product.get("Manufacturer", {}).get("Name", ""),
                manufacturer_part_number=product.get("ManufacturerPartNumber", ""),
                description=product.get("ProductDescription", ""),
                detailed_description=product.get("DetailedDescription"),
                quantity_available=product.get("QuantityAvailable", 0),
                minimum_order_quantity=product.get("MinimumOrderQuantity", 1),
                unit_price=product.get("UnitPrice"),
                product_url=product.get("ProductUrl"),
                primary_datasheet=product.get("PrimaryDatasheet"),
                primary_photo=product.get("PrimaryPhoto"),
                category=taxonomy.get("CategoryName"),
                family=taxonomy.get("FamilyName"),
                parameters=parameters,
                pricing=pricing
            )

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"DigiKey product details failed: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to connect to DigiKey API: {str(e)}"
            )


# Run server function
def run_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the FastAPI server with uvicorn."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
