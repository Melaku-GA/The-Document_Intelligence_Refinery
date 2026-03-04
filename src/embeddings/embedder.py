from typing import List
from src.models.chunk import DocumentChunk
from src.models.embedding import EmbeddedChunk
import random


class Embedder:
    """
    Abstract embedder interface.
    """

    def embed(self, chunks: List[DocumentChunk]) -> List[EmbeddedChunk]:
        raise NotImplementedError
    
    def embed_query(self, query: str) -> List[float]:
        """Embed a query string for retrieval."""
        raise NotImplementedError


class DummyEmbedder(Embedder):
    """
    Deterministic dummy embedder for pipeline testing.
    Replace with real model later.
    """

    def embed(self, chunks: List[DocumentChunk]) -> List[EmbeddedChunk]:
        embedded = []

        for c in chunks:
            vector = [random.random() for _ in range(384)]

            embedded.append(
                EmbeddedChunk(
                    chunk_id=c.chunk_id,
                    vector=vector,
                    metadata={
                        "page": c.page,
                        "bbox": c.bbox,
                        "confidence": c.confidence,
                        "text": c.text,
                    },
                )
            )

        return embedded
    
    def embed_query(self, query: str) -> List[float]:
        """Embed a query string using deterministic seed based on query."""
        # Use hash to create a deterministic but varied vector
        seed = hash(query) % (2**32)
        random.seed(seed)
        vector = [random.random() for _ in range(384)]
        random.seed()  # Reset seed
        return vector
