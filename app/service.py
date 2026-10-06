"""
Business logic behind the REST API.

Every step is delegated to the existing Phase 1-7 modules: this layer
only sequences them, keeps uploads in a temporary file, and reuses an
already stored document when its content hash is unchanged.
"""

import hashlib
import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path

import rag
from chunker import chunk_text
from database import get_connection
from document_processor import (
    SUPPORTED_EXTENSIONS,
    UnsupportedFileTypeError,
    extract_text,
)
from document_repository import store_document
from embedding_repository import embed_document

SERVICE_NAME = "oracle-ai-vector-search"

# A stopped Autonomous Database leaves the driver's TCP connect blocking
# for minutes, so the health probe is given its own deadline.
DB_CHECK_TIMEOUT_SECONDS = 10

STATUS_PROCESSED = "processed"
STATUS_ALREADY_PROCESSED = "already_processed"

logger = logging.getLogger(__name__)


def _probe_database() -> None:
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT 1 FROM dual")
        cursor.fetchone()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def check_database(timeout: float = DB_CHECK_TIMEOUT_SECONDS) -> bool:
    """Report whether Oracle answers a trivial query within the timeout.

    Never raises: an unreachable database is a health result, not an
    error. The probe runs in its own thread so a blocked TCP connect
    cannot stall the request.
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_probe_database)
        try:
            future.result(timeout=timeout)
            return True
        except FutureTimeoutError:
            logger.warning("Database health probe timed out after %ss", timeout)
            return False
        except Exception:
            logger.exception("Database health probe failed")
            return False
        finally:
            executor.shutdown(wait=False)


def _find_document(file_name: str, content_hash: str) -> int | None:
    """Id of an identical document already stored, if there is one."""
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


def _count_chunks(document_id: int) -> tuple[int, int]:
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


def _extract_from_upload(file_name: str, content: bytes) -> str:
    """Write the upload to a temporary file, extract text, then remove it."""
    suffix = Path(file_name).suffix.lower()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)

    try:
        return extract_text(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)


def ingest_document(file_name: str, content: bytes) -> dict:
    """Run an uploaded file through the existing ingestion pipeline.

    Args:
        file_name: Original name of the uploaded file.
        content: Raw bytes of the upload.

    Returns:
        dict: document_id, file_name, number_of_chunks,
        number_of_embeddings and status.

    Raises:
        UnsupportedFileTypeError: If the extension is not PDF or TXT.
        EmptyDocumentError: If no text could be extracted.
        EmptyTextError: If the extracted text cannot be chunked.
    """
    suffix = Path(file_name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{suffix or file_name}'. "
            f"Supported types: {', '.join(SUPPORTED_EXTENSIONS)}."
        )

    text = _extract_from_upload(file_name, content)
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

    document_id = _find_document(file_name, content_hash)
    if document_id is None:
        document_id = store_document(
            file_name=file_name,
            chunks=chunk_text(text),
            file_type=suffix.lstrip("."),
            content_hash=content_hash,
        )
        status = STATUS_PROCESSED
    else:
        status = STATUS_ALREADY_PROCESSED

    # Fills in any chunk still missing a vector, and is a no-op otherwise.
    embed_document(document_id)
    number_of_embeddings, number_of_chunks = _count_chunks(document_id)

    return {
        "document_id": document_id,
        "file_name": file_name,
        "number_of_chunks": number_of_chunks,
        "number_of_embeddings": number_of_embeddings,
        "status": status,
    }


def answer_question(question: str, top_k: int) -> dict:
    """Answer a question with the existing RAG implementation.

    Retrieval and generation are not reimplemented here; this is a thin
    delegation to rag.answer_question().
    """
    return rag.answer_question(question, top_k=top_k)
