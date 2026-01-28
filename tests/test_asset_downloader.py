"""Tests for asset downloader service."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

from electrical_schematics.services.asset_downloader import (
    AssetDownloader,
    AssetDownloadError
)


@pytest.fixture
def temp_assets_dir():
    """Create temporary assets directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def downloader(temp_assets_dir):
    """Create asset downloader with temp directory."""
    return AssetDownloader(temp_assets_dir)


def test_init_creates_directories(temp_assets_dir):
    """Test that initialization creates required directories."""
    downloader = AssetDownloader(temp_assets_dir)

    assert downloader.photos_dir.exists()
    assert downloader.datasheets_dir.exists()
    assert downloader.photos_dir == temp_assets_dir / "component_photos"
    assert downloader.datasheets_dir == temp_assets_dir / "datasheets"


def test_sanitize_filename():
    """Test filename sanitization."""
    downloader = AssetDownloader()

    # Test special characters
    assert downloader._sanitize_filename("3RT2026-1DB40-1AAO") == "3RT2026-1DB40-1AAO"
    assert downloader._sanitize_filename("LM7805/TO220") == "LM7805_TO220"
    assert downloader._sanitize_filename("Part #123") == "Part_123"
    assert downloader._sanitize_filename("C:\\temp\\file") == "C_temp_file"

    # Test consecutive underscores
    assert downloader._sanitize_filename("Part___123") == "Part_123"


@patch('electrical_schematics.services.asset_downloader.requests.get')
def test_download_photo_success(mock_get, downloader):
    """Test successful photo download."""
    # Mock response
    mock_response = Mock()
    mock_response.headers = {'Content-Type': 'image/jpeg'}
    mock_response.iter_content = lambda chunk_size: [b'fake image data']
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    # Download
    photo_path = downloader.download_photo(
        url="https://example.com/photo.jpg",
        part_number="TEST123"
    )

    # Verify
    assert photo_path is not None
    assert photo_path.exists()
    assert photo_path.name == "TEST123.jpg"
    assert photo_path.read_bytes() == b'fake image data'

    # Verify request
    mock_get.assert_called_once()
    assert mock_get.call_args[0][0] == "https://example.com/photo.jpg"


@patch('electrical_schematics.services.asset_downloader.requests.get')
def test_download_photo_already_exists(mock_get, downloader):
    """Test that existing photo is not re-downloaded."""
    # Create existing file
    photo_path = downloader.photos_dir / "TEST123.jpg"
    photo_path.write_bytes(b'existing data')

    # Download (should skip)
    result = downloader.download_photo(
        url="https://example.com/photo.jpg",
        part_number="TEST123",
        force=False
    )

    # Verify
    assert result == photo_path
    assert result.read_bytes() == b'existing data'
    mock_get.assert_not_called()


@patch('electrical_schematics.services.asset_downloader.requests.get')
def test_download_photo_force_redownload(mock_get, downloader):
    """Test that force=True re-downloads existing file."""
    # Create existing file
    photo_path = downloader.photos_dir / "TEST123.jpg"
    photo_path.write_bytes(b'old data')

    # Mock response
    mock_response = Mock()
    mock_response.headers = {'Content-Type': 'image/jpeg'}
    mock_response.iter_content = lambda chunk_size: [b'new data']
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    # Download with force
    result = downloader.download_photo(
        url="https://example.com/photo.jpg",
        part_number="TEST123",
        force=True
    )

    # Verify
    assert result is not None
    assert result.read_bytes() == b'new data'
    mock_get.assert_called_once()


@patch('electrical_schematics.services.asset_downloader.requests.get')
def test_download_photo_no_url(mock_get, downloader):
    """Test handling of missing URL."""
    result = downloader.download_photo(
        url="",
        part_number="TEST123"
    )

    assert result is None
    mock_get.assert_not_called()


@patch('electrical_schematics.services.asset_downloader.requests.get')
def test_download_photo_request_failure(mock_get, downloader):
    """Test handling of request failure."""
    mock_get.side_effect = Exception("Network error")

    # Should not raise, but return None
    result = downloader.download_photo(
        url="https://example.com/photo.jpg",
        part_number="TEST123"
    )

    assert result is None


@patch('electrical_schematics.services.asset_downloader.requests.get')
def test_download_datasheet_success(mock_get, downloader):
    """Test successful datasheet download."""
    # Mock response
    mock_response = Mock()
    mock_response.headers = {'Content-Type': 'application/pdf'}
    mock_response.iter_content = lambda chunk_size: [b'fake pdf data']
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    # Download
    datasheet_path = downloader.download_datasheet(
        url="https://example.com/datasheet.pdf",
        part_number="TEST123"
    )

    # Verify
    assert datasheet_path is not None
    assert datasheet_path.exists()
    assert datasheet_path.name == "TEST123.pdf"
    assert datasheet_path.read_bytes() == b'fake pdf data'


@patch('electrical_schematics.services.asset_downloader.requests.get')
def test_download_both(mock_get, downloader):
    """Test downloading both photo and datasheet."""
    # Mock response
    mock_response = Mock()
    mock_response.headers = {'Content-Type': 'image/jpeg'}
    mock_response.iter_content = lambda chunk_size: [b'fake data']
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    # Download both
    photo_path, datasheet_path = downloader.download_both(
        photo_url="https://example.com/photo.jpg",
        datasheet_url="https://example.com/datasheet.pdf",
        part_number="TEST123"
    )

    # Verify
    assert photo_path is not None
    assert datasheet_path is not None
    assert photo_path.exists()
    assert datasheet_path.exists()
    assert mock_get.call_count == 2


def test_get_photo_path(downloader):
    """Test getting photo path."""
    # No file exists
    assert downloader.get_photo_path("NONEXISTENT") is None

    # Create file
    photo_path = downloader.photos_dir / "TEST123.jpg"
    photo_path.write_bytes(b'test')

    # Should find it
    result = downloader.get_photo_path("TEST123")
    assert result == photo_path


def test_get_datasheet_path(downloader):
    """Test getting datasheet path."""
    # No file exists
    assert downloader.get_datasheet_path("NONEXISTENT") is None

    # Create file
    datasheet_path = downloader.datasheets_dir / "TEST123.pdf"
    datasheet_path.write_bytes(b'test')

    # Should find it
    result = downloader.get_datasheet_path("TEST123")
    assert result == datasheet_path


def test_cleanup_orphaned_assets(downloader):
    """Test cleanup of orphaned assets."""
    # Create some assets
    (downloader.photos_dir / "VALID.jpg").write_bytes(b'valid')
    (downloader.photos_dir / "ORPHAN.jpg").write_bytes(b'orphan')
    (downloader.datasheets_dir / "VALID.pdf").write_bytes(b'valid')
    (downloader.datasheets_dir / "ORPHAN.pdf").write_bytes(b'orphan')

    # Cleanup (only VALID is valid)
    valid_parts = {"VALID"}
    photos_deleted, datasheets_deleted = downloader.cleanup_orphaned_assets(valid_parts)

    # Verify
    assert photos_deleted == 1
    assert datasheets_deleted == 1
    assert (downloader.photos_dir / "VALID.jpg").exists()
    assert not (downloader.photos_dir / "ORPHAN.jpg").exists()
    assert (downloader.datasheets_dir / "VALID.pdf").exists()
    assert not (downloader.datasheets_dir / "ORPHAN.pdf").exists()
