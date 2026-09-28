"""
End-to-end test for semantic search over stored chunks.

Stores a small test document, embeds it, runs a natural-language query,
checks the shape and ordering of the results, and removes every row it
created. Cleanup also runs when the test fails.
Run directly: python src/test_retriever.py
"""

import uuid

from database import get_connection
from document_repository import store_document
from embedding_repository import embed_document
from retriever import search

# Unique marker so a failed run never collides with, or deletes, real rows.
TEST_FILE_NAME = f"test_retriever_{uuid.uuid4().hex[:12]}.txt"
TEST_CHUNKS = [
    "Oracle Autonomous Database runs vector search inside the database engine.",
    "Sourdough bread needs a starter, flour, water, and patience to rise.",
    "The HNSW index accelerates approximate nearest neighbour lookups.",
    "Penguins huddle together to stay warm during Antarctic winters.",
]
QUERY = "How do birds survive extreme cold?"
EXPECTED_CHUNK_INDEX = 3

REQUIRED_FIELDS = ("chunk_id", "document_id", "chunk_index", "chunk_text", "distance")


def _find_test_documents() -> list[int]:
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT document_id FROM documents WHERE file_name = :file_name",
            {"file_name": TEST_FILE_NAME},
        )
        return [int(row[0]) for row in cursor]
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def _delete_test_documents() -> int:
    """Remove this run's rows, committing only the deletes."""
    document_ids = _find_test_documents()
    if not document_ids:
        return 0

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        for document_id in document_ids:
            cursor.execute(
                "DELETE FROM document_chunks WHERE document_id = :document_id",
                {"document_id": document_id},
            )
            cursor.execute(
                "DELETE FROM documents WHERE document_id = :document_id",
                {"document_id": document_id},
            )
        connection.commit()
        return len(document_ids)
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def run_search_checks() -> None:
    document_id = store_document(
        file_name=TEST_FILE_NAME,
        chunks=TEST_CHUNKS,
        file_type="txt",
        source_path=f"data/documents/{TEST_FILE_NAME}",
        status="TEST",
    )
    embedded = embed_document(document_id)
    assert embedded == len(TEST_CHUNKS), f"embedded {embedded} chunks, expected 4"
    print(f"PASS stored and embedded document {document_id} ({embedded} chunks)")

    results = search(QUERY, top_k=3)
    assert results, "semantic search returned no results"
    print(f"PASS query returned {len(results)} result(s)")

    for position, result in enumerate(results):
        missing = [field for field in REQUIRED_FIELDS if field not in result]
        assert not missing, f"result {position} is missing {missing}"
        assert isinstance(result["distance"], float), (
            f"result {position} distance is not numeric"
        )
    print("PASS every result carries the required fields")

    distances = [result["distance"] for result in results]
    assert distances == sorted(distances), f"distances are not ascending: {distances}"
    print(f"PASS distances ascend from {distances[0]:.4f} to {distances[-1]:.4f}")

    best = results[0]
    assert best["document_id"] == document_id, "top result is not the test document"
    assert best["chunk_index"] == EXPECTED_CHUNK_INDEX, (
        f"expected chunk {EXPECTED_CHUNK_INDEX} first, got {best['chunk_index']}"
    )
    assert best["chunk_text"] == TEST_CHUNKS[EXPECTED_CHUNK_INDEX], (
        "top result text does not match the stored chunk"
    )
    print("PASS nearest chunk is the semantically related one")

    for top_k in (1, 2):
        limited = search(QUERY, top_k=top_k)
        assert len(limited) <= top_k, f"top_k={top_k} returned {len(limited)} results"
    print("PASS top_k limits the number of results")


def main() -> None:
    try:
        run_search_checks()
        print("All checks passed")
    finally:
        # Runs on success and on failure, so no test row is ever left behind.
        removed = _delete_test_documents()
        assert not _find_test_documents(), "test rows were not cleaned up"
        print(f"Cleanup removed {removed} test document(s)")


if __name__ == "__main__":
    main()
