import pdfplumber
from pathlib import Path

from src.strategies.base import BaseExtractor, ExtractionResult
from src.models.extracted_document import ExtractedDocument, TextBlock
from src.models.provenance import PageRef, BoundingBox


class FastTextExtractor(BaseExtractor):
    def extract(self, pdf_path: str) -> ExtractionResult:
        text_blocks = []
        total_chars = 0
        pages = 0

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                pages += 1
                words = page.extract_words(use_text_flow=True)

                for i, w in enumerate(words):
                    bbox = BoundingBox(
                        x0=w["x0"],
                        y0=w["top"],
                        x1=w["x1"],
                        y1=w["bottom"],
                    )

                    page_ref = PageRef(
                        page_number=page_num,
                        bbox=bbox
                    )

                    text_blocks.append(
                        TextBlock(
                            text=w["text"],
                            page_ref=page_ref,
                            reading_order=i
                        )
                    )

                    total_chars += len(w["text"])

        avg_chars = total_chars / max(pages, 1)

        confidence = self._confidence_score(avg_chars, len(text_blocks))
        cost_estimate = pages * 0.0001  # symbolic cost

        extracted = ExtractedDocument(
            document_name=Path(pdf_path).name,
            text_blocks=text_blocks,
            tables=[],
            figures=[]
        )

        return ExtractionResult(
            document=extracted,
            confidence=confidence,
            cost_estimate=cost_estimate
        )

    def _confidence_score(self, avg_chars: float, block_count: int) -> float:
        score = 0.0

        if avg_chars > 100:
            score += 0.6
        if block_count > 200:
            score += 0.4

        return min(score, 1.0)