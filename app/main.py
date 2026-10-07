"""
FastAPI routes for the Oracle AI Vector Search project.

Routes stay thin: they validate input, call app.service, and translate
application errors into HTTP responses. Failure logs name the exception
type only. Credential values, wallet passwords and stack traces are not
written to the log or returned to the client.
"""

import logging
import os
from types import ModuleType

import oracledb
import rag
from chunker import EmptyTextError
from document_processor import EmptyDocumentError, UnsupportedFileTypeError
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import schemas, service

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Oracle AI Vector Search - Smart Document Q&A",
    description="Document ingestion and semantic question answering.",
    version="0.8.0",
)


def allowed_origins(raw: str | None = None) -> list[str]:
    """Browser origins permitted to call this API.

    CORS_ORIGINS is a comma-separated list of exact origins, for example
    the Vercel site. A wildcard is discarded so the API never allows
    every origin. Local Vite development does not need this: the dev
    server proxies /api and the browser stays same-origin.
    """
    if raw is None:
        raw = os.getenv("CORS_ORIGINS", "")

    origins: list[str] = []
    seen: set[str] = set()
    for part in raw.split(","):
        origin = part.strip().rstrip("/")
        if not origin or origin == "*":
            continue
        if origin not in seen:
            seen.add(origin)
            origins.append(origin)
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)


def get_service() -> ModuleType:
    """Provide the service layer, so tests can substitute a fake one."""
    return service


def _error(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


@app.exception_handler(UnsupportedFileTypeError)
def _handle_unsupported_file_type(request: Request, error: Exception) -> JSONResponse:
    return _error(400, str(error))


@app.exception_handler(EmptyDocumentError)
def _handle_empty_document(request: Request, error: Exception) -> JSONResponse:
    return _error(400, str(error))


@app.exception_handler(EmptyTextError)
def _handle_empty_text(request: Request, error: Exception) -> JSONResponse:
    return _error(400, str(error))


@app.exception_handler(ValueError)
def _handle_value_error(request: Request, error: Exception) -> JSONResponse:
    return _error(400, str(error))


@app.exception_handler(rag.NoRelevantChunksError)
def _handle_no_chunks(request: Request, error: Exception) -> JSONResponse:
    return _error(404, str(error))


@app.exception_handler(rag.MissingConfigurationError)
def _handle_missing_configuration(request: Request, error: Exception) -> JSONResponse:
    logger.error("Answer generation is not configured (%s)", type(error).__name__)
    return _error(503, "Answer generation is not configured on the server.")


@app.exception_handler(rag.LLMError)
def _handle_llm_error(request: Request, error: Exception) -> JSONResponse:
    logger.error("Language model request failed (%s)", type(error).__name__)
    return _error(502, "The language model could not be reached.")


@app.exception_handler(oracledb.Error)
def _handle_database_error(request: Request, error: Exception) -> JSONResponse:
    logger.error("Database operation failed (%s)", type(error).__name__)
    return _error(503, "The database is currently unavailable.")


@app.exception_handler(rag.RagError)
def _handle_rag_error(request: Request, error: Exception) -> JSONResponse:
    logger.error("Question answering failed (%s)", type(error).__name__)
    return _error(500, "The question could not be answered.")


@app.get("/health", response_model=schemas.HealthResponse)
def health(svc: ModuleType = Depends(get_service)) -> schemas.HealthResponse:
    """Report service liveness and whether Oracle is reachable."""
    connected = svc.check_database()

    return schemas.HealthResponse(
        status="ok" if connected else "degraded",
        service=service.SERVICE_NAME,
        database="connected" if connected else "unavailable",
    )


@app.post("/documents/upload", response_model=schemas.UploadResponse)
def upload_document(
    file: UploadFile = File(...),
    svc: ModuleType = Depends(get_service),
) -> schemas.UploadResponse:
    """Ingest a PDF or TXT upload through the existing pipeline."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="A file name is required.")

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    result = svc.ingest_document(file.filename, content)

    return schemas.UploadResponse(**result)


@app.post("/query", response_model=schemas.QueryResponse)
def query(
    payload: schemas.QueryRequest,
    svc: ModuleType = Depends(get_service),
) -> schemas.QueryResponse:
    """Answer a question from the stored documents and cite its sources."""
    result = svc.answer_question(payload.question, payload.top_k)

    return schemas.QueryResponse(**result)
