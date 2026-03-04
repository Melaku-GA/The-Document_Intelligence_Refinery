import time
from pathlib import Path

from src.strategies.base import BaseExtractor, ExtractionResult
from src.models.extracted_document import ExtractedDocument, TextBlock, TableBlock, FigureBlock
from src.models.provenance import PageRef, BoundingBox
from src.models.enums import ExtractionCostTier


class MinerULayoutExtractor(BaseExtractor):
    """
    Layout-aware extractor using MinerU/Docling approach.
    
    Extracts:
    - Text blocks with bounding boxes
    - Tables as JSON structures
    - Figures with captions
    
    Note: This is a placeholder with simulated output.
    Replace with actual MinerU pipeline integration.
    """

    def extract(self, pdf_path: str) -> ExtractionResult:
        """
        Extract layout-structured content from PDF.
        """
        start_time = time.time()
        
        # ---- Placeholder for MinerU output ----
        # In production, replace with actual MinerU API call
        # e.g., from magic_pdf import parse_pdf_by_sdg
        mineru_output = self._simulate_mineru_extraction(pdf_path)
        
        # Convert to our models
        text_blocks = []
        tables = []
        figures = []
        
        for item in mineru_output:
            item_type = item.get("type", "text")
            
            if item_type == "text":
                bbox = BoundingBox(
                    x0=item["bbox"][0],
                    y0=item["bbox"][1],
                    x1=item["bbox"][2],
                    y1=item["bbox"][3],
                )
                page_ref = PageRef(
                    page_number=item["page"],
                    bbox=bbox
                )
                text_blocks.append(
                    TextBlock(
                        text=item["text"],
                        page_ref=page_ref,
                        reading_order=item.get("order", 0)
                    )
                )
                
            elif item_type == "table":
                # Filter out None values from table cells
                headers = [str(h) if h is not None else "" for h in item.get("headers", [])]
                rows = [[str(c) if c is not None else "" for c in row] for row in item.get("rows", [])]
                
                bbox = BoundingBox(
                    x0=item["bbox"][0],
                    y0=item["bbox"][1],
                    x1=item["bbox"][2],
                    y1=item["bbox"][3],
                )
                page_ref = PageRef(
                    page_number=item["page"],
                    bbox=bbox
                )
                tables.append(
                    TableBlock(
                        headers=headers,
                        rows=rows,
                        page_ref=page_ref
                    )
                )
                
            elif item_type == "figure":
                bbox = BoundingBox(
                    x0=item["bbox"][0],
                    y0=item["bbox"][1],
                    x1=item["bbox"][2],
                    y1=item["bbox"][3],
                )
                page_ref = PageRef(
                    page_number=item["page"],
                    bbox=bbox
                )
                figures.append(
                    FigureBlock(
                        caption=item.get("caption"),
                        page_ref=page_ref
                    )
                )
        
        # Calculate average confidence
        if mineru_output:
            confidences = [item.get("confidence", 0.8) for item in mineru_output]
            doc_confidence = sum(confidences) / len(confidences)
        else:
            doc_confidence = 0.5
        
        # Cost estimation (higher than fast_text due to ML processing)
        cost_estimate = ExtractionCostTier.LAYOUT_AWARE.value
        
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

    def _simulate_mineru_extraction(self, pdf_path: str) -> list:
        """
        Simulate MinerU output for development/testing.
        
        In production, replace with:
        from magic_pdf import parse_pdf_by_sdg
        result = parse_pdf_by_sdg(pdf_path)
        return result.get("content", [])
        """
        import pdfplumber
        
        output = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract text with layout info
                    words = page.extract_words(use_text_flow=True)
                    
                    # Group words into blocks (simplified)
                    current_block = []
                    for i, w in enumerate(words):
                        current_block.append(w["text"])
                        
                        # Create block every 20 words or at end
                        if len(current_block) >= 20 or i == len(words) - 1:
                            text = " ".join(current_block)
                            if text.strip():
                                output.append({
                                    "type": "text",
                                    "text": text,
                                    "page": page_num,
                                    "bbox": [
                                        w.get("x0", 0),
                                        w.get("top", 0),
                                        w.get("x1", 100),
                                        w.get("bottom", 20)
                                    ],
                                    "confidence": 0.85,
                                    "order": len(output)
                                })
                            current_block = []
                    
                    # Extract tables (if any)
                    tables = page.extract_tables()
                    if tables:
                        for table_idx, table in enumerate(tables):
                            output.append({
                                "type": "table",
                                "headers": table[0] if table else [],
                                "rows": table[1:] if len(table) > 1 else [],
                                "page": page_num,
                                "bbox": [50, 100, 500, 300],  # Estimated
                                "confidence": 0.80
                            })
                    
        except Exception as e:
            # Fallback to simple extraction on error
            output = [
                {
                    "type": "text",
                    "text": f"Error extracting layout: {str(e)}",
                    "page": 1,
                    "bbox": [0, 0, 100, 20],
                    "confidence": 0.5
                }
            ]
        
        return output
