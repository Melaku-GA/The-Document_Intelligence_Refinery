from pydantic import BaseModel, Field
from typing import Optional
from .enums import OriginType, LayoutComplexity, ExtractionCostTier

class DocumentProfile(BaseModel):
    document_id: str
    document_name: str

    origin_type: OriginType
    layout_complexity: LayoutComplexity

    language: str = Field(..., description="ISO language code")
    language_confidence: float = Field(..., ge=0.0, le=1.0)

    domain_hint: Optional[str] = Field(
        default=None,
        description="financial | legal | technical | medical | general"
    )

    estimated_extraction_cost: ExtractionCostTier

    avg_chars_per_page: float
    image_area_ratio: float

    notes: Optional[str] = None