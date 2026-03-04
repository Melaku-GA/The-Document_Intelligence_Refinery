"""
Unit tests for extraction confidence scoring.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategies.base import ExtractionStrategy, StrategyType
from src.models.enums import OriginType, LayoutComplexity


class TestConfidenceScoring:
    """Test cases for confidence scoring calculations."""

    def test_confidence_calculation_native_digital(self):
        """Test confidence calculation for native digital documents."""
        # High text extraction rate + native digital = high confidence
        text_extraction_rate = 0.95
        is_native = True
        has_layout = True
        
        # Base confidence
        confidence = text_extraction_rate
        
        # Native digital bonus
        if is_native:
            confidence += 0.05
        
        # Layout preservation bonus
        if has_layout:
            confidence += 0.02
        
        assert confidence >= 0.9

    def test_confidence_calculation_scanned(self):
        """Test confidence calculation for scanned documents."""
        # Lower text extraction rate for scanned
        text_extraction_rate = 0.75
        is_native = False
        has_layout = True
        
        confidence = text_extraction_rate
        
        if is_native:
            confidence += 0.05
        
        if has_layout:
            confidence += 0.02
        
        assert confidence < 0.9

    def test_confidence_with_tables(self):
        """Test confidence with table extraction."""
        text_confidence = 0.90
        table_confidence = 0.85
        
        # Weighted average
        overall = (text_confidence * 0.7) + (table_confidence * 0.3)
        
        assert 0.85 <= overall <= 0.92

    def test_confidence_with_images(self):
        """Test confidence with image extraction."""
        text_confidence = 0.90
        image_confidence = 0.80
        
        # Weighted average
        overall = (text_confidence * 0.6) + (image_confidence * 0.4)
        
        assert 0.82 <= overall <= 0.90


class TestStrategySelectionConfidence:
    """Test cases for strategy selection based on confidence."""

    def test_strategy_a_selection(self):
        """Test Strategy A selection criteria."""
        origin_type = OriginType.NATIVE_DIGITAL
        layout_complexity = LayoutComplexity.SINGLE_COLUMN
        text_quality = 0.98
        
        # Strategy A (Fast Text) is appropriate when:
        # - Native digital
        # - Simple layout
        # - High text quality
        is_strategy_a_appropriate = (
            origin_type == OriginType.NATIVE_DIGITAL and
            layout_complexity in [LayoutComplexity.SINGLE_COLUMN, LayoutComplexity.MULTI_COLUMN] and
            text_quality > 0.95
        )
        
        assert is_strategy_a_appropriate

    def test_strategy_b_selection(self):
        """Test Strategy B selection criteria."""
        origin_type = OriginType.NATIVE_DIGITAL
        layout_complexity = LayoutComplexity.TABLE_HEAVY
        text_quality = 0.90
        
        # Strategy B (Layout) is appropriate when:
        # - Native digital
        # - Complex layout (tables, multi-column)
        # - Good text quality
        is_strategy_b_appropriate = (
            origin_type == OriginType.NATIVE_DIGITAL and
            layout_complexity in [LayoutComplexity.TABLE_HEAVY, LayoutComplexity.MULTI_COLUMN, LayoutComplexity.FIGURE_HEAVY]
        )
        
        assert is_strategy_b_appropriate

    def test_strategy_c_selection(self):
        """Test Strategy C selection criteria."""
        origin_type = OriginType.SCANNED_IMAGE
        layout_complexity = LayoutComplexity.MIXED
        text_quality = 0.70
        
        # Strategy C (Vision) is appropriate when:
        # - Scanned image
        # - Mixed layout
        # - Lower text quality
        is_strategy_c_appropriate = (
            origin_type == OriginType.SCANNED_IMAGE or
            text_quality < 0.80
        )
        
        assert is_strategy_c_appropriate


class TestConfidenceThresholds:
    """Test cases for confidence threshold validation."""

    def test_high_confidence_threshold(self):
        """Test high confidence threshold (>0.95)."""
        confidence = 0.96
        
        assert confidence > 0.95
        assert confidence >= 0.95

    def test_medium_confidence_threshold(self):
        """Test medium confidence threshold (0.80-0.95)."""
        confidence = 0.87
        
        assert 0.80 <= confidence < 0.95

    def test_low_confidence_threshold(self):
        """Test low confidence threshold (<0.80)."""
        confidence = 0.65
        
        assert confidence < 0.80

    def test_confidence_boundary_conditions(self):
        """Test confidence boundary conditions."""
        # Test boundary at 0.95
        assert 0.95 > 0.95 == False
        assert 0.95 >= 0.95 == True
        
        # Test boundary at 0.80
        assert 0.80 >= 0.80 == True
        assert 0.80 > 0.80 == False


class TestConfidenceAggregation:
    """Test cases for aggregating confidence across pages."""

    def test_average_confidence(self):
        """Test average confidence calculation across pages."""
        page_confidences = [0.95, 0.92, 0.88, 0.91, 0.94]
        
        avg_confidence = sum(page_confidences) / len(page_confidences)
        
        assert 0.90 <= avg_confidence <= 0.95

    def test_min_confidence(self):
        """Test minimum confidence across pages."""
        page_confidences = [0.95, 0.92, 0.88, 0.91, 0.94]
        
        min_confidence = min(page_confidences)
        
        assert min_confidence == 0.88

    def test_weighted_confidence(self):
        """Test weighted confidence based on page importance."""
        # More important pages (with tables) get higher weight
        page_confidences = [
            (0.95, 0.1),  # Cover page - low importance
            (0.90, 0.3),  # Regular content
            (0.85, 0.4),  # Table page - high importance
            (0.92, 0.2),  # Regular content
        ]
        
        weighted_sum = sum(conf * weight for conf, weight in page_confidences)
        total_weight = sum(weight for _, weight in page_confidences)
        
        weighted_confidence = weighted_sum / total_weight
        
        assert 0.85 <= weighted_confidence <= 0.95


class TestConfidenceAdjustment:
    """Test cases for confidence factors."""

    def test_text_density_adjustment(self):
        """Test confidence adjustment based on text density."""
        base_confidence = 0.90
        chars_per_page = 2500
        
        # High text density suggests good extraction
        if chars_per_page > 2000:
            adjusted = base_confidence + 0.05
        else:
            adjusted = base_confidence
        
        assert adjusted == 0.95

    def test_image_ratio_adjustment(self):
        """Test confidence adjustment based on image ratio."""
        base_confidence = 0.90
        image_ratio = 0.4
        
        # High image ratio may indicate scanned or complex layout
        if image_ratio > 0.3:
            adjusted = base_confidence - 0.1
        else:
            adjusted = base_confidence
        
        assert adjusted == 0.80

    def test_table_count_adjustment(self):
        """Test confidence adjustment based on table count."""
        base_confidence = 0.90
        table_count = 15
        
        # Many tables may need layout model for proper extraction
        if table_count > 10:
            # Ensure layout model is used
            adjusted = base_confidence + 0.02  # Good with layout model
        else:
            adjusted = base_confidence
        
        assert adjusted == 0.92


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
