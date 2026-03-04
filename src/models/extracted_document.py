from pydantic import BaseModel
from typing import List, Optional
from .provenance import PageRef

class TextBlock(BaseModel):
    text: str
    page_ref: PageRef
    reading_order: int


class TableBlock(BaseModel):
    headers: List[str]
    rows: List[List[str]]
    page_ref: PageRef


class FigureBlock(BaseModel):
    caption: Optional[str]
    page_ref: PageRef


class ExtractedDocument(BaseModel):
    document_name: str
    text_blocks: List[TextBlock]
    tables: List[TableBlock]
    figures: List[FigureBlock]