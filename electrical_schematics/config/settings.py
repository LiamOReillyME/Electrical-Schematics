"""Application settings and configuration."""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class DigiKeyConfig:
    """DigiKey API configuration."""
    client_id: str
    client_secret: str
    api_base_url: str = "https://api.digikey.com"
    token_url: str = "https://api.digikey.com/v1/oauth2/token"

    # Access token storage (updated after authentication)
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[float] = None


@dataclass
class AppSettings:
    """Application settings."""
    database_path: str = "~/.electrical_schematics/components.db"
    digikey: Optional[DigiKeyConfig] = None
    recent_files_limit: int = 10
    default_zoom: float = 1.0


class SettingsManager:
    """Manage application settings."""

    def __init__(self, config_file: Optional[Path] = None):
        """Initialize settings manager.

        Args:
            config_file: Path to config file (defaults to ~/.electrical_schematics/config.json)
        """
        if config_file is None:
            config_dir = Path.home() / ".electrical_schematics"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.json"

        self.config_file = config_file
        self.settings = self._load_settings()

    def _load_settings(self) -> AppSettings:
        """Load settings from file or create defaults."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)

                digikey_data = data.get('digikey')
                digikey_config = None
                if digikey_data:
                    digikey_config = DigiKeyConfig(**digikey_data)

                return AppSettings(
                    database_path=data.get('database_path', AppSettings.database_path),
                    digikey=digikey_config,
                    recent_files_limit=data.get('recent_files_limit', 10),
                    default_zoom=data.get('default_zoom', 1.0)
                )
            except Exception as e:
                print(f"Error loading settings: {e}, using defaults")

        # Return defaults if file doesn't exist or has errors
        return AppSettings()

    def save_settings(self) -> None:
        """Save settings to file."""
        data = {
            'database_path': self.settings.database_path,
            'recent_files_limit': self.settings.recent_files_limit,
            'default_zoom': self.settings.default_zoom
        }

        if self.settings.digikey:
            data['digikey'] = asdict(self.settings.digikey)

        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=2)

    def set_digikey_credentials(
        self,
        client_id: str,
        client_secret: str
    ) -> None:
        """Set DigiKey API credentials.

        Args:
            client_id: DigiKey OAuth client ID
            client_secret: DigiKey OAuth client secret
        """
        self.settings.digikey = DigiKeyConfig(
            client_id=client_id,
            client_secret=client_secret
        )
        self.save_settings()

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

    def update_digikey_tokens(
        self,
        access_token: str,
        refresh_token: str,
        expires_at: float
    ) -> None:
        """Update DigiKey access tokens.

        Args:
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expires_at: Token expiration timestamp
        """
        if self.settings.digikey:
            self.settings.digikey.access_token = access_token
            self.settings.digikey.refresh_token = refresh_token
            self.settings.digikey.token_expires_at = expires_at
            self.save_settings()

    def get_database_path(self) -> Path:
        """Get database path with home directory expansion.

        Returns:
            Absolute path to database file
        """
        return Path(self.settings.database_path).expanduser()


# Global settings instance
_settings_manager: Optional[SettingsManager] = None


def get_settings() -> SettingsManager:
    """Get global settings manager instance.

    Returns:
        Settings manager
    """
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


def initialize_settings_with_digikey(
    client_id: str,
    client_secret: str
) -> SettingsManager:
    """Initialize settings with DigiKey credentials.

    Args:
        client_id: DigiKey OAuth client ID
        client_secret: DigiKey OAuth client secret

    Returns:
        Configured settings manager
    """
    settings = get_settings()
    settings.set_digikey_credentials(client_id, client_secret)
    return settings
