from pydantic import BaseModel
from typing import List, Optional
from .provenance import PageRef
from .enums import ChunkType

class LDU(BaseModel):
    content: str
    chunk_type: ChunkType

    page_refs: List[PageRef]
    parent_section: Optional[str]

    token_count: int
    content_hash: str