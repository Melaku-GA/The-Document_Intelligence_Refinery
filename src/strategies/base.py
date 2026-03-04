from abc import ABC, abstractmethod
from src.models.extracted_document import ExtractedDocument

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ExtractionResult:
    """Result from any extraction strategy."""
    document: ExtractedDocument
    confidence: float
    cost_estimate: float
    processing_time: Optional[float] = 0.0
    strategy_used: Optional[str] = "fast_text"
    extraction_time: Optional[float] = 0.0


class BaseExtractor(ABC):
    """Base class for all extraction strategies."""
    
    @abstractmethod
    def extract(self, pdf_path: str) -> ExtractionResult:
        """Extract content from PDF using this strategy."""
        pass


@dataclass
class TextBlock:
    """Legacy compatibility - text block with location."""
    text: str
    page: int
    bbox: list | None
    confidence: float


@dataclass
class ExtractedDocument:
    """Legacy compatibility - extracted document container."""
    text_blocks: List[TextBlock]
