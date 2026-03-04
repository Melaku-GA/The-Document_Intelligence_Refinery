"""
FactTable: SQLite-based storage for extracted key-value facts from financial documents.

Provides structured querying over extracted facts like:
- Revenue: $4.2B
- Date: Q3 2024
- Growth rate: 15%
- etc.
"""

import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ExtractedFact:
    """A single extracted fact from a document."""
    fact_id: str
    document_name: str
    category: str  # e.g., "financial", "temporal", "metric"
    key: str  # e.g., "revenue", "date", "growth_rate"
    value: str  # e.g., "$4.2B", "Q3 2024", "15%"
    normalized_value: Optional[float] = None  # For numeric comparisons
    page_number: int = 0
    bbox: Optional[Tuple[float, float, float, float]] = None
    confidence: float = 1.0
    context: str = ""  # Surrounding text for context
    extracted_at: str = ""


class FactTable:
    """
    SQLite-backed fact table for structured querying of extracted facts.
    
    Supports:
    - Storing key-value facts from financial documents
    - SQL-like queries for precise fact retrieval
    - Fact verification for audit mode
    """
    
    def __init__(self, db_path: str = ".refinery/fact_table.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                fact_id TEXT PRIMARY KEY,
                document_name TEXT NOT NULL,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                normalized_value REAL,
                page_number INTEGER DEFAULT 0,
                bbox_json TEXT,
                confidence REAL DEFAULT 1.0,
                context TEXT,
                extracted_at TEXT NOT NULL
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_document 
            ON facts(document_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_category 
            ON facts(category)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_key 
            ON facts(key)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_value 
            ON facts(value)
        """)
        
        conn.commit()
        conn.close()
    
    def add_fact(self, fact: ExtractedFact):
        """Add a single fact to the table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        bbox_json = json.dumps(fact.bbox) if fact.bbox else None
        
        cursor.execute("""
            INSERT OR REPLACE INTO facts 
            (fact_id, document_name, category, key, value, normalized_value,
             page_number, bbox_json, confidence, context, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fact.fact_id,
            fact.document_name,
            fact.category,
            fact.key,
            fact.value,
            fact.normalized_value,
            fact.page_number,
            bbox_json,
            fact.confidence,
            fact.context,
            fact.extracted_at or datetime.utcnow().isoformat() + "Z"
        ))
        
        conn.commit()
        conn.close()
    
    def add_facts(self, facts: List[ExtractedFact]):
        """Add multiple facts to the table."""
        for fact in facts:
            self.add_fact(fact)
    
    def query(
        self,
        document_name: Optional[str] = None,
        category: Optional[str] = None,
        key: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> List[ExtractedFact]:
        """
        Query facts with filters.
        
        Args:
            document_name: Filter by document name
            category: Filter by category (e.g., "financial")
            key: Filter by key name
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of matching ExtractedFact objects
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM facts WHERE 1=1"
        params = []
        
        if document_name:
            query += " AND document_name = ?"
            params.append(document_name)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if key:
            query += " AND key LIKE ?"
            params.append(f"%{key}%")
        
        query += " AND confidence >= ?"
        params.append(min_confidence)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_fact(row) for row in rows]
    
    def search_facts(self, search_term: str) -> List[ExtractedFact]:
        """
        Search facts by key or value.
        
        Args:
            search_term: Term to search for
            
        Returns:
            List of matching facts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term}%"
        
        cursor.execute("""
            SELECT * FROM facts 
            WHERE key LIKE ? OR value LIKE ? OR context LIKE ?
            ORDER BY confidence DESC
        """, (search_pattern, search_pattern, search_pattern))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_fact(row) for row in rows]
    
    def verify_fact(
        self,
        claim_key: str,
        claim_value: str,
        document_name: Optional[str] = None,
        tolerance: float = 0.01
    ) -> Tuple[bool, Optional[ExtractedFact]]:
        """
        Verify a claim against stored facts.
        
        Args:
            claim_key: The key being claimed (e.g., "revenue")
            claim_value: The value being claimed (e.g., "$4.2B")
            document_name: Optional document to check
            tolerance: Tolerance for numeric comparison
            
        Returns:
            Tuple of (is_verified, matching_fact or None)
        """
        # Normalize the claim value
        claim_normalized = self._normalize_value(claim_value)
        
        # Search for matching facts
        facts = self.query(document_name=document_name, key=claim_key)
        
        for fact in facts:
            # Check exact match
            if fact.value.lower() == claim_value.lower():
                return True, fact
            
            # Check normalized numeric match
            if claim_normalized is not None and fact.normalized_value is not None:
                if abs(claim_normalized - fact.normalized_value) <= tolerance:
                    return True, fact
            
            # Check if claim is contained in fact value
            if claim_value.lower() in fact.value.lower():
                return True, fact
        
        return False, None
    
    def get_financial_facts(self, document_name: str) -> List[ExtractedFact]:
        """Get all financial facts for a document."""
        return self.query(document_name=document_name, category="financial")
    
    def get_all_keys(self, document_name: Optional[str] = None) -> List[str]:
        """Get all unique keys, optionally filtered by document."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if document_name:
            cursor.execute(
                "SELECT DISTINCT key FROM facts WHERE document_name = ?",
                (document_name,)
            )
        else:
            cursor.execute("SELECT DISTINCT key FROM facts")
        
        rows = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in rows]
    
    def _row_to_fact(self, row: tuple) -> ExtractedFact:
        """Convert a database row to an ExtractedFact."""
        bbox_json = row[7]
        bbox = json.loads(bbox_json) if bbox_json else None
        
        return ExtractedFact(
            fact_id=row[0],
            document_name=row[1],
            category=row[2],
            key=row[3],
            value=row[4],
            normalized_value=row[5],
            page_number=row[6],
            bbox=tuple(bbox) if bbox else None,
            confidence=row[8],
            context=row[9],
            extracted_at=row[10]
        )
    
    def _normalize_value(self, value: str) -> Optional[float]:
        """
        Normalize a value string to a float for comparison.
        
        Handles: $4.2B, 15%, 1,234,567, etc.
        """
        # Remove currency symbols and whitespace
        cleaned = value.strip()
        
        # Handle billions/millions
        multiplier = 1.0
        if cleaned.lower().endswith('b'):
            multiplier = 1_000_000_000
            cleaned = cleaned[:-1]
        elif cleaned.lower().endswith('m'):
            multiplier = 1_000_000
            cleaned = cleaned[:-1]
        elif cleaned.lower().endswith('k'):
            multiplier = 1_000
            cleaned = cleaned[:-1]
        
        # Remove percentage
        if cleaned.endswith('%'):
            cleaned = cleaned[:-1]
        
        # Remove currency symbols
        cleaned = cleaned.replace('$', '').replace(',', '').strip()
        
        try:
            return float(cleaned) * multiplier
        except ValueError:
            return None
    
    def extract_facts_from_text(
        self,
        text: str,
        document_name: str,
        page_number: int = 0,
        bbox: Optional[Tuple[float, float, float, float]] = None
    ) -> List[ExtractedFact]:
        """
        Extract facts from text using pattern matching.
        
        Args:
            text: Text to extract facts from
            document_name: Source document name
            page_number: Page number
            bbox: Bounding box
            
        Returns:
            List of extracted facts
        """
        facts = []
        
        # Financial patterns
        financial_patterns = [
            (r'revenue[:\s]+[\$€£]?([\d,\.]+)([BMKbmk]?)', 'revenue'),
            (r'profit[:\s]+[\$€£]?([\d,\.]+)([BMKbmk]?)', 'profit'),
            (r'loss[:\s]+[\$€£]?([\d,\.]+)([BMKbmk]?)', 'loss'),
            (r'assets?[:\s]+[\$€£]?([\d,\.]+)([BMKbmk]?)', 'assets'),
            (r'liabilities?[:\s]+[\$€£]?([\d,\.]+)([BMKbmk]?)', 'liabilities'),
            (r'equity[:\s]+[\$€£]?([\d,\.]+)([BMKbmk]?)', 'equity'),
            (r'cash[:\s]+[\$€£]?([\d,\.]+)([BMKbmk]?)', 'cash'),
            (r'debt[:\s]+[\$€£]?([\d,\.]+)([BMKbmk]?)', 'debt'),
        ]
        
        # Temporal patterns
        temporal_patterns = [
            (r'Q([1-4])[\s]*(\d{4})', 'quarter'),
            (r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', 'month'),
            (r'(FY|fiscal year)[\s]*(\d{4})', 'fiscal_year'),
            (r'(\d{4})[\s]*[\-\/]?[\s]*(\d{4})?', 'year'),
        ]
        
        # Metric patterns
        metric_patterns = [
            (r'growth[:\s]+([\d,\.]+)%', 'growth_rate'),
            (r'margin[:\s]+([\d,\.]+)%', 'margin'),
            (r'rate[:\s]+([\d,\.]+)%', 'rate'),
            (r'ratio[:\s]+([\d,\.]+)%?', 'ratio'),
        ]
        
        import hashlib
        
        # Extract financial facts
        for pattern, key in financial_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value_str = match.group(0).split(':')[-1].strip()
                normalized = self._normalize_value(value_str)
                
                fact_id = hashlib.md5(
                    f"{document_name}:{key}:{value_str}:{page_number}".encode()
                ).hexdigest()
                
                facts.append(ExtractedFact(
                    fact_id=fact_id,
                    document_name=document_name,
                    category="financial",
                    key=key,
                    value=value_str,
                    normalized_value=normalized,
                    page_number=page_number,
                    bbox=bbox,
                    confidence=0.85,
                    context=text[max(0, match.start()-50):min(len(text), match.end()+50)]
                ))
        
        # Extract temporal facts
        for pattern, key in temporal_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value_str = match.group(0)
                
                fact_id = hashlib.md5(
                    f"{document_name}:{key}:{value_str}:{page_number}".encode()
                ).hexdigest()
                
                facts.append(ExtractedFact(
                    fact_id=fact_id,
                    document_name=document_name,
                    category="temporal",
                    key=key,
                    value=value_str,
                    normalized_value=None,
                    page_number=page_number,
                    bbox=bbox,
                    confidence=0.9,
                    context=text[max(0, match.start()-50):min(len(text), match.end()+50)]
                ))
        
        # Extract metric facts
        for pattern, key in metric_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value_str = match.group(1) + '%'
                
                fact_id = hashlib.md5(
                    f"{document_name}:{key}:{value_str}:{page_number}".encode()
                ).hexdigest()
                
                facts.append(ExtractedFact(
                    fact_id=fact_id,
                    document_name=document_name,
                    category="metric",
                    key=key,
                    value=value_str,
                    normalized_value=float(match.group(1)),
                    page_number=page_number,
                    bbox=bbox,
                    confidence=0.8,
                    context=text[max(0, match.start()-50):min(len(text), match.end()+50)]
                ))
        
        return facts
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the fact table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total facts
        cursor.execute("SELECT COUNT(*) FROM facts")
        total = cursor.fetchone()[0]
        
        # Facts by category
        cursor.execute("""
            SELECT category, COUNT(*) 
            FROM facts 
            GROUP BY category
        """)
        by_category = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Facts by document
        cursor.execute("""
            SELECT document_name, COUNT(*) 
            FROM facts 
            GROUP BY document_name
        """)
        by_document = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Unique keys
        cursor.execute("SELECT COUNT(DISTINCT key) FROM facts")
        unique_keys = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_facts": total,
            "by_category": by_category,
            "by_document": by_document,
            "unique_keys": unique_keys
        }
