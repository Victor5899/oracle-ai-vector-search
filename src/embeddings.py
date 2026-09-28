"""
Embedding generation for the Oracle AI Vector Search project.

Wraps sentence-transformers/all-MiniLM-L6-v2, which produces the
384-dimensional vectors expected by the DOCUMENT_CHUNKS.EMBEDDING column.
The model is loaded once and reused across calls.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Load the embedding model, reusing it on every later call."""
    return SentenceTransformer(MODEL_NAME)


def _validate(vectors: list[list[float]]) -> list[list[float]]:
    """Ensure every vector matches the column's fixed dimension."""
    for index, vector in enumerate(vectors):
        if len(vector) != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Embedding {index} has dimension {len(vector)}, "
                f"expected {EMBEDDING_DIMENSION}."
            )
    return vectors


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for several texts, in the order given.

    Args:
        texts: Non-empty texts to embed.

    Returns:
        list[list[float]]: One 384-dimensional vector per input text.

    Raises:
        ValueError: If texts is empty, any text is blank, or a returned
            vector does not have exactly 384 dimensions.
    """
    if not texts:
        raise ValueError("No texts provided to embed.")
    if any(not text or not text.strip() for text in texts):
        raise ValueError("Cannot embed empty or whitespace-only text.")

    vectors = get_model().encode(texts)

    return _validate([[float(value) for value in vector] for vector in vectors])


def embed_text(text: str) -> list[float]:
    """Generate a single 384-dimensional embedding for one text.

    Args:
        text: Non-empty text to embed.

    Returns:
        list[float]: The text's embedding.

    Raises:
        ValueError: If text is blank or the vector is not 384-dimensional.
    """
    return embed_texts([text])[0]
