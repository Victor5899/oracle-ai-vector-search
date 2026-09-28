"""
Text chunking for the Oracle AI Vector Search project.

Splits extracted document text into ordered, overlapping chunks that are
sized for the sentence-transformers/all-MiniLM-L6-v2 embedding model.
Embedding and database insertion are handled elsewhere.
"""

import re
from collections import deque

MIN_CHUNK_WORDS = 500
MAX_CHUNK_WORDS = 800
OVERLAP_WORDS = 75


class EmptyTextError(ValueError):
    """Raised when there is no text to chunk."""


def _split_paragraphs(text: str) -> list[str]:
    """Split text on blank lines and normalise whitespace in each paragraph."""
    paragraphs = (" ".join(part.split()) for part in re.split(r"\n\s*\n", text))
    return [paragraph for paragraph in paragraphs if paragraph]


def chunk_text(
    text: str,
    min_words: int = MIN_CHUNK_WORDS,
    max_words: int = MAX_CHUNK_WORDS,
    overlap_words: int = OVERLAP_WORDS,
) -> list[str]:
    """Split document text into ordered, overlapping chunks.

    Paragraphs are packed whole wherever they fit. A paragraph is only cut
    mid-way when the current chunk is still below min_words, so paragraph
    boundaries survive whenever that is practical. Each chunk after the
    first begins with the last overlap_words words of its predecessor.

    Args:
        text: Cleaned document text, as returned by document_processor.
        min_words: Word count below which a chunk is not closed early.
        max_words: Hard upper bound on words per chunk.
        overlap_words: Words repeated from the end of the previous chunk.

    Returns:
        list[str]: The chunks, in their original document order.

    Raises:
        EmptyTextError: If text is empty or whitespace-only.
        ValueError: If the size arguments are inconsistent.
    """
    if not 0 <= overlap_words < min_words <= max_words:
        raise ValueError(
            "Expected 0 <= overlap_words < min_words <= max_words, got "
            f"overlap_words={overlap_words}, min_words={min_words}, "
            f"max_words={max_words}."
        )

    paragraphs = _split_paragraphs(text)
    if not paragraphs:
        raise EmptyTextError("Cannot chunk empty or whitespace-only text.")

    pending = deque(paragraphs)
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0
    new_words = 0

    def flush() -> None:
        nonlocal current, current_words, new_words

        chunk = "\n\n".join(current)
        chunks.append(chunk)

        carried = " ".join(chunk.split()[len(chunk.split()) - overlap_words :])
        current = [carried] if carried else []
        current_words = len(carried.split())
        new_words = 0

    while pending:
        paragraph = pending.popleft()
        words = paragraph.split()
        space = max_words - current_words

        if len(words) <= space:
            current.append(paragraph)
            current_words += len(words)
            new_words += len(words)
            continue

        if current_words >= min_words:
            # Close the chunk on a paragraph boundary and retry this
            # paragraph at the start of the next one.
            pending.appendleft(paragraph)
            flush()
            continue

        # The chunk is still too small to close, so cut the paragraph and
        # carry the remainder forward.
        current.append(" ".join(words[:space]))
        current_words += space
        new_words += space
        pending.appendleft(" ".join(words[space:]))
        flush()

    if new_words:
        flush()

    return chunks
