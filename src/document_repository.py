"""
Persistence layer for documents and their chunks.

Writes to the existing DOCUMENTS and DOCUMENT_CHUNKS tables using
parameterized SQL and the connection factory in database.py. Embeddings
are left NULL here and are filled in by a later phase.
"""

import oracledb

from database import get_connection

DEFAULT_STATUS = "UPLOADED"

_INSERT_DOCUMENT = """
    INSERT INTO documents (file_name, file_type, source_path, content_hash, status)
    VALUES (:file_name, :file_type, :source_path, :content_hash, :status)
    RETURNING document_id INTO :document_id
"""

_INSERT_CHUNK = """
    INSERT INTO document_chunks (document_id, chunk_index, chunk_text, token_count)
    VALUES (:document_id, :chunk_index, :chunk_text, :token_count)
"""


def insert_document(
    cursor: oracledb.Cursor,
    file_name: str,
    file_type: str | None = None,
    source_path: str | None = None,
    content_hash: str | None = None,
    status: str = DEFAULT_STATUS,
) -> int:
    """Insert one row into DOCUMENTS and return its generated id.

    The caller owns the transaction: nothing is committed here.

    Args:
        cursor: An open cursor on the transaction's connection.
        file_name: Name of the source file (required by the schema).
        file_type: File extension or MIME-style type.
        source_path: Path the document was read from.
        content_hash: Hash of the document's content, for de-duplication.
        status: Processing status stored on the row.

    Returns:
        int: The document_id assigned by the identity column.
    """
    document_id = cursor.var(oracledb.NUMBER)

    cursor.execute(
        _INSERT_DOCUMENT,
        {
            "file_name": file_name,
            "file_type": file_type,
            "source_path": str(source_path) if source_path is not None else None,
            "content_hash": content_hash,
            "status": status,
            "document_id": document_id,
        },
    )

    return int(document_id.getvalue()[0])


def insert_chunks(
    cursor: oracledb.Cursor,
    document_id: int,
    chunks: list[str],
) -> int:
    """Insert ordered chunks for a document, leaving EMBEDDING NULL.

    chunk_index is the position of the chunk in the list, so the original
    order is recoverable. token_count is approximated by the word count
    until the real tokenizer is introduced with the embedding model.

    Args:
        cursor: An open cursor on the transaction's connection.
        document_id: Id of the parent DOCUMENTS row.
        chunks: Chunk texts, in document order.

    Returns:
        int: The number of chunk rows inserted.

    Raises:
        ValueError: If chunks is empty.
    """
    if not chunks:
        raise ValueError(f"No chunks provided for document_id {document_id}.")

    rows = [
        {
            "document_id": document_id,
            "chunk_index": index,
            "chunk_text": chunk,
            "token_count": len(chunk.split()),
        }
        for index, chunk in enumerate(chunks)
    ]

    # CHUNK_TEXT is a CLOB; bind it as one so oversized chunks are safe.
    cursor.setinputsizes(chunk_text=oracledb.DB_TYPE_CLOB)
    cursor.executemany(_INSERT_CHUNK, rows)

    return len(rows)


def store_document(
    file_name: str,
    chunks: list[str],
    file_type: str | None = None,
    source_path: str | None = None,
    content_hash: str | None = None,
    status: str = DEFAULT_STATUS,
) -> int:
    """Store a document and all of its chunks in a single transaction.

    Commits only when both inserts succeed, and rolls back otherwise. The
    cursor and connection are always closed.

    Args:
        file_name: Name of the source file.
        chunks: Chunk texts, in document order.
        file_type: File extension or MIME-style type.
        source_path: Path the document was read from.
        content_hash: Hash of the document's content.
        status: Processing status stored on the row.

    Returns:
        int: The document_id of the stored document.
    """
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        document_id = insert_document(
            cursor,
            file_name=file_name,
            file_type=file_type,
            source_path=source_path,
            content_hash=content_hash,
            status=status,
        )
        insert_chunks(cursor, document_id, chunks)

        connection.commit()
        return document_id
    except Exception:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
