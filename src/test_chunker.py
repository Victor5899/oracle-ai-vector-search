"""
Tests for the chunker used by the Oracle AI Vector Search project.

Verifies chunk count, ordering, overlap between adjacent chunks, and the
handling of empty text. Run directly: python src/test_chunker.py
"""

from chunker import (
    MAX_CHUNK_WORDS,
    MIN_CHUNK_WORDS,
    OVERLAP_WORDS,
    EmptyTextError,
    chunk_text,
)


def _sample_text(paragraphs: int = 20, words_per_paragraph: int = 120) -> str:
    """Build deterministic text with uniquely numbered words."""
    counter = iter(range(paragraphs * words_per_paragraph))
    return "\n\n".join(
        " ".join(f"w{next(counter)}" for _ in range(words_per_paragraph))
        for _ in range(paragraphs)
    )


def test_long_text_produces_multiple_chunks() -> None:
    chunks = chunk_text(_sample_text())

    assert len(chunks) > 1, "expected long text to produce multiple chunks"
    for index, chunk in enumerate(chunks):
        word_count = len(chunk.split())
        assert word_count <= MAX_CHUNK_WORDS, f"chunk {index} exceeds max size"
        if index < len(chunks) - 1:
            assert word_count >= MIN_CHUNK_WORDS, f"chunk {index} is too small"


def test_chunk_order_is_preserved() -> None:
    text = _sample_text()
    chunks = chunk_text(text)

    # Every word appears once in the source, so first occurrences must be
    # in ascending order across the chunks.
    positions = [text.index(chunk.split()[0]) for chunk in chunks]
    assert positions == sorted(positions), "chunks are out of document order"

    rebuilt = chunks[0].split()
    for chunk in chunks[1:]:
        rebuilt.extend(chunk.split()[OVERLAP_WORDS:])
    assert rebuilt == text.split(), "chunks do not reassemble into the source"


def test_adjacent_chunks_overlap() -> None:
    chunks = chunk_text(_sample_text())

    for index in range(len(chunks) - 1):
        tail = chunks[index].split()[-OVERLAP_WORDS:]
        head = chunks[index + 1].split()[:OVERLAP_WORDS]
        assert tail == head, f"chunks {index} and {index + 1} do not overlap"


def test_empty_text_is_rejected() -> None:
    for text in ("", "   ", "\n\t \n"):
        try:
            chunk_text(text)
        except EmptyTextError:
            continue
        raise AssertionError(f"expected EmptyTextError for {text!r}")


def main() -> None:
    tests = (
        test_long_text_produces_multiple_chunks,
        test_chunk_order_is_preserved,
        test_adjacent_chunks_overlap,
        test_empty_text_is_rejected,
    )

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print(f"{len(tests)} passed")


if __name__ == "__main__":
    main()
