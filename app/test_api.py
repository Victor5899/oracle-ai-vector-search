"""
Tests for the REST API.

The API tests run without Oracle or OpenAI: the service layer or the RAG
entry point is substituted so only routing, validation, delegation and
error mapping are exercised. The live integration tests at the bottom hit
the real database and model and are skipped unless RUN_LIVE_TESTS=1.

Run: python -m pytest app/test_api.py -v
"""

import os
from pathlib import Path
from types import SimpleNamespace

import pytest
import rag
from fastapi.testclient import TestClient

from app import service
from app.main import app, get_service

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PATH = PROJECT_ROOT / "data" / "documents" / "sample.txt"

LIVE_TESTS_ENABLED = os.getenv("RUN_LIVE_TESTS") == "1"
live = pytest.mark.skipif(
    not LIVE_TESTS_ENABLED,
    reason="set RUN_LIVE_TESTS=1 to run against Oracle and OpenAI",
)

QUESTION = "What distance metric does this project use for vector similarity?"

FAKE_ANSWER = {
    "question": QUESTION,
    "answer": "The project uses cosine distance.",
    "sources": [
        {
            "chunk_id": 54,
            "document_id": 24,
            "chunk_index": 1,
            "chunk_text": "This project uses cosine distance.",
            "distance": 0.4579,
        }
    ],
}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _use_fake_service(**attributes) -> None:
    fake = SimpleNamespace(**attributes)
    app.dependency_overrides[get_service] = lambda: fake


def test_health_reports_ok_when_database_is_reachable(client):
    _use_fake_service(check_database=lambda: True)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "oracle-ai-vector-search",
        "database": "connected",
    }


def test_health_reports_degraded_when_database_is_unreachable(client):
    _use_fake_service(check_database=lambda: False)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "unavailable"


@pytest.mark.parametrize(
    "payload",
    [
        {"question": "", "top_k": 3},
        {"question": "   ", "top_k": 3},
        {"top_k": 3},
    ],
)
def test_query_rejects_an_empty_question(client, payload):
    _use_fake_service(answer_question=lambda *args, **kwargs: FAKE_ANSWER)

    response = client.post("/query", json=payload)

    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.parametrize("top_k", [0, -1, 999])
def test_query_rejects_unreasonable_top_k(client, top_k):
    _use_fake_service(answer_question=lambda *args, **kwargs: FAKE_ANSWER)

    response = client.post("/query", json={"question": QUESTION, "top_k": top_k})

    assert response.status_code == 422


def test_query_uses_the_existing_rag_implementation(client, monkeypatch):
    """The route must delegate to rag.answer_question, not re-implement it."""
    calls = []

    def fake_answer_question(question, top_k=rag.DEFAULT_TOP_K):
        calls.append((question, top_k))
        return FAKE_ANSWER

    monkeypatch.setattr(rag, "answer_question", fake_answer_question)

    response = client.post("/query", json={"question": QUESTION, "top_k": 3})

    assert response.status_code == 200
    assert calls == [(QUESTION, 3)], "rag.answer_question was not called once"


def test_query_response_contains_answer_and_sources(client, monkeypatch):
    monkeypatch.setattr(rag, "answer_question", lambda *a, **kw: FAKE_ANSWER)

    body = client.post("/query", json={"question": QUESTION, "top_k": 3}).json()

    assert body["question"] == QUESTION
    assert body["answer"] == FAKE_ANSWER["answer"]
    assert body["sources"], "no sources were returned"
    for source in body["sources"]:
        assert set(source) == {"chunk_id", "document_id", "chunk_index", "distance"}


def test_query_reports_when_no_chunks_match(client):
    def raise_no_chunks(question, top_k):
        raise rag.NoRelevantChunksError("No relevant chunks were found.")

    _use_fake_service(answer_question=raise_no_chunks)

    response = client.post("/query", json={"question": QUESTION})

    assert response.status_code == 404
    assert "No relevant chunks" in response.json()["detail"]


def test_upload_rejects_an_unsupported_file_type(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("notes.md", b"# not supported", "text/markdown")},
    )

    assert response.status_code == 400
    assert ".md" in response.json()["detail"]


def test_upload_rejects_an_empty_file(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_uses_the_existing_pipeline(client, monkeypatch):
    """Every pipeline stage from Phases 1-5 must be used, in order."""
    calls = []

    def fake_extract_text(path):
        calls.append("extract_text")
        assert Path(path).suffix == ".txt", "temp file keeps the real extension"
        assert Path(path).read_bytes() == b"uploaded text", "upload not written"
        return "uploaded text"

    def fake_chunk_text(text):
        calls.append("chunk_text")
        return [text]

    def fake_store_document(**kwargs):
        calls.append("store_document")
        assert kwargs["file_name"] == "upload.txt"
        assert kwargs["chunks"] == ["uploaded text"]
        assert len(kwargs["content_hash"]) == 64, "content hash is stored"
        return 99

    def fake_embed_document(document_id):
        calls.append("embed_document")
        assert document_id == 99
        return 1

    monkeypatch.setattr(service, "extract_text", fake_extract_text)
    monkeypatch.setattr(service, "chunk_text", fake_chunk_text)
    monkeypatch.setattr(service, "store_document", fake_store_document)
    monkeypatch.setattr(service, "embed_document", fake_embed_document)
    monkeypatch.setattr(service, "_find_document", lambda name, digest: None)
    monkeypatch.setattr(service, "_count_chunks", lambda document_id: (1, 1))

    response = client.post(
        "/documents/upload",
        files={"file": ("upload.txt", b"uploaded text", "text/plain")},
    )

    assert response.status_code == 200
    assert calls == [
        "extract_text",
        "chunk_text",
        "store_document",
        "embed_document",
    ], f"pipeline stages were skipped or reordered: {calls}"
    assert response.json() == {
        "document_id": 99,
        "file_name": "upload.txt",
        "number_of_chunks": 1,
        "number_of_embeddings": 1,
        "status": "processed",
    }


def test_upload_reuses_a_document_with_the_same_content_hash(client, monkeypatch):
    monkeypatch.setattr(service, "extract_text", lambda path: "uploaded text")
    monkeypatch.setattr(service, "_find_document", lambda name, digest: 42)
    monkeypatch.setattr(service, "_count_chunks", lambda document_id: (3, 3))
    monkeypatch.setattr(service, "embed_document", lambda document_id: 0)
    monkeypatch.setattr(
        service,
        "store_document",
        lambda **kwargs: pytest.fail("a duplicate document was stored"),
    )

    response = client.post(
        "/documents/upload",
        files={"file": ("sample.txt", b"uploaded text", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["document_id"] == 42
    assert response.json()["status"] == "already_processed"


# --------------------------------------------------------------------------
# Live integration tests: real Oracle database and real OpenAI model.
# Enable with: RUN_LIVE_TESTS=1 python -m pytest app/test_api.py -v
# --------------------------------------------------------------------------


def _count_documents(file_name: str) -> int:
    from database import get_connection

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM documents WHERE file_name = :file_name",
            {"file_name": file_name},
        )
        return int(cursor.fetchone()[0])
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


@live
def test_live_health_reports_a_connected_database(client):
    body = client.get("/health").json()

    assert body["database"] == "connected"
    assert body["status"] == "ok"


@live
def test_live_upload_does_not_duplicate_the_sample_document(client):
    assert SAMPLE_PATH.is_file(), f"missing sample document: {SAMPLE_PATH}"

    response = client.post(
        "/documents/upload",
        files={"file": (SAMPLE_PATH.name, SAMPLE_PATH.read_bytes(), "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["number_of_chunks"] > 0
    assert body["number_of_embeddings"] == body["number_of_chunks"]
    assert _count_documents(SAMPLE_PATH.name) == 1, "the sample was duplicated"


@live
def test_live_query_answers_from_the_sample_document(client):
    response = client.post("/query", json={"question": QUESTION, "top_k": 3})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"].strip(), "the model returned an empty answer"
    assert body["sources"], "no sources were returned"
    for source in body["sources"]:
        assert source["distance"] >= 0
