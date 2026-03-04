from dataclasses import dataclass
from typing import Optional


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    page: int
    bbox: Optional[list]
    confidence: float