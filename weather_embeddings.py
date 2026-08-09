from sentence_transformers import SentenceTransformer

def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 100,
) -> list[str]:
    """
    Split text into overlapping chunks.

    Example:
        chunk 1 = characters 0-799
        chunk 2 = characters 700-1499

    The 100-character overlap helps preserve context
    across chunk boundaries.
    """

    if not text:
        return []

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size"
        )

    # Normalize excessive whitespace
    text = " ".join(text.split())

    chunks = []

    start = 0

    while start < len(text):
        end = min(
            start + chunk_size,
            len(text),
        )

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        # We reached the end of the document
        if end == len(text):
            break

        start = end - overlap

    return chunks





MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None


def get_embedding_model():
    """
    Load the embedding model once and reuse it.
    """

    global _model

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def generate_embedding(text: str) -> list[float]:
    """
    Convert text into a 384-dimensional vector.
    """

    if not text:
        raise ValueError("text cannot be empty")

    model = get_embedding_model()

    embedding = model.encode(text)

    return embedding.tolist()



def build_embeddings_for_documents(
    documents: list[dict],
) -> list[dict]:
    """
    Chunk each weather document and generate embeddings
    for every chunk.
    """

    records = []

    for document in documents:
        chunks = chunk_text(
            document["narrative_text"]
        )

        for chunk_index, chunk in enumerate(chunks):
            embedding = generate_embedding(chunk)

            records.append(
                {
                    "id": (
                        f"{document['id']}_chunk_{chunk_index}"
                    ),
                    "document_id": document["id"],
                    "chunk_index": chunk_index,
                    "chunk_text": chunk,
                    "embedding": embedding,
                    "model_name": MODEL_NAME,
                }
            )

    return records