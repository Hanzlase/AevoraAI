"""PDF document extractor using PyMuPDF with page metadata and provenance."""

import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf as fitz

from app.rag.normalization import normalize_unicode


@dataclass
class ExtractedPDFPage:
    """Container for raw and normalized text extracted from a single PDF page."""

    page_number: int  # 1-indexed
    raw_text: str
    normalized_text: str
    char_count: int
    is_low_text: bool
    headings: list[str]


class PDFSourceLoader:
    """Extracts text page-by-page from the NovaCare PDF document with metadata."""

    def __init__(self, pdf_path: Path | str, low_text_threshold: int = 40) -> None:
        self.pdf_path = Path(pdf_path)
        self.low_text_threshold = low_text_threshold

    def extract_pages(self) -> list[ExtractedPDFPage]:
        """Extract text from all pages in the PDF document."""
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF source document not found at: {self.pdf_path}")

        pages: list[ExtractedPDFPage] = []
        doc = fitz.open(self.pdf_path)

        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_num = page_idx + 1
                raw_text = page.get_text("text")

                # Clean whitespace and strip repeated header/footer noise
                lines = raw_text.splitlines()
                cleaned_lines = []
                headings: list[str] = []

                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    # Check for obvious running header or footer pattern
                    if re.match(r"^Page\s+\d+(\s+of\s+\d+)?$", stripped, re.IGNORECASE):
                        continue
                    if re.match(
                        r"^NovaCare Medical Centre\s*[-–—|]?\s*Confidential$",
                        stripped,
                        re.IGNORECASE,
                    ):
                        continue

                    # Detect candidate section headings (numbered or short titles)
                    if (
                        re.match(r"^(\d+\.|\bSection\b|[A-Z][A-Za-z0-9\s]{3,35}:?$)", stripped)
                        and len(stripped) < 50
                    ):
                        headings.append(stripped)

                    cleaned_lines.append(stripped)

                cleaned_text = "\n".join(cleaned_lines)
                normalized_text = normalize_unicode(cleaned_text)
                char_count = len(normalized_text)
                is_low_text = char_count < self.low_text_threshold

                pages.append(
                    ExtractedPDFPage(
                        page_number=page_num,
                        raw_text=raw_text,
                        normalized_text=normalized_text,
                        char_count=char_count,
                        is_low_text=is_low_text,
                        headings=headings,
                    )
                )
        finally:
            doc.close()

        return pages
