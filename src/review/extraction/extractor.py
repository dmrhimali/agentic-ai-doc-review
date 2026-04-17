"""Extract plain text from PDF, DOCX, and TXT files."""

import logging
from pathlib import Path

import docx
from pypdf import PdfReader

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def extract_text(file_path: str) -> str:
    """Extract text content from a document file.

    Args:
        file_path: Path to the document file.

    Returns:
        Extracted plain text content.

    Raises:
        ValueError: If the file type is not supported.
        FileNotFoundError: If the file does not exist.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {suffix}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    match suffix:
        case ".pdf":
            return _extract_pdf(path)
        case ".docx":
            return _extract_docx(path)
        case ".txt":
            return _extract_txt(path)
        case _:
            raise ValueError(f"Unsupported file type: {suffix}")


def _extract_pdf(path: Path) -> str:
    """Extract text from a PDF file."""
    logger.info("Extracting text from PDF: %s", path.name)
    try:
        reader = PdfReader(str(path))
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        result = "\n\n".join(pages)
    except Exception as e:
        logger.error("Failed to parse PDF %s: %s", path.name, e)
        raise ValueError(
            f"Failed to parse PDF '{path.name}': {e}"
        ) from e

    if not result.strip():
        logger.warning("PDF extracted but empty: %s", path.name)

    return result


def _extract_docx(path: Path) -> str:
    """Extract text from a DOCX file."""
    logger.info("Extracting text from DOCX: %s", path.name)
    try:
        doc = docx.Document(str(path))
        paragraphs = [
            p.text for p in doc.paragraphs if p.text.strip()
        ]
        result = "\n\n".join(paragraphs)
    except Exception as e:
        logger.error("Failed to parse DOCX %s: %s", path.name, e)
        raise ValueError(
            f"Failed to parse DOCX '{path.name}': {e}"
        ) from e

    if not result.strip():
        logger.warning(
            "DOCX extracted but empty: %s", path.name
        )

    return result


def _extract_txt(path: Path) -> str:
    """Extract text from a plain text file."""
    logger.info("Extracting text from TXT: %s", path.name)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        logger.error(
            "Encoding error reading %s: %s", path.name, e
        )
        raise ValueError(
            f"Failed to read '{path.name}': {e}"
        ) from e
