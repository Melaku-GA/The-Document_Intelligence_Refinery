from pydantic import BaseModel
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