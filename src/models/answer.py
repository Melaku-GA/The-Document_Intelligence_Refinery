from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Citation:
    chunk_id: str
    page: int
    confidence: float


@dataclass
class ProvenanceInfo:
    """Extended provenance with full source information."""
    document_name: str
    page_number: int
    bbox: Optional[Tuple[float, float, float, float]] = None
    section_title: Optional[str] = None
    chunk_id: Optional[str] = None


@dataclass
class Answer:
    text: str
    answer_confidence: float
    citations: List[Citation] = field(default_factory=list)
    provenance: List[ProvenanceInfo] = field(default_factory=list)