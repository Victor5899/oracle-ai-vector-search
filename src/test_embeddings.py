"""
Tests for the embedding model wrapper.

Loads the model, embeds two different sentences, and checks the output
dimension and that the vectors differ. Run: python src/test_embeddings.py
"""

from embeddings import EMBEDDING_DIMENSION, embed_text, embed_texts, get_model

SENTENCES = [
    "Oracle AI Vector Search finds documents by meaning, not keywords.",
    "The cat slept on the warm windowsill all afternoon.",
]


def main() -> None:
    model = get_model()
    assert model is get_model(), "model should be loaded once and reused"
    print("PASS model loaded")

    first, second = embed_texts(SENTENCES)
    assert len(first) == EMBEDDING_DIMENSION, "first embedding is the wrong size"
    assert len(second) == EMBEDDING_DIMENSION, "second embedding is the wrong size"
    print(f"PASS both embeddings have dimension {EMBEDDING_DIMENSION}")

    assert first != second, "different sentences produced identical embeddings"
    print("PASS embeddings differ for different sentences")

    single = embed_text(SENTENCES[0])
    assert len(single) == EMBEDDING_DIMENSION, "single embedding is the wrong size"
    print("PASS single-text embedding has dimension 384")

    print("All checks passed")


if __name__ == "__main__":
    main()
