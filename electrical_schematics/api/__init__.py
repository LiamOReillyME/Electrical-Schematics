"""API module for external service integrations."""

from electrical_schematics.api.digikey_client import (
    DigiKeyClient,
    DigiKeyAPIError,
    RateLimiter
)
from electrical_schematics.api.digikey_models import (
    DigiKeyProduct,
    DigiKeyProductDetails,
    DigiKeySearchResponse,
    DigiKeyParameter
)
from electrical_schematics.api.digikey_proxy_client import (
    DigiKeyProxyClient,
    DigiKeyProxyError,
    get_digikey_client
)
from electrical_schematics.api.server_manager import (
    ServerManager,
    get_server_manager,
    ensure_server_running
)

__all__ = [
    # Direct client (for reference/fallback)
    'DigiKeyClient',
    'DigiKeyAPIError',
    'RateLimiter',
    # Models
    'DigiKeyProduct',
    'DigiKeyProductDetails',
    'DigiKeySearchResponse',
    'DigiKeyParameter',
    # Proxy client (recommended for GUI use)
    'DigiKeyProxyClient',
    'DigiKeyProxyError',
    'get_digikey_client',
    # Server management
    'ServerManager',
    'get_server_manager',
    'ensure_server_running',
]
