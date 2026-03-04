from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class EmbeddedChunk:
    chunk_id: str
    vector: List[float]
    metadata: Dict[str, Any]