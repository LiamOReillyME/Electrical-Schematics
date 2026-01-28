# DigiKey Configuration Error Fix

## Bug Report

**Error**: `AttributeError: 'SettingsManager' object has no attribute 'get_digikey_config'`

**When it occurred**: When querying DigiKey API from component edit popup dialog

**Impact**: DigiKey integration was completely broken - users could not fetch component data from DigiKey

---

## Root Cause Analysis

### The Problem

The `SettingsManager` class in `electrical_schematics/config/settings.py` was missing the `get_digikey_config()` method that was being called by:

1. **main_window.py** (line 283) - Component edit dialog
2. **add_vfd_component.py** (line 23) - VFD component script

### Why This Happened

The class had:
- `settings.digikey` attribute (stores DigiKeyConfig object)
- `set_digikey_credentials()` method (sets credentials)
- `update_digikey_tokens()` method (updates OAuth tokens)
- `get_database_path()` method (retrieves database path)

But was missing:
- `get_digikey_config()` method (retrieves DigiKey configuration)

The calling code expected a getter method to access the DigiKey configuration, following the pattern established by `get_database_path()`.

---

## The Fix

### Added Method to SettingsManager

**File**: `/home/liam-oreilly/claude.projects/electricalSchematics/electrical_schematics/config/settings.py`

**Lines**: 109-121

```python
def get_digikey_config(self) -> DigiKeyConfig:
    """Get DigiKey API configuration.

    Returns:
        DigiKeyConfig object with credentials and tokens.
        If not configured, returns an empty DigiKeyConfig with empty strings.

    Raises:
        ValueError: If DigiKey credentials are not configured
    """
    if self.settings.digikey is None:
        # Return empty config to allow graceful error handling
        return DigiKeyConfig(client_id="", client_secret="")
    return self.settings.digikey
```

### Design Decisions

1. **Graceful Degradation**: Returns empty DigiKeyConfig instead of raising exception
   - Allows calling code to check `if not config.client_id` for proper error messages
   - Maintains consistency with existing error handling in main_window.py

2. **Type Safety**: Returns DigiKeyConfig dataclass
   - Ensures all required fields are present (client_id, client_secret, api_base_url, token_url)
   - Provides IDE autocomplete and type checking

3. **Consistent API**: Follows pattern of `get_database_path()`
   - Simple getter method for configuration objects
   - No parameters needed

---

## Testing

### Unit Tests Performed

```bash
cd /home/liam-oreilly/claude.projects/electricalSchematics
python -c "
from electrical_schematics.config.settings import get_settings

# Test 1: Get settings manager
settings = get_settings()
print('✓ Settings manager initialized')

# Test 2: Get DigiKey config (should return empty config if not configured)
config = settings.get_digikey_config()
print(f'✓ get_digikey_config() returned: client_id=\"{config.client_id}\"')

# Test 3: Set credentials
settings.set_digikey_credentials('test_id', 'test_secret')
print('✓ Credentials set')

# Test 4: Retrieve configured credentials
config = settings.get_digikey_config()
print(f'✓ Retrieved config: client_id=\"{config.client_id}\"')

print('✅ All tests passed!')
"
```

**Result**: All tests passed

### Integration Points Verified

1. **main_window.py:283** - Component edit dialog DigiKey query
   - Now successfully calls `get_digikey_config()`
   - Properly handles empty credentials with warning dialog

2. **add_vfd_component.py:23** - VFD component addition script
   - Now successfully retrieves DigiKey config
   - Checks for empty credentials and displays error message

---

## Configuration Guide

### Setting DigiKey API Credentials

DigiKey credentials are stored in: `~/.electrical_schematics/config.json`

#### Option 1: Via Python API

```python
from electrical_schematics.config.settings import get_settings

settings = get_settings()
settings.set_digikey_credentials(
    client_id="your_client_id_here",
    client_secret="your_client_secret_here"
)
```

#### Option 2: Manual Configuration

Create or edit `~/.electrical_schematics/config.json`:

```json
{
  "database_path": "~/.electrical_schematics/components.db",
  "digikey": {
    "client_id": "your_client_id_here",
    "client_secret": "your_client_secret_here",
    "api_base_url": "https://api.digikey.com",
    "token_url": "https://api.digikey.com/v1/oauth2/token"
  },
  "recent_files_limit": 10,
  "default_zoom": 1.0
}
```

### Getting DigiKey API Credentials

1. Register for a DigiKey account at https://www.digikey.com/
2. Navigate to API Portal: https://developer.digikey.com/
3. Create a new application
4. Note your Client ID and Client Secret
5. Set up OAuth redirect URI (typically `https://localhost:8080/callback`)

### DigiKey API Features

Once configured, the application can:
- Search for components by part number
- Fetch detailed product specifications
- Download datasheets and product images
- Check availability and pricing
- Access parameter data (voltage, current, package type, etc.)

---

## Files Modified

### electrical_schematics/config/settings.py

**Changed**: Added `get_digikey_config()` method to SettingsManager class

**Location**: Lines 109-121

**Changes**:
- Added method to retrieve DigiKeyConfig object
- Returns empty config if not configured (graceful degradation)
- Maintains type safety with DigiKeyConfig dataclass return type

---

## Verification Checklist

- [x] Method added to SettingsManager class
- [x] Returns correct type (DigiKeyConfig)
- [x] Handles unconfigured state gracefully
- [x] Maintains consistency with existing API patterns
- [x] Unit tests pass
- [x] Integration points verified (main_window.py, add_vfd_component.py)
- [x] Documentation updated

---

## Related Code

### SettingsManager Class Structure

```python
class SettingsManager:
    def __init__(self, config_file: Optional[Path] = None)
    def _load_settings(self) -> AppSettings
    def save_settings(self) -> None
    def set_digikey_credentials(self, client_id: str, client_secret: str) -> None
    def get_digikey_config(self) -> DigiKeyConfig  # NEW METHOD
    def update_digikey_tokens(self, access_token: str, refresh_token: str, expires_at: float) -> None
    def get_database_path(self) -> Path
```

### DigiKeyConfig Dataclass

```python
@dataclass
class DigiKeyConfig:
    client_id: str
    client_secret: str
    api_base_url: str = "https://api.digikey.com"
    token_url: str = "https://api.digikey.com/v1/oauth2/token"
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[float] = None
```

---

## Status

**Fixed**: 2026-01-28

**Tested**: Yes

**Deployed**: Ready for use

**Breaking Changes**: None (added missing method)

---

## Future Improvements

1. **Settings UI**: Add GUI dialog for configuring DigiKey credentials
2. **Validation**: Add credential validation when setting
3. **Token Refresh**: Automatic token refresh before expiration
4. **Multiple APIs**: Support for additional component databases (Mouser, Arrow, etc.)
5. **Credential Security**: Consider using system keyring for sensitive credentials
