from typing import List, Tuple
from src.models.answer import Answer, Citation


class GroundedAnswerGenerator:
    def __init__(self, min_confidence: float = 0.5):
        self.min_confidence = min_confidence

    def generate(
        self,
        query: str,
        retrieved: List[Tuple[float, float, float, object]],
    ) -> Answer:
        """
        retrieved: (final_score, similarity, confidence, EmbeddedChunk)
        """

        if not retrieved:
            return self._abstain("No relevant information found.")

        # Filter low-confidence chunks
        valid = [r for r in retrieved if r[2] >= self.min_confidence]

        if not valid:
            return self._abstain("Relevant information is too unreliable.")

        # Simple extractive answer (FDE-safe)
        best = valid[0]
        chunk = best[3]

        answer_text = self._extract_answer_text(query, chunk.metadata["text"])

        citations = [
            Citation(
                chunk_id=chunk.chunk_id,
                page=chunk.metadata.get("page", -1),
                confidence=chunk.metadata.get("confidence", 1.0),
            )
        ]

        answer_confidence = min(1.0, best[0])

        return Answer(
            text=answer_text,
            citations=citations,
            answer_confidence=answer_confidence,
        )

    def _extract_answer_text(self, query: str, text: str) -> str:
        """
        Placeholder extractive logic.
        Replace with LLM prompt later.
        """
        return text.strip()

    def _abstain(self, reason: str) -> Answer:
        return Answer(
            text=f"I cannot answer confidently: {reason}",
            citations=[],
            answer_confidence=0.0,
        )