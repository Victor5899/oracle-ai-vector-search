"""
Round-trip test for the document repository against Oracle.

Stores a small test document, reads it back, verifies the stored ids and
chunk data, then removes every row it created. Cleanup also runs when the
test fails. Run directly: python src/test_document_repository.py
"""

import uuid

from database import get_connection
from document_repository import store_document

# Unique marker so a failed run never collides with, or deletes, real rows.
_MARKER = uuid.uuid4().hex[:12]
TEST_FILE_NAME = f"test_repo_{_MARKER}.txt"
ROLLBACK_FILE_NAME = f"test_rollback_{_MARKER}.txt"
TEST_FILE_NAMES = (TEST_FILE_NAME, ROLLBACK_FILE_NAME)

TEST_CHUNKS = [
    "Oracle AI Vector Search stores embeddings next to relational data.",
    "Chunks keep their original order through the chunk_index column.",
    "Embeddings stay NULL until the embedding phase is implemented.",
]


def _as_text(value) -> str:
    """CLOB columns come back as LOB objects in thin mode."""
    return value.read() if hasattr(value, "read") else value


def _fetch_document(cursor, document_id: int):
    cursor.execute(
        """
        SELECT file_name, file_type, source_path, content_hash, status
        FROM documents
        WHERE document_id = :document_id
        """,
        {"document_id": document_id},
    )
    return cursor.fetchone()


def _fetch_chunks(cursor, document_id: int) -> list[tuple]:
    cursor.execute(
        """
        SELECT chunk_index, chunk_text, token_count, embedding
        FROM document_chunks
        WHERE document_id = :document_id
        ORDER BY chunk_index
        """,
        {"document_id": document_id},
    )
    return [
        (int(index), _as_text(text), int(token_count), embedding)
        for index, text, token_count, embedding in cursor
    ]


def _find_test_documents() -> list[int]:
    """Ids of any rows this run's markers match."""
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT document_id FROM documents
            WHERE file_name IN (:test_name, :rollback_name)
            """,
            {"test_name": TEST_FILE_NAME, "rollback_name": ROLLBACK_FILE_NAME},
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
        content_hash="0" * 64,
        status="TEST",
    )

    assert isinstance(document_id, int), "document_id should be an int"
    assert document_id > 0, "document_id should be a generated identity value"
    print(f"PASS insert returned document_id {document_id}")

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        document = _fetch_document(cursor, document_id)
        assert document is not None, "document row was not found"
        file_name, file_type, source_path, content_hash, status = document
        assert file_name == TEST_FILE_NAME, "file_name does not match"
        assert file_type == "txt", "file_type does not match"
        assert source_path.endswith(TEST_FILE_NAME), "source_path does not match"
        assert content_hash == "0" * 64, "content_hash does not match"
        assert status == "TEST", "status does not match"
        print("PASS document row matches the values that were inserted")

        chunks = _fetch_chunks(cursor, document_id)
        assert len(chunks) == len(TEST_CHUNKS), "unexpected number of chunks"
        for position, (index, text, token_count, embedding) in enumerate(chunks):
            assert index == position, f"chunk {position} has index {index}"
            assert text == TEST_CHUNKS[position], f"chunk {position} text differs"
            expected_tokens = len(TEST_CHUNKS[position].split())
            assert token_count == expected_tokens, f"chunk {position} token_count"
            assert embedding is None, f"chunk {position} embedding should be NULL"
        print("PASS chunks were read back in order with NULL embeddings")
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def run_rollback_check() -> None:
    """A failure mid-transaction must leave no document row behind."""
    try:
        store_document(file_name=ROLLBACK_FILE_NAME, chunks=["valid chunk", None])
    except Exception:
        pass
    else:
        raise AssertionError("expected store_document to fail on a bad chunk")

    assert ROLLBACK_FILE_NAME not in _fetched_file_names(), (
        "failed insert was not rolled back"
    )
    print("PASS failed insert rolled back cleanly")


def _fetched_file_names() -> list[str]:
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT file_name FROM documents
            WHERE file_name IN (:test_name, :rollback_name)
            """,
            {"test_name": TEST_FILE_NAME, "rollback_name": ROLLBACK_FILE_NAME},
        )
        return [row[0] for row in cursor]
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def main() -> None:
    try:
        run_round_trip()
        run_rollback_check()
        print("All checks passed")
    finally:
        # Runs on success and on failure, so no test row is ever left behind.
        removed = _delete_test_documents()
        assert not _find_test_documents(), "test rows were not cleaned up"
        print(f"Cleanup removed {removed} test document(s)")


if __name__ == "__main__":
    main()
