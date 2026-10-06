"""Request and response models for the REST API."""

from pydantic import BaseModel, Field, field_validator

MAX_TOP_K = 20
DEFAULT_TOP_K = 3


class HealthResponse(BaseModel):
    """Liveness information, including Oracle reachability."""

    status: str
    service: str
    database: str


class UploadResponse(BaseModel):
    """Result of running an uploaded file through the pipeline."""

    document_id: int
    file_name: str
    number_of_chunks: int
    number_of_embeddings: int
    status: str


class QueryRequest(BaseModel):
    """A natural-language question and how many chunks to retrieve."""

    question: str = Field(min_length=1)
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=MAX_TOP_K)

    @field_validator("question")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be empty")
        return value.strip()


class Source(BaseModel):
    """One retrieved chunk that supported the answer."""

    chunk_id: int
    document_id: int
    chunk_index: int
    distance: float


class QueryResponse(BaseModel):
    """A generated answer together with the chunks it came from."""

    question: str
    answer: str
    sources: list[Source]
