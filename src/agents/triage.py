from pathlib import Path
from uuid import uuid4
import json

from src.models.document_profile import DocumentProfile
from src.models.enums import (
    OriginType,
    LayoutComplexity,
    ExtractionCostTier,
)
from src.utils.pdf_metrics import analyze_pdf_metrics


class TriageAgent:
    def __init__(self):
        pass

    def classify(self, pdf_path: str) -> DocumentProfile:
        metrics = analyze_pdf_metrics(pdf_path)

        avg_chars = metrics["avg_chars_per_page"]
        image_ratio = metrics["image_area_ratio"]

        # ---- Origin Type ----
        if avg_chars < 10 and image_ratio > 0.5:
            origin_type = OriginType.SCANNED_IMAGE
        elif avg_chars > 100 and image_ratio < 0.2:
            origin_type = OriginType.NATIVE_DIGITAL
        else:
            origin_type = OriginType.MIXED

        # ---- Layout Complexity (heuristic v1) ----
        if image_ratio > 0.4:
            layout = LayoutComplexity.FIGURE_HEAVY
        elif avg_chars > 300:
            layout = LayoutComplexity.SINGLE_COLUMN
        else:
            layout = LayoutComplexity.MIXED

        # ---- Cost Tier ----
        if origin_type == OriginType.NATIVE_DIGITAL and layout == LayoutComplexity.SINGLE_COLUMN:
            cost = ExtractionCostTier.FAST_TEXT_SUFFICIENT
        elif origin_type == OriginType.SCANNED_IMAGE:
            cost = ExtractionCostTier.NEEDS_VISION_MODEL
        else:
            cost = ExtractionCostTier.NEEDS_LAYOUT_MODEL

        profile = DocumentProfile(
            document_id=str(uuid4()),
            document_name=Path(pdf_path).name,
            origin_type=origin_type,
            layout_complexity=layout,
            language="en",
            language_confidence=0.9,
            domain_hint=None,
            estimated_extraction_cost=cost,
            avg_chars_per_page=avg_chars,
            image_area_ratio=image_ratio,
        )

        return profile

def save_profile(profile: DocumentProfile, output_dir=".refinery/profiles"):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(output_dir) / f"{profile.document_id}.json"
    out_path.write_text(profile.model_dump_json(indent=2))