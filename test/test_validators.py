"""
Tests for Pydantic model validators and domain invariants.
"""

import pytest
from pydantic import ValidationError
from src.models.provenance import BoundingBox, PageRef, ProvenanceChain
from src.models.ldu import LDU, LDUType
from src.models.enums import ChunkType


class TestBoundingBoxValidators:
    """Test BoundingBox domain invariants."""
    
    def test_valid_bbox(self):
        """Valid bounding box should pass."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=200)
        assert bbox.x0 == 10
        assert bbox.y0 == 20
        assert bbox.x1 == 100
        assert bbox.y1 == 200
    
    def test_x1_must_be_greater_than_x0(self):
        """x1 must be greater than x0."""
        with pytest.raises(ValidationError) as exc_info:
            BoundingBox(x0=100, y0=20, x1=50, y1=200)
        assert "x1 must be greater than x0" in str(exc_info.value)
    
    def test_y1_must_be_greater_than_y0(self):
        """y1 must be greater than y0."""
        with pytest.raises(ValidationError) as exc_info:
            BoundingBox(x0=10, y0=200, x1=100, y1=50)
        assert "y1 must be greater than y0" in str(exc_info.value)


class TestPageRefValidators:
    """Test PageRef domain invariants."""
    
    def test_valid_page_ref(self):
        """Valid page reference should pass."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=200)
        page_ref = PageRef(page_number=5, bbox=bbox)
        assert page_ref.page_number == 5
    
    def test_page_must_be_positive(self):
        """page_number must be positive."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=200)
        with pytest.raises(ValidationError) as exc_info:
            PageRef(page_number=0, bbox=bbox)
        assert "page_number must be positive" in str(exc_info.value)
    
    def test_page_zero_is_invalid(self):
        """page_number=0 should be invalid."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=200)
        with pytest.raises(ValidationError):
            PageRef(page_number=0, bbox=bbox)
    
    def test_negative_page_is_invalid(self):
        """Negative page_number should be invalid."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=200)
        with pytest.raises(ValidationError):
            PageRef(page_number=-1, bbox=bbox)


class TestLDUValidators:
    """Test LDU domain invariants."""
    
    def test_valid_ldu(self):
        """Valid LDU should pass."""
        ldu = LDU(
            ldu_type=LDUType.PARAGRAPH,
            content="This is a test paragraph.",
            chunk_type=ChunkType.PARAGRAPH,
            page=1,
            page_refs=[],
            parent_section=None,
            token_count=5,
            content_hash="abc123"
        )
        assert ldu.page == 1
        assert ldu.token_count == 5
    
    def test_page_must_be_positive(self):
        """page must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            LDU(
                ldu_type=LDUType.PARAGRAPH,
                content="Test",
                chunk_type=ChunkType.PARAGRAPH,
                page=0,
                page_refs=[],
                parent_section=None,
                token_count=1,
                content_hash="abc"
            )
        assert "page must be positive" in str(exc_info.value)
    
    def test_negative_token_count_invalid(self):
        """token_count must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            LDU(
                ldu_type=LDUType.PARAGRAPH,
                content="Test",
                chunk_type=ChunkType.PARAGRAPH,
                page=1,
                page_refs=[],
                parent_section=None,
                token_count=-1,
                content_hash="abc"
            )
        assert "token_count must be non-negative" in str(exc_info.value)
    
    def test_empty_content_invalid(self):
        """content must not be empty."""
        with pytest.raises(ValidationError) as exc_info:
            LDU(
                ldu_type=LDUType.PARAGRAPH,
                content="",
                chunk_type=ChunkType.PARAGRAPH,
                page=1,
                page_refs=[],
                parent_section=None,
                token_count=0,
                content_hash="abc"
            )
        assert "content must not be empty" in str(exc_info.value)
    
    def test_whitespace_content_invalid(self):
        """content with only whitespace should be invalid."""
        with pytest.raises(ValidationError) as exc_info:
            LDU(
                ldu_type=LDUType.PARAGRAPH,
                content="   ",
                chunk_type=ChunkType.PARAGRAPH,
                page=1,
                page_refs=[],
                parent_section=None,
                token_count=0,
                content_hash="abc"
            )
        assert "content must not be empty" in str(exc_info.value)


class TestProvenanceChainValidators:
    """Test ProvenanceChain domain invariants."""
    
    def test_valid_provenance_chain(self):
        """Valid provenance chain should pass."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=200)
        chain = ProvenanceChain(
            document_name="test.pdf",
            page_number=5,
            bbox=bbox,
            content_hash="abc123"
        )
        assert chain.page_number == 5
    
    def test_provenance_page_must_be_positive(self):
        """page_number in provenance must be positive."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=200)
        with pytest.raises(ValidationError):
            ProvenanceChain(
                document_name="test.pdf",
                page_number=0,
                bbox=bbox,
                content_hash="abc"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
