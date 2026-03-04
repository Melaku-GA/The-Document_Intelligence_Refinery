from pydantic import BaseModel, field_validator
from typing import Tuple

class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float
    
    @field_validator('x1')
    @classmethod
    def x1_must_be_greater_than_x0(cls, v, info):
        if 'x0' in info.data and v <= info.data['x0']:
            raise ValueError('x1 must be greater than x0')
        return v
    
    @field_validator('y1')
    @classmethod
    def y1_must_be_greater_than_y0(cls, v, info):
        if 'y0' in info.data and v <= info.data['y0']:
            raise ValueError('y1 must be greater than y0')
        return v


class PageRef(BaseModel):
    page_number: int
    bbox: BoundingBox
    
    @field_validator('page_number')
    @classmethod
    def page_must_be_positive(cls, v):
        if v < 1:
            raise ValueError('page_number must be positive')
        return v


class ProvenanceChain(BaseModel):
    document_name: str
    page_number: int
    bbox: BoundingBox
    content_hash: str
    
    @field_validator('page_number')
    @classmethod
    def page_must_be_positive(cls, v):
        if v < 1:
            raise ValueError('page_number must be positive')
        return v