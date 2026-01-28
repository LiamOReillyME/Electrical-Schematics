"""Find component positions in PDF schematics by locating device tag text.

This module uses PyMuPDF to extract text with bounding box coordinates,
allowing automatic placement of components on PDF overlays based on their
device tag labels (e.g., "-K1", "+DG-M1", "-A1").

Includes page classification to skip non-schematic pages (cover sheets,
table of contents, cable diagrams, parts lists, etc.) and multi-page
support for components that appear on more than one page.

IMPORTANT: This finder locates actual device tags in schematic pages, not
diagram annotations or cross-references. Device tags follow industrial
naming conventions:
- Control panel devices: -K1, -A1, -F2 (prefix: -)
- Field devices: +DG-M1, +DG-B1, +DG-V1 (prefix: +)

Generic labels (CD, E, F, G), numbers (0-9), wire colors (BN, WH), and
cross-references (K2:61/19.9) are NOT device tags and will be filtered out.

Block diagram pages, parts lists, and cable routing tables are automatically
skipped based on page title classification.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import fitz  # PyMuPDF


@dataclass
class ComponentPosition:
    """Position information for a component found in a PDF.

    Attributes:
        device_tag: The device tag identifier (e.g., "-K1", "+DG-M1")
        x: X coordinate (center of bounding box) in PDF points
        y: Y coordinate (center of bounding box) in PDF points
        width: Width of the text bounding box
        height: Height of the text bounding box
        page: PDF page number (0-indexed)
        confidence: Confidence score (0.0 to 1.0)
        match_type: Type of match (exact, partial, or inferred)
    """
    device_tag: str
    x: float
    y: float
    width: float
    height: float
    page: int
    confidence: float = 1.0
    match_type: str = "exact"


@dataclass
class PositionFinderResult:
    """Result from component position finding operation.

    Attributes:
        positions: Dictionary mapping device tags to their best/primary position
        unmatched_tags: Set of device tags that were not found
        ambiguous_matches: Dictionary of tags with multiple positions across pages.
            For multi-page components, this contains ALL positions found.
        skipped_pages: Set of page numbers that were skipped during search
        page_classifications: Dictionary mapping page numbers to their title
    """
    positions: Dict[str, ComponentPosition] = field(default_factory=dict)
    unmatched_tags: Set[str] = field(default_factory=set)
    ambiguous_matches: Dict[str, List[ComponentPosition]] = field(default_factory=dict)
    skipped_pages: Set[int] = field(default_factory=set)
    page_classifications: Dict[int, str] = field(default_factory=dict)


# Page title types that should be skipped during auto-placement.
# These are matched case-insensitively against the English title in the
# title block at the bottom center of each page.
SKIP_PAGE_TITLES = [
    "Cover sheet",
    "Table of contents",
    "Global informations",
    "Documentation overview",
    "Device allocation",
    "Location of components",
    "Cable summary",
    "Motor connection",
    "Cable diagram",
    "Parts list",
    "Device tag",
]

# Additional German title block keywords for fallback detection
SKIP_PAGE_TITLES_DE = [
    "Deckblatt",
    "Inhaltsverzeichnis",
    "Allgemeine Informationen",
    "Dokumentation",
    "Geräteansicht",
    "Bauteileanordnung",
    "Kabel Zusammenfassung",
    "Motoranschluss",
    "Kabelplan",
    "Artikelstückliste",
    "Betriebsmittelkennzeichen",
]


def classify_page(page: fitz.Page) -> str:
    """Classify a PDF page by reading its title block.

    Extracts the English page title from the title block region at the
    bottom center of the page. Industrial electrical schematics (DRAWER
    format and similar) place the page title in a standardized title block.

    The title block region is searched at:
    - Y position: bottom 5% of page (typically y > 95% of page height)
    - X position: center region (roughly x = 55%-75% of page width)

    If no title is found in the precise title block region, falls back to
    scanning the bottom 20% of the page for known skip keywords.

    Args:
        page: PyMuPDF page object

    Returns:
        Page title string if found, or empty string if no title detected
    """
    page_rect = page.rect
    ph = page_rect.height
    pw = page_rect.width

    # Primary detection: Look in the title block region
    # Based on analysis of DRAWER format PDFs, the English title appears at
    # approximately y=761 (for a 795pt tall page) and x between 686-820.
    # We use relative coordinates for portability.
    title_block_region = fitz.Rect(
        pw * 0.55,    # Left edge (~656 for 1193pt wide page)
        ph * 0.94,    # Top edge (~747 for 795pt tall page)
        pw * 0.72,    # Right edge (~859 for 1193pt wide page)
        ph * 0.98     # Bottom edge (~779 for 795pt tall page)
    )

    text_dict = page.get_text("dict", clip=title_block_region)
    title_candidates = []

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if text and len(text) > 3:
                    bbox = span.get("bbox", (0, 0, 0, 0))
                    title_candidates.append((bbox[1], text))

    if title_candidates:
        # Sort by Y position and take the first (topmost) which is typically English
        title_candidates.sort(key=lambda t: t[0])
        return title_candidates[0][1]

    # Fallback: scan full bottom region for known keywords
    bottom_region = fitz.Rect(0, ph * 0.80, pw, ph)
    bottom_text = page.get_text(clip=bottom_region)

    all_skip_titles = SKIP_PAGE_TITLES + SKIP_PAGE_TITLES_DE
    for title in all_skip_titles:
        if title.lower() in bottom_text.lower():
            return title

    return ""


def should_skip_page_by_title(page_title: str) -> bool:
    """Determine if a page should be skipped based on its title.

    Checks the page title against the list of non-schematic page types.
    Matching is case-insensitive and uses substring matching to handle
    variations like "Cable diagram:B1" or "Cable diagram:WE01".

    Args:
        page_title: The page title extracted from the title block

    Returns:
        True if the page should be skipped (non-schematic content)
    """
    if not page_title:
        return False

    title_lower = page_title.lower()

    for skip_title in SKIP_PAGE_TITLES:
        if skip_title.lower() in title_lower:
            return True

    for skip_title in SKIP_PAGE_TITLES_DE:
        if skip_title.lower() in title_lower:
            return True

    return False


def is_cross_reference(text: str) -> bool:
    """Check if text is a cross-reference that should be filtered out.

    Cross-references appear in electrical schematics to indicate where a
    component appears on other pages. They have format:
    - TAG:PAGE/COORDINATE (e.g., "K2:61/19.9" means K2 is on page 61)
    - Appear with small arrows pointing to wire connections
    - Should NOT be treated as component locations

    NOTE: We only use pattern matching, not color-based filtering, because
    actual device tags are also rendered in blue in many schematic formats.

    Args:
        text: Text content extracted from PDF

    Returns:
        True if text is a cross-reference and should be filtered
    """
    if not text:
        return False

    # Pattern: TAG:PAGE/COORDINATE (e.g., "K2:61/19.9", "-K3:20/15.3")
    # This pattern requires a slash after the colon, which distinguishes it
    # from terminal references like "-K1:13" or "-A1-X5:3"
    cross_ref_pattern = r'^[A-Z0-9+-]+:\d+/[\d.]+$'
    return bool(re.match(cross_ref_pattern, text))


class ComponentPositionFinder:
    """Find component positions in PDF schematics by locating device tag text.

    Uses PyMuPDF text extraction with bounding boxes to locate device tags
    in schematic pages. Supports various industrial device tag formats:
    - Standard: -K1, -A1, -F2
    - Field devices: +DG-M1, +DG-B1, +CD-V1
    - Terminal references: -A1-X5:3, +DG-B1:0V
    - Contact instances: -K1.1, -K1.2, -K1.3

    Filters out non-device-tag text:
    - Generic labels (CD, E, F, G)
    - Numbers (0-9)
    - Wire colors (BN, WH, GNYE)
    - Cross-references (K2:61/19.9)

    Page filtering:
    - Automatically classifies each page by reading the title block
    - Skips non-schematic pages (cover sheets, cable diagrams, parts lists, etc.)
    - Always includes schematic pages and block diagram pages

    Multi-page support:
    - Components that appear on multiple pages have ALL positions recorded
    - The best position (highest confidence) is stored in positions dict
    - All positions are stored in ambiguous_matches for multi-page overlay support

    Contact positioning:
    - Detects contact instances using .1, .2, .3 suffixes (e.g., -K1.1, -K1.2)
    - Maps contact suffixes to contact blocks for proper symbol rendering

    Example:
        >>> finder = ComponentPositionFinder("/path/to/schematic.pdf")
        >>> result = finder.find_positions(["-K1", "-K2", "+DG-M1"])
        >>> print(result.positions["-K1"])
        ComponentPosition(device_tag='-K1', x=150.5, y=300.2, ...)
        >>> # Check all pages where -K1 appears
        >>> if "-K1" in result.ambiguous_matches:
        ...     for pos in result.ambiguous_matches["-K1"]:
        ...         print(f"  Page {pos.page}: ({pos.x}, {pos.y})")
        >>> # Find contact positions
        >>> contact_positions = finder.find_contact_positions("-K1")
        >>> for suffix, positions in contact_positions.items():
        ...     print(f"Contact {suffix}: {len(positions)} positions")
        >>> finder.close()
    """

    # Patterns for device tag recognition
    DEVICE_TAG_PATTERN = re.compile(r'^[+-][A-Z0-9]+(?:-[A-Z0-9]+)?(?::\S+)?$')

    # Pattern for contact instance references (e.g., -K1.1, -K1.2)
    CONTACT_INSTANCE_PATTERN = re.compile(r'^([+-][A-Z0-9]+(?:-[A-Z0-9]+)?)\.(\d+)$')

    # Pages typically containing schematic diagrams (before cable/parts lists)
    DEFAULT_SCHEMATIC_PAGE_RANGE = (0, 25)

    # Legacy keyword-based skip list (kept for backward compatibility)
    SKIP_PAGE_KEYWORDS = ["Device tag", "Betriebsmittelkennzeichen",
                          "Cable diagram", "Kabelplan", "Parts list"]

    def __init__(
        self,
        pdf_path: Path,
        schematic_pages: Optional[Tuple[int, int]] = None
    ):
        """Initialize the position finder.

        Args:
            pdf_path: Path to the PDF file
            schematic_pages: Optional tuple of (start_page, end_page) to search.
                           If None, searches default schematic page range.
        """
        self.pdf_path = Path(pdf_path)
        self.doc: Optional[fitz.Document] = None
        self.schematic_pages = schematic_pages or self.DEFAULT_SCHEMATIC_PAGE_RANGE

        # Cache for page classifications to avoid re-reading title blocks
        self._page_classifications: Dict[int, str] = {}
        self._page_skip_cache: Dict[int, bool] = {}

        self._open_document()

    def _open_document(self) -> None:
        """Open the PDF document."""
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")
        self.doc = fitz.open(self.pdf_path)

    def close(self) -> None:
        """Close the PDF document."""
        if self.doc:
            self.doc.close()
            self.doc = None

    def __enter__(self) -> "ComponentPositionFinder":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def classify_all_pages(self) -> Dict[int, str]:
        """Classify all pages in the document by their title block.

        Returns:
            Dictionary mapping page number to page title string
        """
        if not self.doc:
            raise RuntimeError("PDF document not open")

        for page_num in range(len(self.doc)):
            if page_num not in self._page_classifications:
                page = self.doc[page_num]
                title = classify_page(page)
                self._page_classifications[page_num] = title

        return dict(self._page_classifications)

    def get_page_title(self, page_num: int) -> str:
        """Get the title of a specific page.

        Uses cached value if available, otherwise reads from PDF.

        Args:
            page_num: Page number (0-indexed)

        Returns:
            Page title string
        """
        if page_num in self._page_classifications:
            return self._page_classifications[page_num]

        if not self.doc or page_num < 0 or page_num >= len(self.doc):
            return ""

        page = self.doc[page_num]
        title = classify_page(page)
        self._page_classifications[page_num] = title
        return title

    def find_positions(
        self,
        device_tags: List[str],
        search_all_pages: bool = False
    ) -> PositionFinderResult:
        """Find positions of device tags in the PDF.

        Searches all non-skipped pages and collects ALL matches for each
        device tag. Components that appear on multiple pages will have all
        positions recorded in ambiguous_matches, with the best position
        (highest confidence) in the positions dict.

        Args:
            device_tags: List of device tags to search for
            search_all_pages: If True, search all pages; otherwise use schematic_pages range

        Returns:
            PositionFinderResult containing found positions, unmatched tags,
            ambiguous matches (multi-page positions), skipped pages, and
            page classifications
        """
        if not self.doc:
            raise RuntimeError("PDF document not open")

        result = PositionFinderResult()
        result.unmatched_tags = set(device_tags)

        # Determine page range to search
        start_page, end_page = self.schematic_pages
        if search_all_pages:
            start_page = 0
            end_page = len(self.doc)
        else:
            end_page = min(end_page, len(self.doc))

        # Build tag lookup for efficient matching
        tag_set = set(device_tags)
        # Also create normalized versions (without + or - prefix for flexible matching)
        tag_variants = self._build_tag_variants(device_tags)

        # Collect ALL positions for each tag across all pages
        all_tag_positions: Dict[str, List[ComponentPosition]] = {}

        for page_num in range(start_page, end_page):
            if self._should_skip_page(page_num):
                result.skipped_pages.add(page_num)
                continue

            # Record classification
            title = self.get_page_title(page_num)
            if title:
                result.page_classifications[page_num] = title

            page_positions = self._extract_positions_from_page(
                page_num, tag_set, tag_variants
            )

            # Accumulate positions across all pages (multi-page support)
            for tag, positions in page_positions.items():
                if tag not in all_tag_positions:
                    all_tag_positions[tag] = []
                all_tag_positions[tag].extend(positions)

        # Process all collected positions
        for tag, positions in all_tag_positions.items():
            result.unmatched_tags.discard(tag)

            if not positions:
                continue

            # Deduplicate: within the same page, collapse close positions
            deduped = self._deduplicate_positions(positions)

            # Always store the best position as the primary
            best = max(deduped, key=lambda p: p.confidence)
            result.positions[tag] = best

            # If found on multiple pages or multiple distinct locations,
            # store ALL positions in ambiguous_matches for multi-page support
            if len(deduped) > 1:
                result.ambiguous_matches[tag] = deduped

        return result

    def find_contact_positions(
        self,
        device_tag: str,
        page_range: Optional[Tuple[int, int]] = None
    ) -> Dict[str, List[ComponentPosition]]:
        """Find positions of contact instances for a relay/contactor.

        For device -K1, searches for:
        - -K1.1 (first contact)
        - -K1.2 (second contact)
        - -K1.3 (third contact)
        etc.

        Args:
            device_tag: The relay/contactor device tag (e.g., "-K1", "-K2")
            page_range: Optional (start, end) page range. If None, uses schematic_pages.

        Returns:
            Dictionary mapping contact suffix to list of positions:
            {'.1': [pos1, pos2, ...], '.2': [...], '.3': [...]}

        Example:
            >>> finder = ComponentPositionFinder("schematic.pdf")
            >>> contacts = finder.find_contact_positions("-K1")
            >>> for suffix, positions in contacts.items():
            ...     print(f"Contact {suffix}:")
            ...     for pos in positions:
            ...         print(f"  Page {pos.page}: ({pos.x}, {pos.y})")
        """
        if not self.doc:
            raise RuntimeError("PDF document not open")

        # Determine page range
        if page_range:
            start_page, end_page = page_range
        else:
            start_page, end_page = self.schematic_pages

        end_page = min(end_page, len(self.doc))

        # Collect contact positions by suffix
        contact_positions: Dict[str, List[ComponentPosition]] = {}

        # Search for contact instances (.1, .2, .3, etc.)
        for page_num in range(start_page, end_page):
            if self._should_skip_page(page_num):
                continue

            page = self.doc[page_num]
            text_dict = page.get_text("dict")

            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:  # Only text blocks
                    continue

                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        bbox = span.get("bbox", (0, 0, 0, 0))

                        # Check if this is a contact instance reference
                        match = self.CONTACT_INSTANCE_PATTERN.match(text)
                        if match:
                            base_tag = match.group(1)
                            suffix = f".{match.group(2)}"

                            # Check if base tag matches our device
                            if base_tag == device_tag:
                                position = ComponentPosition(
                                    device_tag=text,  # Full reference (e.g., "-K1.1")
                                    x=(bbox[0] + bbox[2]) / 2,
                                    y=(bbox[1] + bbox[3]) / 2,
                                    width=bbox[2] - bbox[0],
                                    height=bbox[3] - bbox[1],
                                    page=page_num,
                                    confidence=1.0,
                                    match_type="contact_instance"
                                )

                                if suffix not in contact_positions:
                                    contact_positions[suffix] = []
                                contact_positions[suffix].append(position)

        return contact_positions

    def _deduplicate_positions(
        self,
        positions: List[ComponentPosition],
        threshold: float = 50.0
    ) -> List[ComponentPosition]:
        """Deduplicate positions, keeping one per distinct location.

        Within the same page, positions that are close together are
        collapsed to the one with highest confidence. Positions on
        different pages are always kept as distinct.

        Args:
            positions: List of positions to deduplicate
            threshold: Distance threshold for same-page deduplication

        Returns:
            Deduplicated list of positions
        """
        if len(positions) <= 1:
            return positions

        # Group by page
        by_page: Dict[int, List[ComponentPosition]] = {}
        for pos in positions:
            if pos.page not in by_page:
                by_page[pos.page] = []
            by_page[pos.page].append(pos)

        result = []
        for page_num, page_positions in by_page.items():
            # Within a page, collapse close positions
            clusters: List[List[ComponentPosition]] = []
            used = set()

            for i, pos1 in enumerate(page_positions):
                if i in used:
                    continue
                cluster = [pos1]
                used.add(i)

                for j, pos2 in enumerate(page_positions):
                    if j in used:
                        continue
                    dist = ((pos1.x - pos2.x) ** 2 + (pos1.y - pos2.y) ** 2) ** 0.5
                    if dist <= threshold:
                        cluster.append(pos2)
                        used.add(j)

                clusters.append(cluster)

            # Take best from each cluster
            for cluster in clusters:
                best = max(cluster, key=lambda p: p.confidence)
                result.append(best)

        return result

    def _build_tag_variants(self, device_tags: List[str]) -> Dict[str, str]:
        """Build variants of device tags for flexible matching.

        Creates mappings like:
        - "K1" -> "-K1" (stripped prefix)
        - "A1" -> "-A1"
        - "DG-M1" -> "+DG-M1"

        Args:
            device_tags: List of canonical device tags

        Returns:
            Dictionary mapping variants to canonical tags
        """
        variants = {}
        for tag in device_tags:
            # Add the tag itself
            variants[tag] = tag

            # Add version without +/- prefix
            stripped = tag.lstrip("+-")
            if stripped != tag:
                variants[stripped] = tag

            # Add common variations
            # For "+DG-M1", also match "DG-M1" and "M1"
            parts = stripped.split("-")
            if len(parts) > 1:
                # Just the suffix (e.g., "M1" from "+DG-M1")
                variants[parts[-1]] = tag

        return variants

    def _should_skip_page(self, page_num: int) -> bool:
        """Check if a page should be skipped based on its title block.

        Uses title block classification to determine if a page contains
        non-schematic content (cover sheets, cable diagrams, parts lists, etc.).

        Results are cached to avoid re-reading the title block on each call.

        Args:
            page_num: Page number to check

        Returns:
            True if page should be skipped
        """
        if not self.doc:
            return True

        # Check cache
        if page_num in self._page_skip_cache:
            return self._page_skip_cache[page_num]

        # Get page title from title block
        title = self.get_page_title(page_num)

        # Check if this title indicates a non-schematic page
        skip = should_skip_page_by_title(title)

        # Cache result
        self._page_skip_cache[page_num] = skip
        return skip

    def _extract_positions_from_page(
        self,
        page_num: int,
        tag_set: Set[str],
        tag_variants: Dict[str, str]
    ) -> Dict[str, List[ComponentPosition]]:
        """Extract component positions from a single page.

        Filters out cross-references and non-device-tag text.

        Args:
            page_num: Page number to search
            tag_set: Set of canonical device tags to find
            tag_variants: Dictionary of tag variants to canonical tags

        Returns:
            Dictionary mapping device tags to list of positions found
        """
        if not self.doc:
            return {}

        page = self.doc[page_num]
        positions: Dict[str, List[ComponentPosition]] = {}

        # Get text with positions using "dict" format
        text_dict = page.get_text("dict")

        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:  # Only text blocks
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    bbox = span.get("bbox", (0, 0, 0, 0))

                    # Skip cross-references (TAG:PAGE/COORDINATE format)
                    if is_cross_reference(text):
                        continue

                    # Skip contact instances (handled by find_contact_positions)
                    if self.CONTACT_INSTANCE_PATTERN.match(text):
                        continue

                    # Try to match this text to a device tag
                    matched_tag = self._match_text_to_tag(text, tag_set, tag_variants)

                    if matched_tag:
                        position = ComponentPosition(
                            device_tag=matched_tag,
                            x=(bbox[0] + bbox[2]) / 2,  # Center X
                            y=(bbox[1] + bbox[3]) / 2,  # Center Y
                            width=bbox[2] - bbox[0],
                            height=bbox[3] - bbox[1],
                            page=page_num,
                            confidence=self._calculate_confidence(text, matched_tag),
                            match_type=self._determine_match_type(text, matched_tag)
                        )

                        if matched_tag not in positions:
                            positions[matched_tag] = []
                        positions[matched_tag].append(position)

        return positions

    def _match_text_to_tag(
        self,
        text: str,
        tag_set: Set[str],
        tag_variants: Dict[str, str]
    ) -> Optional[str]:
        """Match extracted text to a device tag.

        Args:
            text: Text extracted from PDF
            tag_set: Set of canonical device tags
            tag_variants: Dictionary of variants to canonical tags

        Returns:
            Canonical device tag if matched, None otherwise
        """
        if not text:
            return None

        # Exact match (highest priority)
        if text in tag_set:
            return text

        # Check against variants
        if text in tag_variants:
            return tag_variants[text]

        # Check if text contains a tag (for cases like "-K1:13" matching "-K1")
        for tag in tag_set:
            if text.startswith(tag):
                return tag
            # Handle terminal references like "-A1-X5:3"
            if tag in text:
                return tag

        # Check variant containment
        for variant, canonical in tag_variants.items():
            if variant == text or text.startswith(variant + ":"):
                return canonical

        return None

    def _calculate_confidence(self, text: str, matched_tag: str) -> float:
        """Calculate confidence score for a match.

        Args:
            text: Original extracted text
            matched_tag: Matched device tag

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Exact match
        if text == matched_tag:
            return 1.0

        # Text starts with tag (e.g., "-K1:13" for "-K1")
        if text.startswith(matched_tag):
            return 0.9

        # Tag is contained in text
        if matched_tag in text:
            return 0.8

        # Variant match (prefix stripped)
        if text.lstrip("+-") == matched_tag.lstrip("+-"):
            return 0.85

        return 0.7

    def _determine_match_type(self, text: str, matched_tag: str) -> str:
        """Determine the type of match.

        Args:
            text: Original extracted text
            matched_tag: Matched device tag

        Returns:
            Match type: "exact", "partial", or "inferred"
        """
        if text == matched_tag:
            return "exact"
        elif matched_tag in text or text in matched_tag:
            return "partial"
        else:
            return "inferred"

    def _are_positions_close(
        self,
        positions: List[ComponentPosition],
        threshold: float = 50.0
    ) -> bool:
        """Check if all positions are close together.

        Args:
            positions: List of positions to check
            threshold: Maximum distance between positions to consider "close"

        Returns:
            True if all positions are within threshold of each other
        """
        if len(positions) <= 1:
            return True

        for i, pos1 in enumerate(positions):
            for pos2 in positions[i + 1:]:
                if pos1.page != pos2.page:
                    return False
                distance = ((pos1.x - pos2.x) ** 2 + (pos1.y - pos2.y) ** 2) ** 0.5
                if distance > threshold:
                    return False

        return True

    def find_all_device_tags(
        self,
        page_range: Optional[Tuple[int, int]] = None
    ) -> List[ComponentPosition]:
        """Find all device tags in the PDF without a predefined list.

        Useful for discovery/analysis of unknown schematics.
        Respects page classification and skips non-schematic pages.

        Args:
            page_range: Optional (start, end) page range to search

        Returns:
            List of all ComponentPosition objects for found device tags
        """
        if not self.doc:
            raise RuntimeError("PDF document not open")

        positions = []
        start_page, end_page = page_range or (0, len(self.doc))
        end_page = min(end_page, len(self.doc))

        for page_num in range(start_page, end_page):
            if self._should_skip_page(page_num):
                continue

            page = self.doc[page_num]
            text_dict = page.get_text("dict")

            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue

                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        bbox = span.get("bbox", (0, 0, 0, 0))

                        # Skip cross-references
                        if is_cross_reference(text):
                            continue

                        # Check if text looks like a device tag
                        if self.DEVICE_TAG_PATTERN.match(text):
                            position = ComponentPosition(
                                device_tag=text,
                                x=(bbox[0] + bbox[2]) / 2,
                                y=(bbox[1] + bbox[3]) / 2,
                                width=bbox[2] - bbox[0],
                                height=bbox[3] - bbox[1],
                                page=page_num,
                                confidence=1.0,
                                match_type="discovered"
                            )
                            positions.append(position)

        return positions


def find_device_tag_positions(
    pdf_path: Path,
    device_tags: List[str],
    schematic_pages: Optional[Tuple[int, int]] = None
) -> Dict[str, dict]:
    """Convenience function to find device tag positions in a PDF.

    This is a simplified interface for the ComponentPositionFinder class.

    Args:
        pdf_path: Path to the PDF file
        device_tags: List of device tags to search for
        schematic_pages: Optional (start, end) page range for schematic pages

    Returns:
        Dictionary mapping device_tag to position dict with keys:
        - x: Center X coordinate
        - y: Center Y coordinate
        - page: Page number (0-indexed)
        - width: Bounding box width
        - height: Bounding box height
        - confidence: Match confidence (0.0-1.0)

    Example:
        >>> positions = find_device_tag_positions(
        ...     Path("schematic.pdf"),
        ...     ["-K1", "-K2", "+DG-M1"]
        ... )
        >>> print(positions["-K1"])
        {'x': 150.5, 'y': 300.2, 'page': 3, 'width': 25.0, 'height': 12.0, 'confidence': 1.0}
    """
    with ComponentPositionFinder(pdf_path, schematic_pages) as finder:
        result = finder.find_positions(device_tags)

        # Convert to simple dictionary format
        positions = {}
        for tag, pos in result.positions.items():
            positions[tag] = {
                'x': pos.x,
                'y': pos.y,
                'page': pos.page,
                'width': pos.width,
                'height': pos.height,
                'confidence': pos.confidence
            }

        return positions
