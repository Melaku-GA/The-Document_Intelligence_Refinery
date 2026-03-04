from src.models.document_profile import DocumentProfile
from src.models.enums import ExtractionCostTier
from src.strategies.fast_text import FastTextExtractor
from src.strategies.base import ExtractionResult
from src.storage.ledger import ExtractionLedger

from src.strategies.mineru_layout import MinerULayoutExtractor


#class ExtractionRouter:
   # def __init__(self, confidence_threshold: float = 0.65):
   #     self.fast_text = FastTextExtractor()
    #    # layout_aware and vision will be plugged later
     #   self.confidence_threshold = confidence_threshold
      #  self.ledger = ExtractionLedger()
        
class ExtractionRouter:
    def __init__(self, confidence_threshold: float = 0.65):
        self.fast_text = FastTextExtractor()
        self.mineru = MinerULayoutExtractor()
        self.confidence_threshold = confidence_threshold
        self.ledger = ExtractionLedger()

    def extract(self, pdf_path: str, profile: DocumentProfile) -> ExtractionResult:
        """
        Routes extraction based on DocumentProfile and confidence.
        """
        # ---- Strategy A: Fast Text ----
        if profile.estimated_extraction_cost == ExtractionCostTier.FAST_TEXT_SUFFICIENT:
            result = self.fast_text.extract(pdf_path)

            escalated = result.confidence < self.confidence_threshold
            self.ledger.log(
                document_name=profile.document_name,
                strategy="fast_text",
                confidence=result.confidence,
                cost=result.cost_estimate,
                escalated=escalated,
            )

            if not escalated:
                return result

            # Escalation path (Strategy B placeholder)
            return self._escalate(pdf_path, profile)

        # ---- Direct escalation paths ----
        return self._escalate(pdf_path, profile)

    #def _escalate(self, pdf_path: str, profile: DocumentProfile) -> ExtractionResult:
        """
        Placeholder escalation logic.
        """
       # raise NotImplementedError(
      #      "Escalation triggered: layout-aware / vision extractor not yet implemented."
   #     )

    def _escalate(self, pdf_path: str, profile: DocumentProfile) -> ExtractionResult:
        result = self.mineru.extract(pdf_path)

        self.ledger.log(
            document_name=profile.document_name,
            strategy="mineru_layout",
            confidence=result.confidence,
            cost=result.cost_estimate,
            escalated=False,
        )

        return result