"""PDF rendering and display."""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional, Tuple
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QByteArray


class PDFRenderer:
    """Renders PDF pages to images for display in Qt."""

    def __init__(self, pdf_path: Path):
        """
        Initialize the PDF renderer.

        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = pdf_path
        self.doc: Optional[fitz.Document] = None
        self._load_pdf()

    def _load_pdf(self) -> None:
        """Load the PDF document."""
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

        self.doc = fitz.open(self.pdf_path)

    def get_page_count(self) -> int:
        """Get the number of pages in the PDF."""
        return len(self.doc) if self.doc else 0

    def render_page(self, page_num: int, zoom: float = 1.0) -> Optional[QPixmap]:
        """
        Render a PDF page to a QPixmap.

        Args:
            page_num: Page number (0-indexed)
            zoom: Zoom level (1.0 = 100%)

        Returns:
            QPixmap of the rendered page, or None if error
        """
        if not self.doc or page_num < 0 or page_num >= len(self.doc):
            return None

        page = self.doc[page_num]

        # Render at higher resolution for better quality
        mat = fitz.Matrix(zoom * 2, zoom * 2)  # 2x for retina/high-DPI
        pix = page.get_pixmap(matrix=mat)

        # Convert to QImage
        img_data = pix.tobytes("ppm")
        qimg = QImage.fromData(QByteArray(img_data), "PPM")

        return QPixmap.fromImage(qimg)

    def get_page_size(self, page_num: int) -> Tuple[float, float]:
        """
        Get the size of a page in points.

        Args:
            page_num: Page number (0-indexed)

        Returns:
            Tuple of (width, height) in points
        """
        if not self.doc or page_num < 0 or page_num >= len(self.doc):
            return (0.0, 0.0)

        page = self.doc[page_num]
        rect = page.rect
        return (rect.width, rect.height)

    def extract_text(self, page_num: int) -> str:
        """
        Extract text from a page.

        Args:
            page_num: Page number (0-indexed)

        Returns:
            Extracted text
        """
        if not self.doc or page_num < 0 or page_num >= len(self.doc):
            return ""

        page = self.doc[page_num]
        return page.get_text()

    def close(self) -> None:
        """Close the PDF document."""
        if self.doc:
            self.doc.close()
            self.doc = None

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.close()
