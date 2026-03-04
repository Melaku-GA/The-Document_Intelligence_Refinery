import time
import base64
from pathlib import Path
from typing import Optional, Dict, Any

from src.strategies.base import BaseExtractor, ExtractionResult
from src.models.extracted_document import ExtractedDocument, TextBlock, TableBlock, FigureBlock
from src.models.provenance import PageRef, BoundingBox
from src.models.enums import ExtractionCostTier


class BudgetGuard:
    """
    Token budget guard for VLM-based extraction.
    Tracks spending and prevents runaway costs.
    """
    
    def __init__(
        self,
        max_tokens: int = 100000,
        max_cost: float = 5.0,  # $5.00 max
        cost_per_1k_input: float = 0.0015,  # ~$1.50/1M tokens (vision models)
        cost_per_1k_output: float = 0.004,  # ~$4.00/1M tokens
    ):
        self.max_tokens = max_tokens
        self.max_cost = max_cost
        self.cost_per_1k_input = cost_per_1k_input
        self.cost_per_1k_output = cost_per_1k_output
        
        self.tokens_spent = 0
        self.cost_spent = 0.0
        self.request_count = 0
    
    def estimate_cost(self, input_tokens: int, output_tokens: int = 500) -> float:
        """Estimate cost for a request."""
        input_cost = (input_tokens / 1000) * self.cost_per_1k_input
        output_cost = (output_tokens / 1000) * self.cost_per_1k_output
        return input_cost + output_cost
    
    def can_proceed(self, estimated_cost: float) -> bool:
        """Check if request would exceed budget."""
        return (self.cost_spent + estimated_cost) <= self.max_cost
    
    def record(self, input_tokens: int, output_tokens: int, actual_cost: float):
        """Record actual token usage."""
        self.tokens_spent += input_tokens + output_tokens
        self.cost_spent += actual_cost
        self.request_count += 1
    
    def get_status(self) -> Dict[str, Any]:
        """Get current budget status."""
        return {
            "tokens_spent": self.tokens_spent,
            "cost_spent": self.cost_spent,
            "requests": self.request_count,
            "budget_remaining": self.max_cost - self.cost_spent,
            "tokens_remaining": self.max_tokens - self.tokens_spent,
        }


class VisionExtractor(BaseExtractor):
    """
    Vision Language Model (VLM) based extraction.
    
    Uses VLM for:
    - Complex layout understanding
    - Handwriting recognition
    - Image-heavy documents
    - Tables with merged cells
    
    Note: Currently uses mock implementation.
    Integrate with OpenRouter or similar for production.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "openai/gpt-4o",
        max_pages: int = 10,
        budget_guard: Optional[BudgetGuard] = None,
    ):
        self.api_key = api_key
        self.model = model
        self.max_pages = max_pages
        self.budget_guard = budget_guard or BudgetGuard()
        
    def extract(self, pdf_path: str) -> ExtractionResult:
        """
        Extract content using VLM.
        
        Strategy:
        1. Convert PDF pages to images
        2. Send to VLM with extraction prompt
        3. Parse VLM response into structured format
        """
        start_time = time.time()
        
        # Check budget before proceeding
        if not self.budget_guard.can_proceed(estimated_cost=0.5):
            raise RuntimeError(
                f"Budget exhausted: {self.budget_guard.get_status()}"
            )
        
        # Convert PDF to images (first N pages based on budget)
        pages_to_process = self._get_pages_to_process(pdf_path)
        
        # Process with VLM (mock for now)
        text_blocks = []
        tables = []
        figures = []
        
        for page_num in pages_to_process:
            page_content = self._process_page_with_vlm(pdf_path, page_num)
            
            if page_content:
                text_blocks.extend(page_content.get("text_blocks", []))
                tables.extend(page_content.get("tables", []))
                figures.extend(page_content.get("figures", []))
        
        # Calculate confidence (VLM typically has high confidence for readable docs)
        doc_confidence = 0.90 if text_blocks else 0.5
        
        # High cost due to VLM API calls
        cost_estimate = ExtractionCostTier.NEEDS_VISION_MODEL.value
        
        extracted = ExtractedDocument(
            document_name=Path(pdf_path).name,
            text_blocks=text_blocks,
            tables=tables,
            figures=figures
        )
        
        processing_time = time.time() - start_time
        
        result = ExtractionResult(
            document=extracted,
            confidence=doc_confidence,
            cost_estimate=cost_estimate
        )
        result.processing_time = processing_time
        
        return result
    
    def _get_pages_to_process(self, pdf_path: str) -> list:
        """Determine which pages to process based on budget."""
        import pdfplumber
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                
                # Limit pages based on budget
                max_budget_pages = int(self.budget_guard.get_status()["budget_remaining"] / 0.1)
                return list(range(1, min(total_pages, self.max_pages, max_budget_pages) + 1))
        except:
            return [1]  # Fallback to first page
    
    def _process_page_with_vlm(
        self,
        pdf_path: str,
        page_num: int
    ) -> Dict[str, Any]:
        """
        Process a single page with VLM.
        
        In production, replace with actual API call:
        
        # Using OpenRouter
        import openai
        client = openai.OpenAI(api_key=self.api_key, base_url="https://openrouter.ai/api/v1")
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all text, tables, and figures from this page."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                    ]
                }
            ]
        )
        """
        
        # Mock implementation - returns structured placeholder
        # In production, this would call the VLM API
        
        return {
            "text_blocks": [
                TextBlock(
                    text=f"VLM extracted text from page {page_num}...",
                    page_ref=PageRef(
                        page_number=page_num,
                        bbox=BoundingBox(x0=0, y0=0, x1=100, y1=20)
                    ),
                    reading_order=0
                )
            ],
            "tables": [],
            "figures": []
        }
    
    def _pdf_to_images(self, pdf_path: str, page_nums: list) -> list:
        """
        Convert PDF pages to images for VLM processing.
        
        Requires: pip install pdf2image pillow
        """
        # Placeholder - implement with pdf2image
        # from pdf2image import convert_from_path
        # images = convert_from_path(pdf_path, first_page=page_nums[0], last_page=page_nums[-1])
        # return images
        return []
    
    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status."""
        return self.budget_guard.get_status()
