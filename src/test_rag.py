"""
Tests for retrieval-augmented answer generation.

Reuses the stored sample document (storing it only if it is not already
in Oracle), checks retrieval and prompt construction without calling the
API, then generates one real answer when OPENAI_API_KEY is configured.
Run directly: python src/test_rag.py
"""

import hashlib
import os
from pathlib import Path

import rag
from chunker import chunk_text
from database import get_connection
from document_processor import extract_text
from document_repository import store_document
from embedding_repository import embed_document

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PATH = PROJECT_ROOT / "data" / "documents" / "sample.txt"

QUESTION = "What distance metric does this project use for vector similarity?"
TOP_K = 3
REQUIRED_SOURCE_FIELDS = (
    "chunk_id",
    "document_id",
    "chunk_index",
    "chunk_text",
    "distance",
)


def _find_document(file_name: str, content_hash: str) -> int | None:
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT document_id
            FROM documents
            WHERE file_name = :file_name
              AND content_hash = :content_hash
            ORDER BY document_id
            FETCH FIRST 1 ROWS ONLY
            """,
            {"file_name": file_name, "content_hash": content_hash},
        )
        row = cursor.fetchone()
        return int(row[0]) if row else None
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def ensure_sample_document() -> int:
    """Return the sample document's id, storing it only if it is absent."""
    if not SAMPLE_PATH.is_file():
        raise SystemExit(
            f"Sample document not found: {SAMPLE_PATH}\n"
            "Create data/documents/sample.txt before running this test."
        )

    text = extract_text(SAMPLE_PATH)
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

    document_id = _find_document(SAMPLE_PATH.name, content_hash)
    if document_id is None:
        document_id = store_document(
            file_name=SAMPLE_PATH.name,
            chunks=chunk_text(text),
            file_type=SAMPLE_PATH.suffix.lstrip("."),
            source_path=str(SAMPLE_PATH.relative_to(PROJECT_ROOT)),
            content_hash=content_hash,
        )
        print(f"PASS stored sample document as {document_id}")
    else:
        print(f"PASS reused existing sample document {document_id}")

    embed_document(document_id)
    return document_id


def test_retrieval_returns_relevant_chunks(document_id: int) -> list[dict]:
    sources = rag.retrieve_context(QUESTION, top_k=TOP_K)

    assert sources, "retrieval returned no chunks"
    assert len(sources) <= TOP_K, f"retrieval returned {len(sources)} chunks"
    for position, source in enumerate(sources):
        missing = [f for f in REQUIRED_SOURCE_FIELDS if f not in source]
        assert not missing, f"source {position} is missing {missing}"
    assert any(source["document_id"] == document_id for source in sources), (
        "no chunk from the sample document was retrieved"
    )
    print(f"PASS retrieved {len(sources)} relevant chunk(s) from the sample")

    return sources


def test_prompt_contains_only_context_and_question(sources: list[dict]) -> None:
    context = rag.build_context(sources)
    messages = rag.build_messages(QUESTION, context)
    user_content = messages[-1]["content"]

    for source in sources:
        assert source["chunk_text"] in user_content, "a retrieved chunk is missing"
    assert QUESTION in user_content, "the question is missing from the prompt"

    # Nothing beyond the retrieved chunks and the question reaches the model.
    remainder = user_content.replace(QUESTION, "")
    for source in sources:
        remainder = remainder.replace(source["chunk_text"], "")
    leaked = [
        word
        for word in remainder.split()
        if len(word) > 12 and word.isalpha()
    ]
    assert not leaked, f"unexpected content in the prompt: {leaked[:5]}"
    print("PASS prompt carries only the retrieved context and the question")


def test_missing_api_key_is_reported() -> None:
    saved_key = os.environ.pop("OPENAI_API_KEY", None)
    rag.get_client.cache_clear()
    try:
        rag.get_client()
    except rag.MissingConfigurationError as error:
        assert "OPENAI_API_KEY" in str(error), "error should name the variable"
        print("PASS missing OPENAI_API_KEY raises a clear error")
    else:
        raise AssertionError("expected MissingConfigurationError")
    finally:
        if saved_key is not None:
            os.environ["OPENAI_API_KEY"] = saved_key
        rag.get_client.cache_clear()


def test_answer_question(document_id: int) -> None:
    result = rag.answer_question(QUESTION, top_k=TOP_K)

    assert result["question"] == QUESTION, "the question was not echoed back"
    assert result["answer"].strip(), "the model returned an empty answer"
    assert result["sources"], "no sources were returned with the answer"
    for position, source in enumerate(result["sources"]):
        missing = [f for f in REQUIRED_SOURCE_FIELDS if f not in source]
        assert not missing, f"source {position} is missing {missing}"
    print("PASS answer and sources were returned")

    print(f"\nQuestion: {result['question']}")
    print(f"Answer:   {result['answer']}")
    print("Sources:")
    for source in result["sources"]:
        print(
            f"  chunk_id {source['chunk_id']}"
            f" | document {source['document_id']}"
            f" | chunk {source['chunk_index']}"
            f" | distance {source['distance']:.4f}"
        )


def main() -> None:
    document_id = ensure_sample_document()
    sources = test_retrieval_returns_relevant_chunks(document_id)
    test_prompt_contains_only_context_and_question(sources)
    test_missing_api_key_is_reported()

    if not os.getenv("OPENAI_API_KEY"):
        print(
            "\nSKIP live answer generation: OPENAI_API_KEY is not set.\n"
            "Add OPENAI_API_KEY and OPENAI_MODEL to .env, then re-run."
        )
        return

    test_answer_question(document_id)
    print("\nAll checks passed")


if __name__ == "__main__":
    main()
