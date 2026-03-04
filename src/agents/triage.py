from pathlib import Path
from uuid import uuid4
import re
from collections import Counter

from src.models.document_profile import DocumentProfile
from src.models.enums import (
    OriginType,
    LayoutComplexity,
    ExtractionCostTier,
)
from src.utils.pdf_metrics import analyze_pdf_metrics


# Domain keywords for classification
DOMAIN_KEYWORDS = {
    "financial": [
        "balance sheet", "income statement", "cash flow", "revenue", "expense",
        "asset", "liability", "equity", "profit", "loss", "audit", "fiscal",
        "budget", "financial", "quarterly", "annual report", "bank", "loan",
        "interest", "depreciation", "amortization", "ledger", "receivable", "payable"
    ],
    "legal": [
        "whereas", "hereby", "pursuant to", "contract", "agreement", "party",
        "plaintiff", "defendant", "court", "jurisdiction", "arbitration", "clause",
        "amendment", "liability", "indemnity", "warranty", "confidential", "termination"
    ],
    "technical": [
        "algorithm", "api", "backend", "frontend", "database", "server", "client",
        "protocol", "encryption", "authentication", "configuration", "deployment",
        "infrastructure", "microservice", "container", "pipeline", "framework", "library"
    ],
    "medical": [
        "patient", "diagnosis", "treatment", "symptom", "prescription", "medication",
        "hospital", "clinical", "physician", "disease", "therapy", "surgery",
        "biopsy", "radiology", "laboratory", "vaccine", "dosage", "pharmaceutical"
    ]
}


def detect_language(text_sample: str) -> tuple[str, float]:
    """Detect language using character frequency analysis."""
    if not text_sample or len(text_sample) < 50:
        return "en", 0.5
    
    # Character set patterns for different scripts
    ethiopic_chars = len(re.findall(r'[\u1200-\u137F]', text_sample))
    latin_chars = len(re.findall(r'[a-zA-Z]', text_sample))
    
    total = ethiopic_chars + latin_chars
    if total == 0:
        return "en", 0.5
    
    ethiopic_ratio = ethiopic_chars / total
    latin_ratio = latin_chars / total
    
    # Check for Amharic/Ethiopic script
    if ethiopic_ratio > 0.3:
        return "am", min(0.95, ethiopic_ratio + 0.1)
    
    # Default to English with high confidence for Latin-dominated text
    return "en", min(0.95, latin_ratio + 0.1)


def classify_domain(text_sample: str) -> tuple[str | None, float]:
    """Classify document domain using keyword matching."""
    if not text_sample or len(text_sample) < 100:
        return None, 0.0
    
    text_lower = text_sample.lower()
    scores = {}
    
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[domain] = score
    
    if not scores:
        return None, 0.0
    
    best_domain = max(scores, key=scores.get)
    # Normalize confidence based on number of matches
    confidence = min(0.95, 0.3 + (scores[best_domain] * 0.1))
    
    return best_domain, confidence


class TriageAgent:
    def __init__(self):
        pass

    def classify(self, pdf_path: str) -> DocumentProfile:
        """Classify document and create profile."""
        metrics = analyze_pdf_metrics(pdf_path)
        
        # Extract text sample for language/domain analysis
        text_sample = metrics.get("text_sample", "")[:5000]  # First 5000 chars
        
        avg_chars = metrics["avg_chars_per_page"]
        image_ratio = metrics["image_area_ratio"]
        table_count = metrics.get("table_count", 0)
        
        # ---- Origin Type ----
        origin_type = self._detect_origin_type(avg_chars, image_ratio, metrics)

        # ---- Layout Complexity ----
        layout = self._detect_layout_complexity(image_ratio, avg_chars, table_count, metrics)

        # ---- Cost Tier ----
        cost = self._estimate_extraction_cost(origin_type, layout)

        # ---- Language Detection ----
        language, language_confidence = detect_language(text_sample)

        # ---- Domain Classification ----
        domain_hint, domain_confidence = classify_domain(text_sample)

        profile = DocumentProfile(
            document_id=str(uuid4()),
            document_name=Path(pdf_path).name,
            origin_type=origin_type,
            layout_complexity=layout,
            language=language,
            language_confidence=language_confidence,
            domain_hint=domain_hint,
            estimated_extraction_cost=cost,
            avg_chars_per_page=avg_chars,
            image_area_ratio=image_ratio,
            page_count=metrics.get("pages", 0),
            is_native_digital=(origin_type == OriginType.NATIVE_DIGITAL),
            has_tables=(table_count > 0),
            has_images=(image_ratio > 0.1),
        )

        return profile
    
    def _detect_origin_type(self, avg_chars: float, image_ratio: float, metrics: dict) -> OriginType:
        """Detect document origin type."""
        # Check for form fields (form fillable)
        form_fields = metrics.get("form_fields", 0)
        if form_fields > 0:
            return OriginType.FORM_FILLABLE
        
        # Scanned image detection
        if avg_chars < 10 and image_ratio > 0.5:
            return OriginType.SCANNED_IMAGE
        
        # Native digital detection
        if avg_chars > 100 and image_ratio < 0.2:
            return OriginType.NATIVE_DIGITAL
        
        # Mixed content
        return OriginType.MIXED
    
    def _detect_layout_complexity(
        self, 
        image_ratio: float, 
        avg_chars: float, 
        table_count: int,
        metrics: dict
    ) -> LayoutComplexity:
        """Detect layout complexity."""
        # Figure heavy
        if image_ratio > 0.4:
            return LayoutComplexity.FIGURE_HEAVY
        
        # Table heavy
        if table_count > 5 or metrics.get("table_area_ratio", 0) > 0.3:
            return LayoutComplexity.TABLE_HEAVY
        
        # Multi-column detection (heuristic)
        if avg_chars > 200 and metrics.get("column_count", 1) > 1:
            return LayoutComplexity.MULTI_COLUMN
        
        # Single column (simple documents)
        if avg_chars > 100:
            return LayoutComplexity.SINGLE_COLUMN
        
        return LayoutComplexity.MIXED
    
    def _estimate_extraction_cost(self, origin_type: OriginType, layout: LayoutComplexity) -> ExtractionCostTier:
        """Estimate extraction cost based on document characteristics."""
        # Fast text sufficient for simple native digital single-column
        if (origin_type == OriginType.NATIVE_DIGITAL and 
            layout in (LayoutComplexity.SINGLE_COLUMN, LayoutComplexity.MULTI_COLUMN)):
            return ExtractionCostTier.FAST_TEXT_SUFFICIENT
        
        # Vision model needed for scanned images
        if origin_type == OriginType.SCANNED_IMAGE:
            return ExtractionCostTier.NEEDS_VISION_MODEL
        
        # Layout model needed for complex layouts
        if origin_type in (OriginType.FORM_FILLABLE, OriginType.MIXED):
            return ExtractionCostTier.NEEDS_LAYOUT_MODEL
        
        # Default to layout model
        return ExtractionCostTier.NEEDS_LAYOUT_MODEL


def save_profile(profile: DocumentProfile, output_dir=".refinery/profiles"):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(output_dir) / f"{profile.document_id}.json"
    out_path.write_text(profile.model_dump_json(indent=2))