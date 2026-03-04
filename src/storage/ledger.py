import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class ExtractionLedger:
    """
    Ledger for tracking all extraction operations.
    
    Logs to .refinery/extraction_ledger.jsonl with:
    - strategy_used
    - confidence_score
    - cost_estimate
    - processing_time
    - escalation details
    """
    
    def __init__(self, path: str = ".refinery/extraction_ledger.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        
    def log(
        self,
        document_name: str,
        strategy: str,
        confidence: float,
        cost: float,
        processing_time: float = 0.0,
        escalated: bool = False,
    ):
        """
        Log an extraction attempt.
        
        Args:
            document_name: Name of the document
            strategy: Strategy used (fast_text, mineru_layout, vision_vlm)
            confidence: Confidence score from extraction
            cost: Estimated cost
            processing_time: Time taken for extraction
            escalated: Whether this was an escalation from another strategy
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "document_name": document_name,
            "strategy_used": strategy,
            "confidence_score": confidence,
            "cost_estimate": cost,
            "processing_time": processing_time,
            "escalated": escalated,
        }
        
        self._write_entry(entry)
        
    def log_extended(self, entry: Dict[str, Any]):
        """
        Log an extended entry with additional fields.
        
        Args:
            entry: Full entry dictionary
        """
        # Ensure timestamp
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.utcnow().isoformat() + "Z"
            
        self._write_entry(entry)
        
    def _write_entry(self, entry: Dict[str, Any]):
        """Write a single JSONL entry."""
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
            
    def get_recent(self, limit: int = 10) -> list:
        """
        Get recent extraction entries.
        
        Args:
            limit: Number of recent entries to return
            
        Returns:
            List of recent extraction entries
        """
        if not self.path.exists():
            return []
            
        entries = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
                    
        return entries[-limit:]
        
    def get_by_document(self, document_name: str) -> list:
        """
        Get all entries for a specific document.
        
        Args:
            document_name: Name of the document
            
        Returns:
            List of extraction entries for the document
        """
        if not self.path.exists():
            return []
            
        entries = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if entry.get("document_name") == document_name:
                        entries.append(entry)
                        
        return entries
        
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about extractions.
        
        Returns:
            Dictionary with extraction statistics
        """
        if not self.path.exists():
            return {
                "total_extractions": 0,
                "avg_confidence": 0.0,
                "escalation_rate": 0.0,
            }
            
        entries = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
                    
        if not entries:
            return {
                "total_extractions": 0,
                "avg_confidence": 0.0,
                "escalation_rate": 0.0,
            }
            
        total = len(entries)
        avg_confidence = sum(e.get("confidence_score", 0) for e in entries) / total
        escalated = sum(1 for e in entries if e.get("escalated", False))
        
        return {
            "total_extractions": total,
            "avg_confidence": avg_confidence,
            "escalation_rate": escalated / total if total > 0 else 0.0,
            "strategies_used": list(set(e.get("strategy_used", "") for e in entries)),
        }
