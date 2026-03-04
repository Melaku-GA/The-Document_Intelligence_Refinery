from src.strategies.base import (
    TextBlock,
    ExtractedDocument,
    ExtractionResult,
)
from src.models.enums import ExtractionCostTier


class MinerULayoutExtractor:
    """
    Layout-aware extractor for scanned and mixed PDFs.
    """

    def extract(self, pdf_path: str) -> ExtractionResult:
        """
        Simulated MinerU integration.
        Replace internals with actual MinerU pipeline later.
        """

        # ---- Placeholder for MinerU output ----
        # Pretend MinerU returns structured blocks per page
        mineru_output = [
            {
                "text": "Invoice Number: INV-2024-001",
                "page": 1,
                "bbox": [50, 100, 400, 140],
                "confidence": 0.92,
            },
            {
                "text": "Total Amount: $1,240.00",
                "page": 1,
                "bbox": [50, 600, 400, 640],
                "confidence": 0.89,
            },
        ]

        text_blocks = [
            TextBlock(
                text=b["text"],
                page=b["page"],
                bbox=b["bbox"],
                confidence=b["confidence"],
            )
            for b in mineru_output
        ]

        doc_confidence = sum(b.confidence for b in text_blocks) / len(text_blocks)

        return ExtractionResult(
            document=ExtractedDocument(text_blocks=text_blocks),
            confidence=doc_confidence,
            cost_estimate=ExtractionCostTier.LAYOUT_AWARE.value,
        )