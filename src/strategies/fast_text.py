import pdfplumber
import time
from pathlib import Path
from typing import List, Dict, Any

from src.strategies.base import BaseExtractor, ExtractionResult
from src.models.extracted_document import ExtractedDocument, TextBlock
from src.models.provenance import PageRef, BoundingBox


class FastTextExtractor(BaseExtractor):
    """
    Fast text extraction strategy using pdfplumber.
    Includes confidence scoring based on multiple metrics.
    """

    def extract(self, pdf_path: str) -> ExtractionResult:
        start_time = time.time()
        text_blocks: List[TextBlock] = []
        total_chars = 0
        pages = 0
        image_area = 0.0
        page_area = 0.0
        font_sizes: List[float] = []

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                pages += 1

                # Track page area
                page_area += page.width * page.height

                # Track images
                for img in page.images:
                    image_area += img.get("width", 0) * img.get("height", 0)

                # Extract words with font metadata
                words = page.extract_words(use_text_flow=True)

                for i, w in enumerate(words):
                    # Collect font size for metadata analysis
                    if "size" in w:
                        font_sizes.append(w["size"])

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

        # Calculate metrics
        avg_chars = total_chars / max(pages, 1)
        image_ratio = image_area / max(page_area, 1)
        char_density = total_chars / max(page_area, 1) * 1000  # chars per 1000 points

        # Calculate confidence score
        confidence = self._confidence_score(
            avg_chars=avg_chars,
            block_count=len(text_blocks),
            image_ratio=image_ratio,
            char_density=char_density,
            font_sizes=font_sizes
        )

        # Cost: symbolic based on pages processed
        cost_estimate = pages * 0.0001

        extracted = ExtractedDocument(
            document_name=Path(pdf_path).name,
            text_blocks=text_blocks,
            tables=[],
            figures=[]
        )

        processing_time = time.time() - start_time

        result = ExtractionResult(
            document=extracted,
            confidence=confidence,
            cost_estimate=cost_estimate
        )

        # Attach processing time for ledger
        result.processing_time = processing_time

        return result

    def _confidence_score(
        self,
        avg_chars: float,
        block_count: int,
        image_ratio: float,
        char_density: float,
        font_sizes: List[float]
    ) -> float:
        """
        Calculate confidence score based on multiple metrics:
        - Character count (avg_chars)
        - Character density (chars per page area)
        - Image-to-page area ratio
        - Font metadata consistency
        """
        score = 0.0
        details = {}

        # 1. Character count scoring (max 0.3)
        if avg_chars > 500:
            score += 0.3
            details["chars_score"] = 0.3
        elif avg_chars > 200:
            score += 0.2
            details["chars_score"] = 0.2
        elif avg_chars > 50:
            score += 0.1
            details["chars_score"] = 0.1
        else:
            details["chars_score"] = 0.0

        # 2. Block count scoring (max 0.2)
        if block_count > 500:
            score += 0.2
            details["block_score"] = 0.2
        elif block_count > 200:
            score += 0.15
            details["block_score"] = 0.15
        elif block_count > 50:
            score += 0.1
            details["block_score"] = 0.1
        else:
            details["block_score"] = 0.0

        # 3. Character density scoring (max 0.2)
        # Good text density indicates searchable text
        if char_density > 5.0:
            score += 0.2
            details["density_score"] = 0.2
        elif char_density > 2.0:
            score += 0.15
            details["density_score"] = 0.15
        elif char_density > 0.5:
            score += 0.1
            details["density_score"] = 0.1
        else:
            details["density_score"] = 0.0

        # 4. Image ratio scoring (max 0.15)
        # High image ratio suggests scanned document - lower confidence
        if image_ratio < 0.1:
            score += 0.15  # Clean text-based PDF
            details["image_score"] = 0.15
        elif image_ratio < 0.3:
            score += 0.1
            details["image_score"] = 0.1
        elif image_ratio < 0.5:
            score += 0.05
            details["image_score"] = 0.05
        else:
            details["image_score"] = 0.0  # Likely scanned

        # 5. Font metadata scoring (max 0.15)
        # Consistent font sizes indicate proper text extraction
        if font_sizes:
            unique_sizes = len(set(font_sizes))
            avg_size = sum(font_sizes) / len(font_sizes)
            
            # Most documents have 2-5 font sizes
            if 1 <= unique_sizes <= 8 and avg_size > 5:
                score += 0.15
                details["font_score"] = 0.15
            elif unique_sizes <= 10:
                score += 0.1
                details["font_score"] = 0.1
            else:
                score += 0.05
                details["font_score"] = 0.05
        else:
            details["font_score"] = 0.0

        # Store details for debugging
        self._last_confidence_details = details

        return min(score, 1.0)

    def get_confidence_details(self) -> Dict[str, float]:
        """Return the last confidence calculation details."""
        return getattr(self, "_last_confidence_details", {})
