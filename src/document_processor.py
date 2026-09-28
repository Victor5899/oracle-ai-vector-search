"""
Document text extraction for the Oracle AI Vector Search project.

Reads PDF and plain-text documents from disk and returns cleaned text.
Chunking, embedding and database insertion are handled elsewhere.
"""

from pathlib import Path

from pypdf import PdfReader

SUPPORTED_EXTENSIONS = (".pdf", ".txt")


class UnsupportedFileTypeError(ValueError):
    """Raised when a file's extension is not PDF or TXT."""


class EmptyDocumentError(ValueError):
    """Raised when a document contains no extractable text."""


def _clean_text(text: str) -> str:
    """Normalise whitespace while preserving paragraph breaks."""
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]

    cleaned_lines = []
    for line in lines:
        # Collapse runs of blank lines into a single paragraph break.
        if not line and (not cleaned_lines or not cleaned_lines[-1]):
            continue
        cleaned_lines.append(" ".join(line.split()))

    return "\n".join(cleaned_lines).strip()


def _read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_text(file_path: str | Path) -> str:
    """Extract cleaned plain text from a PDF or TXT file.

    Args:
        file_path: Path to the document to read.

    Returns:
        str: The document's cleaned text.

    Raises:
        FileNotFoundError: If the path does not point to an existing file.
        UnsupportedFileTypeError: If the extension is not PDF or TXT.
        EmptyDocumentError: If no text could be extracted.
    """
    path = Path(file_path).expanduser()

    if not path.is_file():
        raise FileNotFoundError(f"No such file: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{suffix or path.name}'. "
            f"Supported types: {', '.join(SUPPORTED_EXTENSIONS)}."
        )

    raw_text = _read_pdf(path) if suffix == ".pdf" else _read_txt(path)
    cleaned_text = _clean_text(raw_text)

    if not cleaned_text:
        raise EmptyDocumentError(
            f"No extractable text found in {path.name}. The document may be "
            "empty or contain only scanned images."
        )

    return cleaned_text


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract cleaned text from a PDF or TXT document."
    )
    parser.add_argument("file_path", help="Path to a .pdf or .txt file")
    args = parser.parse_args()

    text = extract_text(args.file_path)
    print(f"Characters extracted: {len(text)}")
    print(text)


if __name__ == "__main__":
    main()
