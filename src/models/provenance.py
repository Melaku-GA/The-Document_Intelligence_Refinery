from pydantic import BaseModel
from typing import Tuple

class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class PageRef(BaseModel):
    page_number: int
    bbox: BoundingBox


class ProvenanceChain(BaseModel):
    document_name: str
    page_number: int
    bbox: BoundingBox
    content_hash: str