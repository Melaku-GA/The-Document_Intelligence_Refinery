"""
Unit tests for the Triage Agent classification system.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.triage import TriageAgent, detect_language, classify_domain
from src.models.enums import OriginType, LayoutComplexity, ExtractionCostTier


class TestTriageAgent:
    """Test cases for TriageAgent classification."""

    def test_triage_agent_initialization(self):
        """Test that TriageAgent can be initialized."""
        agent = TriageAgent()
        assert agent is not None

    def test_classify_sample_document(self):
        """Test classification of a sample document."""
        agent = TriageAgent()
        # Use one of the sample documents
        pdf_path = "Data/samples/Consumer Price Index August 2025.pdf"
        
        if os.path.exists(pdf_path):
            profile = agent.classify(pdf_path)
            
            # Verify profile has required fields
            assert profile.document_id is not None
            assert profile.document_name is not None
            assert profile.origin_type is not None
            assert profile.layout_complexity is not None
            assert profile.language is not None
            assert profile.estimated_extraction_cost is not None

    def test_detect_language_english(self):
        """Test English language detection."""
        text = "This is a sample English text that contains standard Latin characters and common words."
        lang, confidence = detect_language(text)
        assert lang == "en"
        assert confidence > 0.5

    def test_detect_language_amharic(self):
        """Test Amharic language detection."""
        # Sample with Ethiopic characters
        text = "ይህ አንድ ናሙና ጽሑፍ ነው ። አማርኛ ፊደል ።"
        lang, confidence = detect_language(text)
        assert lang == "am"
        assert confidence > 0.5

    def test_detect_language_short_text(self):
        """Test language detection with short text."""
        text = "short"
        lang, confidence = detect_language(text)
        assert lang == "en"  # Default fallback
        assert confidence == 0.5

    def test_classify_domain_financial(self):
        """Test financial domain classification."""
        text = """
        The company's balance sheet shows total assets of $10 million.
        The income statement indicates revenue of $5 million and net profit of $1 million.
        Cash flow from operations was positive at $2 million.
        """
        domain, confidence = classify_domain(text)
        assert domain == "financial"
        assert confidence > 0.3

    def test_classify_domain_technical(self):
        """Test technical domain classification."""
        text = """
        The API endpoint requires authentication using JWT tokens.
        The backend database uses PostgreSQL with connection pooling.
        The deployment pipeline uses Docker containers on Kubernetes.
        """
        domain, confidence = classify_domain(text)
        assert domain == "technical"
        assert confidence > 0.3

    def test_classify_domain_legal(self):
        """Test legal domain classification."""
        text = """
        WHEREAS the parties hereby agree to the terms and conditions set forth herein.
        PURSUANT TO the contract, the party shall indemnify against all liabilities.
        This agreement shall be governed by the jurisdiction of the courts.
        """
        domain, confidence = classify_domain(text)
        assert domain == "legal"
        assert confidence > 0.3

    def test_classify_domain_unknown(self):
        """Test unknown domain classification."""
        text = "This is just some random text without specific domain keywords."
        domain, confidence = classify_domain(text)
        assert domain is None
        assert confidence == 0.0


class TestOriginTypeDetection:
    """Test cases for origin type detection."""

    def test_native_digital_detection(self):
        """Test native digital document detection."""
        agent = TriageAgent()
        # High chars per page, low image ratio = native digital
        origin = agent._detect_origin_type(
            avg_chars=2500,
            image_ratio=0.05,
            metrics={}
        )
        assert origin == OriginType.NATIVE_DIGITAL

    def test_scanned_detection(self):
        """Test scanned document detection."""
        agent = TriageAgent()
        # Low chars per page, high image ratio = scanned
        origin = agent._detect_origin_type(
            avg_chars=5,
            image_ratio=0.8,
            metrics={}
        )
        assert origin == OriginType.SCANNED_IMAGE

    def test_form_detection(self):
        """Test form fillable detection."""
        agent = TriageAgent()
        origin = agent._detect_origin_type(
            avg_chars=1000,
            image_ratio=0.1,
            metrics={"form_fields": 10}
        )
        assert origin == OriginType.FORM_FILLABLE

    def test_mixed_detection(self):
        """Test mixed content detection."""
        agent = TriageAgent()
        origin = agent._detect_origin_type(
            avg_chars=500,
            image_ratio=0.3,
            metrics={}
        )
        assert origin == OriginType.MIXED


class TestLayoutComplexity:
    """Test cases for layout complexity detection."""

    def test_figure_heavy_detection(self):
        """Test figure-heavy layout detection."""
        agent = TriageAgent()
        layout = agent._detect_layout_complexity(
            image_ratio=0.5,
            avg_chars=1000,
            table_count=0,
            metrics={}
        )
        assert layout == LayoutComplexity.FIGURE_HEAVY

    def test_table_heavy_detection(self):
        """Test table-heavy layout detection."""
        agent = TriageAgent()
        layout = agent._detect_layout_complexity(
            image_ratio=0.1,
            avg_chars=3000,
            table_count=10,
            metrics={}
        )
        assert layout == LayoutComplexity.TABLE_HEAVY

    def test_single_column_detection(self):
        """Test single column layout detection."""
        agent = TriageAgent()
        layout = agent._detect_layout_complexity(
            image_ratio=0.05,
            avg_chars=1500,
            table_count=0,
            metrics={"column_count": 1}
        )
        assert layout == LayoutComplexity.SINGLE_COLUMN

    def test_multi_column_detection(self):
        """Test multi column layout detection."""
        agent = TriageAgent()
        layout = agent._detect_layout_complexity(
            image_ratio=0.1,
            avg_chars=2500,
            table_count=2,
            metrics={"column_count": 2}
        )
        assert layout == LayoutComplexity.MULTI_COLUMN


class TestExtractionCostEstimation:
    """Test cases for extraction cost estimation."""

    def test_fast_text_sufficient(self):
        """Test fast text strategy recommendation."""
        agent = TriageAgent()
        cost = agent._estimate_extraction_cost(
            OriginType.NATIVE_DIGITAL,
            LayoutComplexity.SINGLE_COLUMN
        )
        assert cost == ExtractionCostTier.FAST_TEXT_SUFFICIENT

    def test_vision_model_needed(self):
        """Test vision model recommendation for scanned docs."""
        agent = TriageAgent()
        cost = agent._estimate_extraction_cost(
            OriginType.SCANNED_IMAGE,
            LayoutComplexity.MIXED
        )
        assert cost == ExtractionCostTier.NEEDS_VISION_MODEL

    def test_layout_model_needed(self):
        """Test layout model recommendation."""
        agent = TriageAgent()
        cost = agent._estimate_extraction_cost(
            OriginType.FORM_FILLABLE,
            LayoutComplexity.TABLE_HEAVY
        )
        assert cost == ExtractionCostTier.NEEDS_LAYOUT_MODEL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
