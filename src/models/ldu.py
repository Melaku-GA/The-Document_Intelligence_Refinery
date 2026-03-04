from pydantic import BaseModel, field_validator
from typing import List, Optional
from enum import Enum
from .provenance import PageRef, BoundingBox
from .enums import ChunkType

class LDUType(str, Enum):
    """Layout Detection Unit Types."""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    FIGURE = "figure"
    LIST = "list"
    CAPTION = "caption"


class LDU(BaseModel):
    ldu_type: LDUType
    content: str
    chunk_type: ChunkType
    page: int

    page_refs: List[PageRef]
    parent_section: Optional[str]
    bounding_box: Optional[BoundingBox] = None
    
    # Relationships
    cross_references: List[str] = []

    token_count: int
    content_hash: str
    
    @field_validator('page')
    @classmethod
    def page_must_be_positive(cls, v):
        if v < 1:
            raise ValueError('page must be positive')
        return v
    
    @field_validator('token_count')
    @classmethod
    def token_count_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('token_count must be non-negative')
        return v
    
    @field_validator('content')
    @classmethod
    def content_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('content must not be empty')
        return v