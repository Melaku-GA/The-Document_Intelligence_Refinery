from pydantic import BaseModel, Field
from typing import Optional
from .enums import OriginType, LayoutComplexity, ExtractionCostTier

class DocumentProfile(BaseModel):
    document_id: str
    document_name: str
    
    # Additional fields for classification and processing
    page_count: int = Field(default=0, description="Total number of pages")
    is_native_digital: bool = Field(default=True, description="Whether document is native digital")
    has_tables: bool = Field(default=False, description="Whether document contains tables")
    has_images: bool = Field(default=False, description="Whether document contains images")
    actual_class: Optional[str] = Field(default=None, description="Expected document class (A, B, C, D)")
    
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