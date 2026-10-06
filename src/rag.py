"""
Retrieval-augmented answer generation.

Retrieves the most relevant chunks with retriever.search(), builds a
context from them, and asks an OpenAI model to answer using only that
context. Retrieval and generation stay in separate functions so either
side can be used or tested on its own.

Configuration comes from the project's .env file:
    OPENAI_API_KEY  - API key for the OpenAI SDK
    OPENAI_MODEL    - Model name used for answer generation
"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from retriever import search

# Load variables from the .env file in the project root, regardless of
# the current working directory the script is invoked from.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")

DEFAULT_TOP_K = 5
NOT_FOUND_MESSAGE = "The information was not found in the provided documents."

SYSTEM_PROMPT = (
    "You answer questions about a document collection. "
    "Use only the information in the supplied context. "
    "Never invent, assume, or add facts from outside the context. "
    "If the context does not contain the answer, reply exactly: "
    f"{NOT_FOUND_MESSAGE} "
    "Keep the answer concise."
)


class RagError(Exception):
    """Base class for retrieval-augmented generation failures."""


class MissingConfigurationError(RagError):
    """Raised when a required .env setting is missing."""


class NoRelevantChunksError(RagError):
    """Raised when retrieval finds nothing to answer from."""


class LLMError(RagError):
    """Raised when the OpenAI API call fails."""


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise MissingConfigurationError(
            f"Missing required environment variable {name}. "
            "Add it to your .env file."
        )
    return value.strip()


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    """Create the OpenAI client once and reuse it.

    Raises:
        MissingConfigurationError: If OPENAI_API_KEY is not set.
    """
    return OpenAI(api_key=_require_env("OPENAI_API_KEY"))


def get_model_name() -> str:
    """Read the model name from the environment.

    Raises:
        MissingConfigurationError: If OPENAI_MODEL is not set.
    """
    return _require_env("OPENAI_MODEL")


def retrieve_context(question: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """Retrieve the chunks most relevant to a question.

    Args:
        question: The user's natural-language question.
        top_k: Maximum number of chunks to retrieve.

    Returns:
        list[dict]: Retrieved chunks, nearest first, as returned by
        retriever.search().

    Raises:
        ValueError: If the question is blank.
        NoRelevantChunksError: If no embedded chunk matched.
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    sources = search(question, top_k=top_k)
    if not sources:
        raise NoRelevantChunksError(
            "No relevant chunks were found. Store and embed a document "
            "before asking questions."
        )

    return sources


def build_context(sources: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block."""
    return "\n\n".join(
        f"[{position}] (document {source['document_id']}, "
        f"chunk {source['chunk_index']})\n{source['chunk_text']}"
        for position, source in enumerate(sources, start=1)
    )


def build_messages(question: str, context: str) -> list[dict]:
    """Build the chat messages sent to the model.

    The user message carries the retrieved context and the question, and
    nothing else, so the model cannot draw on unretrieved text.
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {question}",
        },
    ]


def generate_answer(question: str, sources: list[dict]) -> str:
    """Ask the model to answer the question from the retrieved chunks.

    Args:
        question: The user's natural-language question.
        sources: Chunks returned by retrieve_context().

    Returns:
        str: The model's answer.

    Raises:
        ValueError: If the question is blank or sources is empty.
        MissingConfigurationError: If OPENAI_API_KEY or OPENAI_MODEL is unset.
        LLMError: If the API call fails or returns an empty answer.
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")
    if not sources:
        raise ValueError("Cannot generate an answer without retrieved context.")

    messages = build_messages(question, build_context(sources))

    try:
        response = get_client().chat.completions.create(
            model=get_model_name(),
            messages=messages,
        )
    except OpenAIError as error:
        raise LLMError(f"OpenAI request failed: {error}") from error

    answer = (response.choices[0].message.content or "").strip()
    if not answer:
        raise LLMError("The model returned an empty answer.")

    return answer


def answer_question(question: str, top_k: int = DEFAULT_TOP_K) -> dict:
    """Answer a question from stored documents and report its sources.

    Args:
        question: The user's natural-language question.
        top_k: Maximum number of chunks to retrieve as context.

    Returns:
        dict: The question, the generated answer, and the sources used,
        each with chunk_id, document_id, chunk_index, chunk_text and
        distance.
    """
    sources = retrieve_context(question, top_k=top_k)
    answer = generate_answer(question, sources)

    return {
        "question": question,
        "answer": answer,
        "sources": sources,
    }
