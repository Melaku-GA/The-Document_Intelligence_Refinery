from abc import ABC, abstractmethod
from src.models.extracted_document import ExtractedDocument


from dataclasses import dataclass
from typing import List


class ExtractionResult:
    def __init__(self, document: ExtractedDocument, confidence: float, cost_estimate: float):
        self.document = document
        self.confidence = confidence
        self.cost_estimate = cost_estimate


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, pdf_path: str) -> ExtractionResult:
        pass
@dataclass
class TextBlock:
    text: str
    page: int
    bbox: list | None
    confidence: float


@dataclass
class ExtractedDocument:
    text_blocks: List[TextBlock]


@dataclass
class ExtractionResult:
    document: ExtractedDocument
    confidence: float
    cost_estimate: float