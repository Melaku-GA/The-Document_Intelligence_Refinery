import time
from pathlib import Path
from typing import Optional

from src.models.document_profile import DocumentProfile
from src.models.enums import ExtractionCostTier
from src.strategies.fast_text import FastTextExtractor
from src.strategies.mineru_layout import MinerULayoutExtractor
from src.strategies.vision import VisionExtractor, BudgetGuard
from src.strategies.base import ExtractionResult
from src.storage.ledger import ExtractionLedger


class ExtractionRouter:
    """
    Multi-strategy extraction router with confidence-gated escalation.
    
    Strategy selection based on DocumentProfile:
    - FAST_TEXT_SUFFICIENT: Try fast_text first, escalate if confidence < threshold
    - NEEDS_LAYOUT_MODEL: Use MinerU layout extraction directly
    - NEEDS_VISION_MODEL: Use VLM extraction directly
    
    Confidence escalation:
    - If Strategy A confidence < threshold, auto-retry with Strategy B
    - Continue until threshold met or all strategies exhausted
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.65,
        max_escalation_levels: int = 2,
        budget_guard: Optional[BudgetGuard] = None,
    ):
        self.confidence_threshold = confidence_threshold
        self.max_escalation_levels = max_escalation_levels
        
        # Initialize extractors
        self.fast_text = FastTextExtractor()
        self.mineru = MinerULayoutExtractor()
        self.vision = VisionExtractor(budget_guard=budget_guard or BudgetGuard())
        
        # Initialize ledger
        self.ledger = ExtractionLedger()
        
    def extract(
        self,
        pdf_path: str,
        profile: DocumentProfile,
    ) -> ExtractionResult:
        """
        Route extraction based on DocumentProfile with confidence-gated escalation.
        
        Args:
            pdf_path: Path to PDF file
            profile: Document profile from triage
            
        Returns:
            ExtractionResult with highest confidence achieved
        """
        start_time = time.time()
        
        # Select initial strategy based on profile
        initial_strategy = self._select_initial_strategy(profile)
        
        # Track escalation path
        escalation_path = []
        
        # Strategy A: Initial extraction
        result = self._execute_strategy(
            initial_strategy,
            pdf_path,
            profile,
            escalation_path
        )
        
        # Confidence-gated escalation loop
        while result.confidence < self.confidence_threshold:
            next_strategy = self._get_next_strategy(
                initial_strategy,
                len(escalation_path)
            )
            
            if next_strategy is None:
                # No more strategies to try
                break
                
            escalation_path.append(next_strategy)
            
            # Execute next strategy
            result = self._execute_strategy(
                next_strategy,
                pdf_path,
                profile,
                escalation_path
            )
        
        # Log final result
        total_time = time.time() - start_time
        self._log_extraction(
            document_name=profile.document_name,
            strategy=str(result),  # Will use strategy name
            confidence=result.confidence,
            cost=result.cost_estimate,
            processing_time=total_time,
            escalated=len(escalation_path) > 0,
            escalation_path=escalation_path,
        )
        
        return result
    
    def _select_initial_strategy(
        self,
        profile: DocumentProfile
    ) -> str:
        """
        Select initial extraction strategy based on document profile.
        """
        cost_tier = profile.estimated_extraction_cost
        
        if cost_tier == ExtractionCostTier.NEEDS_VISION_MODEL:
            return "vision"
        elif cost_tier == ExtractionCostTier.NEEDS_LAYOUT_MODEL:
            return "mineru"
        else:
            return "fast_text"
    
    def _get_next_strategy(
        self,
        initial_strategy: str,
        escalation_level: int
    ) -> Optional[str]:
        """
        Get next strategy in escalation chain.
        """
        strategy_chain = {
            "fast_text": ["mineru", "vision"],
            "mineru": ["vision"],
            "vision": [None],
        }
        
        if escalation_level < len(strategy_chain.get(initial_strategy, [])):
            return strategy_chain[initial_strategy][escalation_level]
        
        return None
    
    def _execute_strategy(
        self,
        strategy: str,
        pdf_path: str,
        profile: DocumentProfile,
        escalation_path: list,
    ) -> ExtractionResult:
        """
        Execute a specific extraction strategy.
        """
        if strategy == "fast_text":
            result = self.fast_text.extract(pdf_path)
            strategy_name = "fast_text"
        elif strategy == "mineru":
            result = self.mineru.extract(pdf_path)
            strategy_name = "mineru_layout"
        elif strategy == "vision":
            result = self.vision.extract(pdf_path)
            strategy_name = "vision_vlm"
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        # Log this attempt
        self.ledger.log(
            document_name=profile.document_name,
            strategy=strategy_name,
            confidence=result.confidence,
            cost=result.cost_estimate,
            processing_time=getattr(result, "processing_time", 0),
            escalated=False,  # Will be set in final log
        )
        
        return result
    
    def _log_extraction(
        self,
        document_name: str,
        strategy: str,
        confidence: float,
        cost: float,
        processing_time: float,
        escalated: bool,
        escalation_path: list,
    ):
        """
        Log final extraction result with full details.
        """
        # Use the ledger's log method with extended info
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "document_name": document_name,
            "strategy_used": strategy,
            "confidence_score": confidence,
            "cost_estimate": cost,
            "processing_time": processing_time,
            "escalated": escalated,
            "escalation_path": escalation_path if escalation_path else [],
        }
        
        self.ledger.log_extended(entry)
