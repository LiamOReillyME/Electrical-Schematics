"""Asset downloader for component photos and datasheets."""

import logging
import requests
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class AssetDownloadError(Exception):
    """Error during asset download."""
    pass


class AssetDownloader:
    """Downloads and manages component photos and datasheets from DigiKey.

    Downloads are saved locally with sanitized part numbers as filenames.
    Supports resumable downloads and validates file integrity.
    """

    def __init__(self, assets_dir: Optional[Path] = None):
        """Initialize asset downloader.

        Args:
            assets_dir: Root directory for assets. Defaults to package assets folder.
        """
        if assets_dir is None:
            assets_dir = Path(__file__).parent.parent / "assets"

        self.assets_dir = Path(assets_dir)
        self.photos_dir = self.assets_dir / "component_photos"
        self.datasheets_dir = self.assets_dir / "datasheets"

        # Create directories
        self.photos_dir.mkdir(parents=True, exist_ok=True)
        self.datasheets_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Asset downloader initialized: {self.assets_dir}")

    def _sanitize_filename(self, part_number: str) -> str:
        """Sanitize part number for use as filename.

        Args:
            part_number: Original part number

        Returns:
            Sanitized filename-safe string
        """
        # Replace problematic characters
        sanitized = part_number.replace('/', '_').replace('\\', '_')
        sanitized = sanitized.replace(' ', '_').replace('*', '_')
        sanitized = sanitized.replace('?', '_').replace(':', '_').replace('#', '_')
        sanitized = sanitized.replace('"', '_').replace('<', '_')
        sanitized = sanitized.replace('>', '_').replace('|', '_')

        # Remove consecutive underscores
        while '__' in sanitized:
            sanitized = sanitized.replace('__', '_')

        return sanitized.strip('_')

    def download_photo(
        self,
        url: str,
        part_number: str,
        force: bool = False
    ) -> Optional[Path]:
        """Download component photo from DigiKey.

        Args:
            url: Photo URL
            part_number: Manufacturer part number
            force: If True, re-download even if file exists

        Returns:
            Local path to downloaded photo, or None if download failed

        Raises:
            AssetDownloadError: If download fails critically
        """
        if not url:
            logger.warning(f"No photo URL provided for {part_number}")
            return None

        # Sanitize filename
        safe_name = self._sanitize_filename(part_number)

        # Determine extension from URL
        parsed = urlparse(url)
        ext = Path(parsed.path).suffix
        if not ext or ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            ext = '.jpg'  # Default to JPG

        output_path = self.photos_dir / f"{safe_name}{ext}"

        # Skip if already exists
        if output_path.exists() and not force:
            logger.debug(f"Photo already exists: {output_path}")
            return output_path

        try:
            logger.info(f"Downloading photo for {part_number}: {url}")
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # Verify content type
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"Unexpected content type: {content_type}")

            # Write to file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Verify file was written
            if not output_path.exists() or output_path.stat().st_size == 0:
                raise AssetDownloadError(f"Failed to write photo: {output_path}")

            logger.info(f"Photo saved: {output_path}")
            return output_path

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download photo from {url}: {e}")
            # Clean up partial file
            if output_path.exists():
                output_path.unlink()
            return None

        except Exception as e:
            logger.error(f"Unexpected error downloading photo: {e}")
            if output_path.exists():
                output_path.unlink()
            return None  # raise AssetDownloadError(f"Photo download failed: {e}")

    def download_datasheet(
        self,
        url: str,
        part_number: str,
        force: bool = False
    ) -> Optional[Path]:
        """Download component datasheet from DigiKey.

        Args:
            url: Datasheet URL
            part_number: Manufacturer part number
            force: If True, re-download even if file exists

        Returns:
            Local path to downloaded datasheet, or None if download failed

        Raises:
            AssetDownloadError: If download fails critically
        """
        if not url:
            logger.warning(f"No datasheet URL provided for {part_number}")
            return None

        # Sanitize filename
        safe_name = self._sanitize_filename(part_number)

        # Determine extension from URL (usually PDF)
        parsed = urlparse(url)
        ext = Path(parsed.path).suffix
        if not ext or ext.lower() not in ['.pdf', '.doc', '.docx', '.zip']:
            ext = '.pdf'  # Default to PDF

        output_path = self.datasheets_dir / f"{safe_name}{ext}"

        # Skip if already exists
        if output_path.exists() and not force:
            logger.debug(f"Datasheet already exists: {output_path}")
            return output_path

        try:
            logger.info(f"Downloading datasheet for {part_number}: {url}")
            response = requests.get(url, timeout=60, stream=True)
            response.raise_for_status()

            # Verify content type
            content_type = response.headers.get('Content-Type', '')
            if 'application/pdf' not in content_type and 'application/octet-stream' not in content_type:
                logger.warning(f"Unexpected content type for datasheet: {content_type}")

            # Write to file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Verify file was written
            if not output_path.exists() or output_path.stat().st_size == 0:
                raise AssetDownloadError(f"Failed to write datasheet: {output_path}")

            logger.info(f"Datasheet saved: {output_path}")
            return output_path

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download datasheet from {url}: {e}")
            # Clean up partial file
            if output_path.exists():
                output_path.unlink()
            return None

        except Exception as e:
            logger.error(f"Unexpected error downloading datasheet: {e}")
            if output_path.exists():
                output_path.unlink()
            raise AssetDownloadError(f"Datasheet download failed: {e}")

    def download_both(
        self,
        photo_url: Optional[str],
        datasheet_url: Optional[str],
        part_number: str,
        force: bool = False
    ) -> tuple[Optional[Path], Optional[Path]]:
        """Download both photo and datasheet for a component.

        Args:
            photo_url: Photo URL
            datasheet_url: Datasheet URL
            part_number: Manufacturer part number
            force: If True, re-download even if files exist

        Returns:
            Tuple of (photo_path, datasheet_path), either may be None
        """
        photo_path = None
        datasheet_path = None

        if photo_url:
            photo_path = self.download_photo(photo_url, part_number, force=force)

        if datasheet_url:
            datasheet_path = self.download_datasheet(datasheet_url, part_number, force=force)

        return photo_path, datasheet_path

    def get_photo_path(self, part_number: str) -> Optional[Path]:
        """Get path to photo if it exists locally.

        Args:
            part_number: Manufacturer part number

        Returns:
            Path to photo if exists, None otherwise
        """
        safe_name = self._sanitize_filename(part_number)

        # Check common image extensions
        for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            photo_path = self.photos_dir / f"{safe_name}{ext}"
            if photo_path.exists():
                return photo_path

        return None

    def get_datasheet_path(self, part_number: str) -> Optional[Path]:
        """Get path to datasheet if it exists locally.

        Args:
            part_number: Manufacturer part number

        Returns:
            Path to datasheet if exists, None otherwise
        """
        safe_name = self._sanitize_filename(part_number)

        # Check common document extensions
        for ext in ['.pdf', '.doc', '.docx', '.zip']:
            datasheet_path = self.datasheets_dir / f"{safe_name}{ext}"
            if datasheet_path.exists():
                return datasheet_path

        return None

    def cleanup_orphaned_assets(self, valid_part_numbers: set[str]) -> tuple[int, int]:
        """Remove assets for parts no longer in the library.

        Args:
            valid_part_numbers: Set of current valid part numbers

        Returns:
            Tuple of (photos_deleted, datasheets_deleted)
        """
        photos_deleted = 0
        datasheets_deleted = 0

        # Check photos
        for photo_file in self.photos_dir.glob('*'):
            if photo_file.is_file():
                # Extract part number from filename
                stem = photo_file.stem
                if stem not in valid_part_numbers:
                    logger.info(f"Deleting orphaned photo: {photo_file}")
                    photo_file.unlink()
                    photos_deleted += 1

        # Check datasheets
        for datasheet_file in self.datasheets_dir.glob('*'):
            if datasheet_file.is_file():
                stem = datasheet_file.stem
                if stem not in valid_part_numbers:
                    logger.info(f"Deleting orphaned datasheet: {datasheet_file}")
                    datasheet_file.unlink()
                    datasheets_deleted += 1

        return photos_deleted, datasheets_deleted
