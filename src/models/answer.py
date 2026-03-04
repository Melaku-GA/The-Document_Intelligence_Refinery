from dataclasses import dataclass
from typing import List


@dataclass
class Citation:
    chunk_id: str
    page: int
    confidence: float


@dataclass
class Answer:
    text: str
    citations: List[Citation]
    answer_confidence: float