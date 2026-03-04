from typing import List, Tuple
from src.models.embedding import EmbeddedChunk
from src.embeddings.embedder import Embedder
import math


class InMemoryVectorStore:
    def __init__(self):
        self.vectors: List[EmbeddedChunk] = []

    def add(self, embedded_chunks: List[EmbeddedChunk]):
        self.vectors.extend(embedded_chunks)

    def __len__(self):
        return len(self.vectors)

    def retrieve(
        self,
        query: str,
        embedder: Embedder,
        top_k: int = 5,
    ) -> List[Tuple[float, float, float, EmbeddedChunk]]:
        """
        Retrieve the most similar chunks for a query.
        
        Args:
            query: The query string
            embedder: The embedder to use for encoding the query
            top_k: Number of results to return
            
        Returns:
            List of tuples: (final_score, similarity, confidence, EmbeddedChunk)
            - final_score: Combined score (similarity * confidence)
            - similarity: Cosine similarity between query and chunk
            - confidence: Confidence score from the chunk metadata
            - EmbeddedChunk: The embedded chunk
        """
        if not self.vectors:
            return []
        
        # Embed the query
        query_vector = embedder.embed_query(query)
        
        # Calculate similarities
        results = []
        for chunk in self.vectors:
            similarity = self._cosine_similarity(query_vector, chunk.vector)
            confidence = chunk.metadata.get("confidence", 1.0)
            final_score = similarity * confidence
            
            results.append((final_score, similarity, confidence, chunk))
        
        # Sort by final score descending and return top_k
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:top_k]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
