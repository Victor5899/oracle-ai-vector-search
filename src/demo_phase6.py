"""
Demonstration runner for the completed Phase 1-6 pipeline.

Extracts data/documents/sample.txt, chunks it, stores the document and
chunks in Oracle, embeds them, and answers one fixed semantic query with
Oracle AI Vector Search. Re-running reuses the stored document when the
file's content hash is unchanged, so no duplicate records are created.

Run: python src/demo_phase6.py
"""

import hashlib
import sys
from pathlib import Path

from chunker import chunk_text
from database import get_connection
from document_processor import extract_text
from document_repository import store_document
from embedding_repository import embed_document
from retriever import search

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PATH = PROJECT_ROOT / "data" / "documents" / "sample.txt"

DEMO_QUERY = "How does the system measure similarity between vectors?"
TOP_K = 3
PREVIEW_CHARS = 220


def _find_existing_document(file_name: str, content_hash: str) -> int | None:
    """Return the id of a previously stored identical document, if any."""
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


def _count_embeddings(document_id: int) -> tuple[int, int]:
    """Return (chunks with an embedding, total chunks) for a document."""
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END), COUNT(*)
            FROM document_chunks
            WHERE document_id = :document_id
            """,
            {"document_id": document_id},
        )
        embedded, total = cursor.fetchone()
        return int(embedded), int(total)
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def _heading(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def main() -> None:
    if not SAMPLE_PATH.is_file():
        raise SystemExit(
            f"Demo document not found: {SAMPLE_PATH}\n"
            "Create data/documents/sample.txt before running this demo."
        )

    _heading("1. Text extraction")
    text = extract_text(SAMPLE_PATH)
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print(f"Document name:      {SAMPLE_PATH.name}")
    print(f"Characters extracted: {len(text):,}")

    _heading("2. Chunking")
    chunks = chunk_text(text)
    print(f"Chunks created:     {len(chunks)}")
    print(f"Words per chunk:    {[len(chunk.split()) for chunk in chunks]}")

    _heading("3. Oracle storage")
    document_id = _find_existing_document(SAMPLE_PATH.name, content_hash)
    if document_id is None:
        document_id = store_document(
            file_name=SAMPLE_PATH.name,
            chunks=chunks,
            file_type=SAMPLE_PATH.suffix.lstrip("."),
            source_path=str(SAMPLE_PATH.relative_to(PROJECT_ROOT)),
            content_hash=content_hash,
        )
        print(f"Oracle document_id: {document_id} (newly stored)")
    else:
        print(f"Oracle document_id: {document_id} (reused, content unchanged)")

    _heading("4. Embeddings")
    newly_embedded = embed_document(document_id)
    embedded, total = _count_embeddings(document_id)
    print(f"Embeddings created this run: {newly_embedded}")
    print(f"Embeddings stored:  {embedded} of {total} chunks (384 dimensions each)")

    _heading("5. Semantic search")
    print(f"Query:              {DEMO_QUERY}")
    results = search(DEMO_QUERY, top_k=TOP_K)
    if not results:
        print("No results returned.")
        return

    for rank, result in enumerate(results, start=1):
        preview = " ".join(result["chunk_text"].split())
        if len(preview) > PREVIEW_CHARS:
            preview = preview[:PREVIEW_CHARS].rstrip() + "..."
        print(
            f"\nResult {rank} | cosine distance {result['distance']:.4f}"
            f" | document {result['document_id']}"
            f" | chunk {result['chunk_index']}"
            f" | chunk_id {result['chunk_id']}"
        )
        print(f"  {preview}")

    print("\nDemo complete: Phase 1-6 pipeline ran end to end.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as error:
        sys.exit(f"Demo failed: {type(error).__name__}: {error}")
