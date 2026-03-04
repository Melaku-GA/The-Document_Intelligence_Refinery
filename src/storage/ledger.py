import json
from pathlib import Path
from datetime import datetime


class ExtractionLedger:
    def __init__(self, path=".refinery/extraction_ledger.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        document_name: str,
        strategy: str,
        confidence: float,
        cost: float,
        escalated: bool,
    ):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "document_name": document_name,
            "strategy_used": strategy,
            "confidence_score": confidence,
            "cost_estimate": cost,
            "escalated": escalated,
        }

        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")