"""
Resume Service — PDF parsing, chunking, embedding, and FAISS index management.
"""
import re

import fitz  # PyMuPDF


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract plain text from PDF bytes using PyMuPDF.
    Returns empty string if extraction fails (scanned PDF).
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        for page in doc:
            pages.append(page.get_text("text"))
        doc.close()
        text = "\n".join(pages)
        return _clean_text(text)
    except Exception:
        return ""


def _clean_text(text: str) -> str:
    """Remove excessive whitespace while preserving paragraph structure."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def is_scanned_pdf(text: str) -> bool:
    """Heuristic: less than 50 chars likely means the PDF is image-only."""
    return len(text.strip()) < 50
