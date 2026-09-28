"""
Round-trip test for storing embeddings in the Oracle VECTOR column.

Stores a small test document, embeds its chunks, reads the vectors back,
and removes every row it created. Cleanup also runs when the test fails.
Run directly: python src/test_embedding_repository.py
"""

import uuid

from database import get_connection
from document_repository import store_document
from embedding_repository import embed_document
from embeddings import EMBEDDING_DIMENSION

# Unique marker so a failed run never collides with, or deletes, real rows.
TEST_FILE_NAME = f"test_embeddings_{uuid.uuid4().hex[:12]}.txt"
TEST_CHUNKS = [
    "Oracle AI Vector Search finds documents by meaning, not keywords.",
    "Each chunk is embedded into a 384-dimensional FLOAT32 vector.",
    "The vector is stored alongside the chunk text in the same table.",
]


def _fetch_embeddings(document_id: int) -> list[tuple[int, object]]:
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT chunk_index, embedding
            FROM document_chunks
            WHERE document_id = :document_id
            ORDER BY chunk_index
            """,
            {"document_id": document_id},
        )
        return [(int(index), embedding) for index, embedding in cursor]
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


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


def run_round_trip() -> None:
    document_id = store_document(
        file_name=TEST_FILE_NAME,
        chunks=TEST_CHUNKS,
        file_type="txt",
        source_path=f"data/documents/{TEST_FILE_NAME}",
        status="TEST",
    )
    print(f"PASS stored test document {document_id} with {len(TEST_CHUNKS)} chunks")

    updated = embed_document(document_id)
    assert updated == len(TEST_CHUNKS), f"embedded {updated} chunks, expected 3"
    print(f"PASS embedded and stored {updated} chunk vectors")

    rows = _fetch_embeddings(document_id)
    assert len(rows) == len(TEST_CHUNKS), "unexpected number of chunk rows"
    for position, (index, embedding) in enumerate(rows):
        assert index == position, f"chunk {position} has index {index}"
        assert embedding is not None, f"chunk {position} embedding is NULL"
        assert len(embedding) == EMBEDDING_DIMENSION, (
            f"chunk {position} embedding has {len(embedding)} dimensions"
        )
    print(f"PASS all {len(rows)} embeddings are non-NULL with dimension 384")

    # A second pass must find nothing left to embed.
    assert embed_document(document_id) == 0, "re-run should skip embedded chunks"
    print("PASS re-running skips chunks that already have a vector")


def main() -> None:
    try:
        run_round_trip()
        print("All checks passed")
    finally:
        # Runs on success and on failure, so no test row is ever left behind.
        removed = _delete_test_documents()
        assert not _find_test_documents(), "test rows were not cleaned up"
        print(f"Cleanup removed {removed} test document(s)")


if __name__ == "__main__":
    main()
