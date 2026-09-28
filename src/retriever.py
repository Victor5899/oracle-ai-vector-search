"""
Semantic search over stored document chunks.

Embeds a natural-language query with embeddings.py and ranks chunks by
COSINE distance against DOCUMENT_CHUNKS.EMBEDDING, using the existing
IDX_CHUNKS_EMBEDDING HNSW index.
"""

from array import array

import oracledb

from database import get_connection
from embeddings import embed_text

DEFAULT_TOP_K = 5

# 'f' is a 4-byte C float, matching the column's FLOAT32 storage format.
_VECTOR_TYPECODE = "f"

_SEARCH_TEMPLATE = """
    SELECT chunk_id,
           document_id,
           chunk_index,
           chunk_text,
           VECTOR_DISTANCE(embedding, :query_vector, COSINE) AS distance
    FROM document_chunks
    WHERE embedding IS NOT NULL
    ORDER BY distance
    FETCH {approx} FIRST :top_k ROWS ONLY
"""


def search(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    approximate: bool = True,
) -> list[dict]:
    """Find the chunks most similar to a natural-language query.

    Args:
        query: The natural-language question or phrase to search for.
        top_k: Maximum number of chunks to return.
        approximate: When True, use approximate search so the HNSW index
            is applied; set False for an exact scan.

    Returns:
        list[dict]: Up to top_k results ordered from nearest to furthest,
        each with chunk_id, document_id, chunk_index, chunk_text and
        distance.

    Raises:
        ValueError: If query is blank or top_k is less than one.
    """
    if not query or not query.strip():
        raise ValueError("Cannot search for empty or whitespace-only text.")
    if top_k < 1:
        raise ValueError(f"top_k must be at least 1, got {top_k}.")

    query_vector = array(_VECTOR_TYPECODE, embed_text(query))
    statement = _SEARCH_TEMPLATE.format(approx="APPROX" if approximate else "")

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.setinputsizes(query_vector=oracledb.DB_TYPE_VECTOR)
        cursor.execute(statement, {"query_vector": query_vector, "top_k": top_k})

        # CHUNK_TEXT is a CLOB, which comes back as a LOB object in thin mode.
        return [
            {
                "chunk_id": int(chunk_id),
                "document_id": int(document_id),
                "chunk_index": int(chunk_index),
                "chunk_text": text.read() if hasattr(text, "read") else text,
                "distance": float(distance),
            }
            for chunk_id, document_id, chunk_index, text, distance in cursor
        ]
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
