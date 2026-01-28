"""Tests for component position finder module."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from electrical_schematics.pdf.component_position_finder import (
    ComponentPositionFinder,
    ComponentPosition,
    PositionFinderResult,
    find_device_tag_positions,
    classify_page,
    should_skip_page_by_title,
    SKIP_PAGE_TITLES,
)


def _make_mock_finder(**kwargs):
    """Create a mock ComponentPositionFinder with required attributes.

    Initializes cache dictionaries that are normally set in __init__
    but missing when using __new__ to bypass PDF file opening.
    """
    finder = ComponentPositionFinder.__new__(ComponentPositionFinder)
    finder.doc = kwargs.get("doc", MagicMock())
    if "doc_len" in kwargs:
        finder.doc.__len__ = MagicMock(return_value=kwargs["doc_len"])
    else:
        finder.doc.__len__ = MagicMock(return_value=10)
    finder.pdf_path = kwargs.get("pdf_path", Path("/fake/path.pdf"))
    finder.schematic_pages = kwargs.get("schematic_pages", (0, 25))
    finder._page_classifications = kwargs.get("_page_classifications", {})
    finder._page_skip_cache = kwargs.get("_page_skip_cache", {})
    return finder


def _make_mock_page(text="", title_block_text=None):
    """Create a mock PDF page suitable for classify_page().

    Args:
        text: Full page text returned by get_text() with no format arg
        title_block_text: Optional text to return in title block region.
            If None, returns empty dict for "dict" format.
    """
    mock_page = MagicMock()
    mock_page.rect = MagicMock()
    mock_page.rect.height = 795.0
    mock_page.rect.width = 1193.0

    def get_text_side_effect(fmt=None, **kwargs):
        if fmt == "dict":
            if title_block_text:
                return {
                    "blocks": [{
                        "type": 0,
                        "lines": [{
                            "spans": [{
                                "text": title_block_text,
                                "bbox": (720.0, 761.0, 800.0, 773.0)
                            }]
                        }]
                    }]
                }
            return {"blocks": []}
        return text

    mock_page.get_text.side_effect = get_text_side_effect
    return mock_page


class TestComponentPosition:
    """Tests for ComponentPosition dataclass."""

    def test_create_position(self) -> None:
        """Test creating a component position."""
        pos = ComponentPosition(
            device_tag="-K1",
            x=150.5,
            y=300.2,
            width=25.0,
            height=12.0,
            page=3,
            confidence=0.95,
            match_type="exact"
        )

        assert pos.device_tag == "-K1"
        assert pos.x == 150.5
        assert pos.y == 300.2
        assert pos.width == 25.0
        assert pos.height == 12.0
        assert pos.page == 3
        assert pos.confidence == 0.95
        assert pos.match_type == "exact"

    def test_default_values(self) -> None:
        """Test default values for optional fields."""
        pos = ComponentPosition(
            device_tag="-K2",
            x=100.0,
            y=200.0,
            width=30.0,
            height=15.0,
            page=0
        )

        assert pos.confidence == 1.0
        assert pos.match_type == "exact"


class TestPositionFinderResult:
    """Tests for PositionFinderResult dataclass."""

    def test_empty_result(self) -> None:
        """Test creating an empty result."""
        result = PositionFinderResult()

        assert result.positions == {}
        assert result.unmatched_tags == set()
        assert result.ambiguous_matches == {}

    def test_result_with_data(self) -> None:
        """Test result with positions and unmatched tags."""
        pos = ComponentPosition(
            device_tag="-K1",
            x=100.0,
            y=200.0,
            width=25.0,
            height=12.0,
            page=0
        )

        result = PositionFinderResult(
            positions={"-K1": pos},
            unmatched_tags={"-K2", "-K3"},
            ambiguous_matches={}
        )

        assert "-K1" in result.positions
        assert result.positions["-K1"].x == 100.0
        assert "-K2" in result.unmatched_tags
        assert "-K3" in result.unmatched_tags

    def test_result_has_skipped_pages_and_classifications(self) -> None:
        """Test that result includes skipped pages and page classifications."""
        result = PositionFinderResult()
        result.skipped_pages.add(0)
        result.skipped_pages.add(6)
        result.page_classifications[7] = "Block diagram"

        assert 0 in result.skipped_pages
        assert 6 in result.skipped_pages
        assert result.page_classifications[7] == "Block diagram"


class TestPageClassification:
    """Tests for page classification functions."""

    def test_should_skip_page_by_title_skip_titles(self) -> None:
        """Test that known skip titles are detected."""
        assert should_skip_page_by_title("Cover sheet") is True
        assert should_skip_page_by_title("Cover Sheet") is True
        assert should_skip_page_by_title("Table of contents") is True
        assert should_skip_page_by_title("Global informations") is True
        assert should_skip_page_by_title("Documentation overview") is True
        assert should_skip_page_by_title("Device allocation") is True
        assert should_skip_page_by_title("Location of components") is True
        assert should_skip_page_by_title("Cable summary") is True
        assert should_skip_page_by_title("Motor connection") is True
        assert should_skip_page_by_title("Cable diagram") is True
        assert should_skip_page_by_title("Cable diagram:B1") is True
        assert should_skip_page_by_title("Cable diagram:WE01") is True
        assert should_skip_page_by_title("Parts list") is True

    def test_should_skip_page_by_title_allow_titles(self) -> None:
        """Test that schematic and block diagram pages are NOT skipped."""
        assert should_skip_page_by_title("Block diagram") is False
        assert should_skip_page_by_title("Contactor control") is False
        assert should_skip_page_by_title("Power feed AC") is False
        assert should_skip_page_by_title("Power supply DC") is False
        assert should_skip_page_by_title("CPU") is False
        assert should_skip_page_by_title("X5, X51") is False
        assert should_skip_page_by_title("FI Lift motor") is False
        assert should_skip_page_by_title("Extractor motor") is False
        assert should_skip_page_by_title("") is False

    def test_should_skip_page_by_title_german(self) -> None:
        """Test German title detection."""
        assert should_skip_page_by_title("Deckblatt") is True
        assert should_skip_page_by_title("Inhaltsverzeichnis") is True
        assert should_skip_page_by_title("Kabelplan") is True
        assert should_skip_page_by_title("Artikelstückliste") is True

    def test_should_skip_page_empty_title(self) -> None:
        """Test that empty title does not cause skip."""
        assert should_skip_page_by_title("") is False
        assert should_skip_page_by_title("   ") is False


class TestComponentPositionFinderMethods:
    """Tests for ComponentPositionFinder internal methods using mock instances."""

    @pytest.fixture
    def mock_finder(self):
        """Create a mock finder without actually opening a PDF."""
        return _make_mock_finder()

    def test_build_tag_variants(self, mock_finder) -> None:
        """Test building tag variants for flexible matching."""
        variants = mock_finder._build_tag_variants(["-K1", "+DG-M1", "-A1"])

        # Original tags should be in variants
        assert variants["-K1"] == "-K1"
        assert variants["+DG-M1"] == "+DG-M1"
        assert variants["-A1"] == "-A1"

        # Stripped versions should map to original
        assert variants["K1"] == "-K1"
        assert variants["DG-M1"] == "+DG-M1"
        assert variants["A1"] == "-A1"

        # Suffix-only should map to original
        assert variants["M1"] == "+DG-M1"

    def test_match_text_to_tag_exact(self, mock_finder) -> None:
        """Test exact matching of text to tags."""
        tag_set = {"-K1", "-K2", "+DG-M1"}
        variants = mock_finder._build_tag_variants(list(tag_set))

        # Exact match
        assert mock_finder._match_text_to_tag("-K1", tag_set, variants) == "-K1"
        assert mock_finder._match_text_to_tag("+DG-M1", tag_set, variants) == "+DG-M1"

        # No match
        assert mock_finder._match_text_to_tag("-K3", tag_set, variants) is None
        assert mock_finder._match_text_to_tag("random", tag_set, variants) is None

    def test_match_text_to_tag_variants(self, mock_finder) -> None:
        """Test variant matching of text to tags."""
        tag_set = {"-K1", "+DG-M1"}
        variants = mock_finder._build_tag_variants(list(tag_set))

        # Variant match (stripped prefix)
        assert mock_finder._match_text_to_tag("K1", tag_set, variants) == "-K1"
        assert mock_finder._match_text_to_tag("M1", tag_set, variants) == "+DG-M1"

    def test_match_text_to_tag_terminal_reference(self, mock_finder) -> None:
        """Test matching terminal references like -K1:13."""
        tag_set = {"-K1", "-A1"}
        variants = mock_finder._build_tag_variants(list(tag_set))

        # Terminal reference should match base tag
        assert mock_finder._match_text_to_tag("-K1:13", tag_set, variants) == "-K1"
        assert mock_finder._match_text_to_tag("-A1-X5:3", tag_set, variants) == "-A1"

    def test_calculate_confidence(self, mock_finder) -> None:
        """Test confidence calculation for matches."""
        # Exact match = 1.0
        assert mock_finder._calculate_confidence("-K1", "-K1") == 1.0

        # Starts with tag = 0.9
        assert mock_finder._calculate_confidence("-K1:13", "-K1") == 0.9

        # Tag contained in text = 0.8
        assert mock_finder._calculate_confidence("some-K1-text", "-K1") == 0.8

        # Variant match = 0.85
        assert mock_finder._calculate_confidence("K1", "-K1") == 0.85

    def test_determine_match_type(self, mock_finder) -> None:
        """Test match type determination."""
        assert mock_finder._determine_match_type("-K1", "-K1") == "exact"
        assert mock_finder._determine_match_type("-K1:13", "-K1") == "partial"
        # "K1" is contained in "-K1" so it's partial
        assert mock_finder._determine_match_type("K1", "-K1") == "partial"
        # A truly inferred case would be something unrelated
        assert mock_finder._determine_match_type("other", "something") == "inferred"

    def test_are_positions_close(self, mock_finder) -> None:
        """Test position proximity check."""
        pos1 = ComponentPosition("-K1", 100.0, 200.0, 20.0, 10.0, 0)
        pos2 = ComponentPosition("-K1", 110.0, 205.0, 20.0, 10.0, 0)
        pos3 = ComponentPosition("-K1", 500.0, 600.0, 20.0, 10.0, 0)
        pos4 = ComponentPosition("-K1", 100.0, 200.0, 20.0, 10.0, 1)  # Different page

        # Close positions on same page
        assert mock_finder._are_positions_close([pos1, pos2]) is True

        # Far positions
        assert mock_finder._are_positions_close([pos1, pos3]) is False

        # Different pages
        assert mock_finder._are_positions_close([pos1, pos4]) is False

        # Single position
        assert mock_finder._are_positions_close([pos1]) is True

        # Empty list
        assert mock_finder._are_positions_close([]) is True

    def test_should_skip_page_with_title_cache(self) -> None:
        """Test page skip logic uses title-block-based classification."""
        finder = _make_mock_finder()

        # Pre-populate the cache to simulate title block classification
        finder._page_classifications[0] = "Cover sheet"
        finder._page_classifications[1] = "Block diagram"
        finder._page_classifications[2] = "Contactor control"
        finder._page_classifications[3] = "Cable diagram:B1"

        # Should skip cover sheet
        assert finder._should_skip_page(0) is True

        # Should NOT skip block diagram
        assert finder._should_skip_page(1) is False

        # Should NOT skip schematic pages
        assert finder._should_skip_page(2) is False

        # Should skip cable diagram
        assert finder._should_skip_page(3) is True

    def test_should_skip_page_with_empty_title(self) -> None:
        """Test page skip logic when no title is found (falls back to not skipping)."""
        finder = _make_mock_finder()

        # Mock the page to return empty dict for "dict" format and empty string for text
        mock_page = _make_mock_page(text="", title_block_text=None)
        finder.doc.__getitem__ = MagicMock(return_value=mock_page)

        # Should NOT skip if no title can be determined
        assert finder._should_skip_page(0) is False

    def test_should_skip_page_caches_result(self) -> None:
        """Test that _should_skip_page caches results."""
        finder = _make_mock_finder()

        mock_page = _make_mock_page(text="", title_block_text="Cover sheet")
        finder.doc.__getitem__ = MagicMock(return_value=mock_page)

        # First call should classify and cache
        assert finder._should_skip_page(0) is True
        assert 0 in finder._page_skip_cache
        assert finder._page_skip_cache[0] is True

        # Second call should use cache (won't re-read page)
        assert finder._should_skip_page(0) is True

    def test_special_characters_in_tags(self, mock_finder) -> None:
        """Test device tags with special characters."""
        tag_set = {"-A1-X5", "+DG-B1:0V"}
        variants = mock_finder._build_tag_variants(list(tag_set))

        # Should handle complex tags
        assert "-A1-X5" in variants
        assert "+DG-B1:0V" in variants


class TestDeduplicatePositions:
    """Tests for position deduplication (multi-page support)."""

    def test_deduplicate_same_page_close(self) -> None:
        """Test that close positions on same page are collapsed."""
        finder = _make_mock_finder()
        positions = [
            ComponentPosition("-K1", 100.0, 200.0, 20.0, 10.0, 0, 1.0),
            ComponentPosition("-K1", 105.0, 202.0, 20.0, 10.0, 0, 0.9),
        ]
        result = finder._deduplicate_positions(positions)
        assert len(result) == 1
        assert result[0].confidence == 1.0  # Best confidence kept

    def test_deduplicate_different_pages(self) -> None:
        """Test that positions on different pages are kept."""
        finder = _make_mock_finder()
        positions = [
            ComponentPosition("-K1", 100.0, 200.0, 20.0, 10.0, 0, 1.0),
            ComponentPosition("-K1", 100.0, 200.0, 20.0, 10.0, 5, 0.9),
        ]
        result = finder._deduplicate_positions(positions)
        assert len(result) == 2

    def test_deduplicate_same_page_far(self) -> None:
        """Test that far positions on same page are kept as distinct."""
        finder = _make_mock_finder()
        positions = [
            ComponentPosition("-K1", 100.0, 200.0, 20.0, 10.0, 0, 1.0),
            ComponentPosition("-K1", 500.0, 600.0, 20.0, 10.0, 0, 0.9),
        ]
        result = finder._deduplicate_positions(positions)
        assert len(result) == 2

    def test_deduplicate_single(self) -> None:
        """Test with single position."""
        finder = _make_mock_finder()
        positions = [
            ComponentPosition("-K1", 100.0, 200.0, 20.0, 10.0, 0, 1.0),
        ]
        result = finder._deduplicate_positions(positions)
        assert len(result) == 1

    def test_deduplicate_empty(self) -> None:
        """Test with empty list."""
        finder = _make_mock_finder()
        result = finder._deduplicate_positions([])
        assert len(result) == 0


class TestConvenienceFunction:
    """Tests for the find_device_tag_positions convenience function."""

    def test_find_device_tag_positions_mock(self) -> None:
        """Test the convenience function with mocked PDF."""
        # Create mock position finder result
        mock_result = PositionFinderResult(
            positions={
                "-K1": ComponentPosition("-K1", 100.0, 200.0, 25.0, 12.0, 0, 1.0)
            },
            unmatched_tags={"-K2"},
            ambiguous_matches={}
        )

        with patch('electrical_schematics.pdf.component_position_finder.ComponentPositionFinder') as MockFinder:
            mock_instance = MagicMock()
            mock_instance.find_positions.return_value = mock_result
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=None)
            MockFinder.return_value = mock_instance

            result = find_device_tag_positions(
                Path("/fake/path.pdf"),
                ["-K1", "-K2"]
            )

            assert "-K1" in result
            assert result["-K1"]["x"] == 100.0
            assert result["-K1"]["y"] == 200.0
            assert result["-K1"]["page"] == 0
            assert result["-K1"]["confidence"] == 1.0
            assert "-K2" not in result


class TestIntegrationWithRealPDF:
    """Integration tests with real PDF files (skipped if file not available)."""

    @pytest.fixture
    def drawer_pdf_path(self) -> Path:
        """Get path to DRAWER test PDF."""
        # Try multiple known paths
        paths = [
            Path("/home/liam-oreilly/Documents/electrical_pdf/DRAWER.pdf"),
            Path("/home/liam-oreilly/claude.projects/electricalSchematics/DRAWER.pdf"),
        ]
        for path in paths:
            if path.exists():
                return path
        pytest.skip("Test PDF not found")

    def test_find_positions_in_drawer_pdf(self, drawer_pdf_path: Path) -> None:
        """Test finding positions in a real DRAWER PDF."""
        # Common device tags in DRAWER format
        device_tags = ["-K1", "-K2", "-A1", "+DG-M1"]

        with ComponentPositionFinder(drawer_pdf_path) as finder:
            result = finder.find_positions(device_tags)

            # We should find at least some of these tags
            print(f"Found positions: {list(result.positions.keys())}")
            print(f"Unmatched: {result.unmatched_tags}")
            print(f"Ambiguous: {list(result.ambiguous_matches.keys())}")

            # Verify position data structure
            for tag, pos in result.positions.items():
                assert pos.x > 0 or pos.y > 0, f"Position for {tag} should have coordinates"
                assert pos.page >= 0, f"Position for {tag} should have valid page"
                assert 0 <= pos.confidence <= 1.0, f"Confidence should be 0-1"

    def test_find_all_device_tags(self, drawer_pdf_path: Path) -> None:
        """Test discovering all device tags in PDF."""
        with ComponentPositionFinder(drawer_pdf_path) as finder:
            all_positions = finder.find_all_device_tags(page_range=(0, 5))

            print(f"Discovered {len(all_positions)} device tags in first 5 pages")
            for pos in all_positions[:10]:
                print(f"  {pos.device_tag} at page {pos.page} ({pos.x:.1f}, {pos.y:.1f})")

    def test_page_classification(self, drawer_pdf_path: Path) -> None:
        """Test page classification on real DRAWER PDF."""
        with ComponentPositionFinder(drawer_pdf_path) as finder:
            classifications = finder.classify_all_pages()

            print(f"Page classifications ({len(classifications)} pages):")
            for page_num in sorted(classifications.keys()):
                title = classifications[page_num]
                skip = should_skip_page_by_title(title)
                status = "SKIP" if skip else "SCAN"
                print(f"  Page {page_num:2d}: [{status}] {title}")

            # Page 0 should be Cover sheet (skip)
            if 0 in classifications:
                assert should_skip_page_by_title(classifications[0]) is True

    def test_multi_page_component_detection(self, drawer_pdf_path: Path) -> None:
        """Test that components found on multiple pages are recorded."""
        with ComponentPositionFinder(drawer_pdf_path) as finder:
            # Search all pages for common tags
            result = finder.find_positions(
                ["-K1", "-A1", "-K1.0"],
                search_all_pages=True
            )

            # Check for multi-page matches
            for tag, positions in result.ambiguous_matches.items():
                pages = set(p.page for p in positions)
                if len(pages) > 1:
                    print(f"  {tag} found on pages: {sorted(pages)}")

    def test_skipped_pages_reported(self, drawer_pdf_path: Path) -> None:
        """Test that skipped pages are reported in results."""
        with ComponentPositionFinder(drawer_pdf_path) as finder:
            result = finder.find_positions(["-K1"], search_all_pages=True)

            print(f"Skipped pages: {sorted(result.skipped_pages)}")
            print(f"Page classifications: {result.page_classifications}")

            # Should have skipped some pages (cover sheet, cable diagrams, etc.)
            assert len(result.skipped_pages) > 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_file_not_found(self) -> None:
        """Test that FileNotFoundError is raised for missing PDF."""
        with pytest.raises(FileNotFoundError):
            ComponentPositionFinder(Path("/nonexistent/path.pdf"))

    def test_empty_device_tags_list(self) -> None:
        """Test with empty device tags list using mock finder."""
        finder = _make_mock_finder()

        result = finder.find_positions([])

        assert result.positions == {}
        assert result.unmatched_tags == set()

    def test_context_manager_closes_document(self) -> None:
        """Test that context manager properly closes document."""
        finder = _make_mock_finder()
        mock_doc = MagicMock()
        finder.doc = mock_doc

        # Simulate context manager exit
        finder.__exit__(None, None, None)

        # Document should be closed
        mock_doc.close.assert_called_once()
        assert finder.doc is None

    def test_close_method(self) -> None:
        """Test explicit close method."""
        finder = _make_mock_finder()
        mock_doc = MagicMock()
        finder.doc = mock_doc

        finder.close()

        mock_doc.close.assert_called_once()
        assert finder.doc is None

        # Calling close again should not raise
        finder.close()


class TestFindPositions:
    """Tests for the main find_positions method."""

    @pytest.fixture
    def mock_finder_with_pages(self):
        """Create a mock finder with simulated page content."""
        finder = _make_mock_finder(schematic_pages=(0, 10))

        # Create mock document
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=10)

        # Create mock pages with text content
        def make_page(page_num):
            mock_page = MagicMock()
            mock_page.rect = MagicMock()
            mock_page.rect.height = 795.0
            mock_page.rect.width = 1193.0
            if page_num == 0:
                # Page with device tag text
                def get_text_side_effect(fmt=None, **kwargs):
                    if fmt == "dict":
                        return {
                            "blocks": [{
                                "type": 0,
                                "lines": [{
                                    "spans": [{
                                        "text": "-K1",
                                        "bbox": (100, 200, 130, 215)
                                    }, {
                                        "text": "-K2",
                                        "bbox": (200, 300, 230, 315)
                                    }]
                                }]
                            }]
                        }
                    return "Schematic page with components"
                mock_page.get_text.side_effect = get_text_side_effect
            else:
                def get_text_empty(fmt=None, **kwargs):
                    if fmt == "dict":
                        return {"blocks": []}
                    return "Empty page"
                mock_page.get_text.side_effect = get_text_empty
            return mock_page

        mock_doc.__getitem__ = lambda self, idx: make_page(idx)
        finder.doc = mock_doc

        return finder

    def test_find_positions_basic(self, mock_finder_with_pages) -> None:
        """Test finding positions with mock PDF content."""
        result = mock_finder_with_pages.find_positions(["-K1", "-K2", "-K3"])

        # Should find K1 and K2
        assert "-K1" in result.positions
        assert "-K2" in result.positions

        # K3 should be unmatched
        assert "-K3" in result.unmatched_tags

        # Check position values
        k1_pos = result.positions["-K1"]
        assert k1_pos.x == 115.0  # (100 + 130) / 2
        assert k1_pos.y == 207.5  # (200 + 215) / 2
        assert k1_pos.page == 0

    def test_find_positions_search_all_pages(self, mock_finder_with_pages) -> None:
        """Test searching all pages."""
        result = mock_finder_with_pages.find_positions(["-K1"], search_all_pages=True)

        # Should still find K1
        assert "-K1" in result.positions

    def test_find_positions_multi_page(self) -> None:
        """Test finding the same tag on multiple pages."""
        finder = _make_mock_finder(schematic_pages=(0, 3), doc_len=3)

        def make_page(page_num):
            mock_page = MagicMock()
            mock_page.rect = MagicMock()
            mock_page.rect.height = 795.0
            mock_page.rect.width = 1193.0

            if page_num in (0, 2):
                # Both pages have -K1
                def get_text_with_k1(fmt=None, **kwargs):
                    if fmt == "dict":
                        return {
                            "blocks": [{
                                "type": 0,
                                "lines": [{
                                    "spans": [{
                                        "text": "-K1",
                                        "bbox": (100, 200, 130, 215)
                                    }]
                                }]
                            }]
                        }
                    return "Schematic page"
                mock_page.get_text.side_effect = get_text_with_k1
            else:
                def get_text_empty(fmt=None, **kwargs):
                    if fmt == "dict":
                        return {"blocks": []}
                    return "Empty page"
                mock_page.get_text.side_effect = get_text_empty
            return mock_page

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=3)
        mock_doc.__getitem__ = lambda self, idx: make_page(idx)
        finder.doc = mock_doc

        result = finder.find_positions(["-K1"])

        # Should find K1
        assert "-K1" in result.positions

        # Should have multi-page positions in ambiguous_matches
        assert "-K1" in result.ambiguous_matches
        pages = set(p.page for p in result.ambiguous_matches["-K1"])
        assert 0 in pages
        assert 2 in pages
