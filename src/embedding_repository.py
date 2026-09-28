"""
Embedding persistence for the Oracle AI Vector Search project.

Reads chunk text back from DOCUMENT_CHUNKS, embeds it with embeddings.py,
and writes the vectors into the existing EMBEDDING VECTOR(384, FLOAT32)
column, matching rows on chunk_id.
"""

from array import array

import oracledb

from database import get_connection
from embeddings import EMBEDDING_DIMENSION, embed_texts

# 'f' is a 4-byte C float, matching the column's FLOAT32 storage format.
_VECTOR_TYPECODE = "f"

_SELECT_CHUNKS = """
    SELECT chunk_id, chunk_text
    FROM document_chunks
    WHERE document_id = :document_id
    ORDER BY chunk_index
"""

_SELECT_CHUNKS_WITHOUT_EMBEDDING = """
    SELECT chunk_id, chunk_text
    FROM document_chunks
    WHERE document_id = :document_id
      AND embedding IS NULL
    ORDER BY chunk_index
"""

_UPDATE_EMBEDDING = """
    UPDATE document_chunks
    SET embedding = :embedding
    WHERE chunk_id = :chunk_id
"""


def fetch_chunks(
    cursor: oracledb.Cursor,
    document_id: int,
    only_missing: bool = True,
) -> list[tuple[int, str]]:
    """Read a document's chunks as (chunk_id, chunk_text) pairs.

    Args:
        cursor: An open cursor on the transaction's connection.
        document_id: Id of the parent DOCUMENTS row.
        only_missing: When True, skip chunks that already have a vector.

    Returns:
        list[tuple[int, str]]: Chunk ids and text, in chunk_index order.
    """
    statement = _SELECT_CHUNKS_WITHOUT_EMBEDDING if only_missing else _SELECT_CHUNKS
    cursor.execute(statement, {"document_id": document_id})

    # CHUNK_TEXT is a CLOB, which comes back as a LOB object in thin mode.
    return [
        (int(chunk_id), text.read() if hasattr(text, "read") else text)
        for chunk_id, text in cursor
    ]


def update_embeddings(
    cursor: oracledb.Cursor,
    embeddings_by_chunk_id: dict[int, list[float]],
) -> int:
    """Write embeddings into the EMBEDDING column, keyed by chunk_id.

    The caller owns the transaction: nothing is committed here.

    Args:
        cursor: An open cursor on the transaction's connection.
        embeddings_by_chunk_id: One 384-dimensional vector per chunk id.

    Returns:
        int: The number of chunk rows updated.

    Raises:
        ValueError: If a vector does not have exactly 384 dimensions, or
            if an update did not match an existing chunk row.
    """
    if not embeddings_by_chunk_id:
        return 0

    rows = []
    for chunk_id, vector in embeddings_by_chunk_id.items():
        if len(vector) != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Chunk {chunk_id} has a {len(vector)}-dimensional embedding, "
                f"expected {EMBEDDING_DIMENSION}."
            )
        rows.append(
            {
                "chunk_id": chunk_id,
                "embedding": array(_VECTOR_TYPECODE, vector),
            }
        )

    cursor.setinputsizes(embedding=oracledb.DB_TYPE_VECTOR)
    cursor.executemany(_UPDATE_EMBEDDING, rows)

    if cursor.rowcount != len(rows):
        raise ValueError(
            f"Updated {cursor.rowcount} chunk row(s) but expected {len(rows)}."
        )

    return cursor.rowcount


def embed_document(document_id: int, only_missing: bool = True) -> int:
    """Embed a stored document's chunks and save the vectors.

    Runs as one transaction: commits only when every chunk is updated,
    and rolls back otherwise. The cursor and connection are always closed.

    Args:
        document_id: Id of the document whose chunks should be embedded.
        only_missing: When True, only chunks with a NULL embedding are
            processed, so the call can safely be repeated.

    Returns:
        int: The number of chunk rows given an embedding.
    """
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        chunks = fetch_chunks(cursor, document_id, only_missing=only_missing)
        if not chunks:
            return 0

        chunk_ids = [chunk_id for chunk_id, _ in chunks]
        vectors = embed_texts([text for _, text in chunks])
        updated = update_embeddings(cursor, dict(zip(chunk_ids, vectors)))

        connection.commit()
        return updated
    except Exception:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
