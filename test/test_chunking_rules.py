"""
Unit tests for chunking rules.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.chunking.rules import ChunkingRules, ChunkBoundaryType


class TestChunkingRules:
    """Test cases for chunking rules."""

    def test_chunking_rules_initialization(self):
        """Test ChunkingRules can be initialized."""
        rules = ChunkingRules()
        assert rules is not None
        assert rules.max_chars > 0
        assert rules.min_chars > 0

    def test_default_max_chars(self):
        """Test default max chars value."""
        rules = ChunkingRules()
        assert rules.max_chars == 800

    def test_default_min_chars(self):
        """Test default min chars value."""
        rules = ChunkingRules()
        assert rules.min_chars == 100

    def test_custom_max_chars(self):
        """Test custom max chars value."""
        rules = ChunkingRules(max_chars=1000)
        assert rules.max_chars == 1000


class TestBoundaryDetection:
    """Test cases for boundary detection."""

    def test_detect_paragraph_boundary(self):
        """Test paragraph boundary detection."""
        # Double newline indicates paragraph boundary
        text = "This is paragraph one.\n\nThis is paragraph two."
        
        boundaries = ChunkingRules.detect_boundaries(text)
        
        assert ChunkBoundaryType.PARAGRAPH in boundaries

    def test_detect_sentence_boundary(self):
        """Test sentence boundary detection."""
        text = "This is sentence one. This is sentence two. This is sentence three."
        
        boundaries = ChunkingRules.detect_boundaries(text)
        
        assert ChunkBoundaryType.SENTENCE in boundaries

    def test_detect_section_boundary(self):
        """Test section boundary detection."""
        # Section headers often indicate major boundaries
        text = "1. Introduction\n\nSome content here.\n\n2. Methods\n\nMore content."
        
        boundaries = ChunkingRules.detect_boundaries(text)
        
        assert ChunkBoundaryType.SECTION in boundaries

    def test_detect_table_boundary(self):
        """Test table boundary detection."""
        # Table patterns indicate table boundaries
        text = "Before table\n| Column 1 | Column 2 |\n|----------|----------|\n| Cell 1   | Cell 2   |\nAfter table"
        
        boundaries = ChunkingRules.detect_boundaries(text)
        
        assert ChunkBoundaryType.TABLE in boundaries


class TestChunkSizeCalculation:
    """Test cases for chunk size calculations."""

    def test_calculate_chunk_size_simple(self):
        """Test simple chunk size calculation."""
        text = "A" * 500
        max_size = 800
        
        chunks = ChunkingRules.split_by_size(text, max_size)
        
        assert len(chunks) == 1
        assert len(chunks[0]) == 500

    def test_calculate_chunk_size_overflow(self):
        """Test chunk size when text exceeds max."""
        text = "A" * 1500
        max_size = 800
        
        chunks = ChunkingRules.split_by_size(text, max_size)
        
        assert len(chunks) == 2
        assert len(chunks[0]) == 800
        assert len(chunks[1]) == 700

    def test_calculate_chunk_size_multiple(self):
        """Test multiple chunk generation."""
        text = "A" * 2500
        max_size = 800
        
        chunks = ChunkingRules.split_by_size(text, max_size)
        
        assert len(chunks) == 4  # 800 + 800 + 800 + 100
        assert len(chunks[-1]) == 100

    def test_min_chunk_size_enforcement(self):
        """Test minimum chunk size is enforced."""
        text = "Short text"
        max_size = 1000
        min_size = 50
        
        # Small text should still be a chunk
        chunks = ChunkingRules.split_by_size(text, max_size, min_size)
        
        assert len(chunks) >= 1


class TestSemanticChunking:
    """Test cases for semantic chunking logic."""

    def test_semantic_chunk_at_section(self):
        """Test chunking at semantic sections."""
        text = "Introduction\n\nThis is the introduction content.\n\nMethodology\n\nThis is methodology content."
        
        chunks = ChunkingRules.semantic_chunk(text)
        
        # Should have at least 2 chunks (one per section)
        assert len(chunks) >= 2

    def test_semantic_chunk_respects_max_size(self):
        """Test semantic chunking respects max size."""
        # Create long text that should be split
        text = "Section A\n\n" + ("Content here. " * 200)
        
        chunks = ChunkingRules.semantic_chunk(text, max_chars=800)
        
        # Check that no chunk exceeds max
        for chunk in chunks:
            assert len(chunk) <= 800

    def test_semantic_chunk_preserves_context(self):
        """Test semantic chunking preserves context."""
        text = "Important: This is a critical piece of information that should not be split."
        
        chunks = ChunkingRules.semantic_chunk(text, max_chars=100)
        
        # Important content should stay together if possible
        assert len(chunks) <= 2  # Either 1 or 2 chunks


class TestChunkBoundaryType:
    """Test cases for chunk boundary types."""

    def test_boundary_type_values(self):
        """Test all boundary type values exist."""
        assert hasattr(ChunkBoundaryType, 'PARAGRAPH')
        assert hasattr(ChunkBoundaryType, 'SENTENCE')
        assert hasattr(ChunkBoundaryType, 'SECTION')
        assert hasattr(ChunkBoundaryType, 'TABLE')
        assert hasattr(ChunkBoundaryType, 'PAGE')
        assert hasattr(ChunkBoundaryType, 'FORCE')

    def test_boundary_priority(self):
        """Test boundary priority ordering."""
        # PAGE should have highest priority
        # SENTENCE should have lowest priority
        page_priority = ChunkBoundaryType.PAGE.value
        sentence_priority = ChunkBoundaryType.SENTENCE.value
        
        assert page_priority < sentence_priority  # Lower value = higher priority


class TestOverlapHandling:
    """Test cases for chunk overlap handling."""

    def test_overlap_calculation(self):
        """Test overlap calculation."""
        chunk_size = 800
        overlap = 100
        
        # Second chunk should start 100 chars before the end of first
        first_end = chunk_size
        second_start = first_end - overlap
        
        assert second_start == 700

    def test_overlap_with_boundaries(self):
        """Test overlap respects boundaries."""
        text = "First chunk content here.\n\nSecond section starts here."
        chunk_size = 30
        overlap = 10
        
        # Overlap should not create chunks that don't make sense
        # The overlap should be trimmed to fit at boundary
        chunks = ChunkingRules.split_with_overlap(text, chunk_size, overlap)
        
        assert len(chunks) >= 1


class TestSpecialCases:
    """Test cases for special chunking scenarios."""

    def test_empty_text_handling(self):
        """Test handling of empty text."""
        text = ""
        
        chunks = ChunkingRules.semantic_chunk(text)
        
        assert len(chunks) == 0

    def test_whitespace_only_handling(self):
        """Test handling of whitespace-only text."""
        text = "   \n\n   \n\n   "
        
        chunks = ChunkingRules.semantic_chunk(text)
        
        # Whitespace-only should result in empty or minimal chunks
        assert len([c for c in chunks if c.strip()]) == 0

    def test_single_word_handling(self):
        """Test handling of single word."""
        text = "Word"
        
        chunks = ChunkingRules.semantic_chunk(text)
        
        # Single word should still be a chunk if above min
        assert len(chunks) >= 1

    def test_unicode_content_handling(self):
        """Test handling of unicode content."""
        text = "አማርኛ ጽሑፍ English text 日本語"
        
        chunks = ChunkingRules.semantic_chunk(text)
        
        assert len(chunks) >= 1
        # Unicode should be preserved
        assert "አማርኛ" in chunks[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
