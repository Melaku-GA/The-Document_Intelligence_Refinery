"""
Chunking rules for semantic document processing.

Implements the 5 mandatory chunking rules:
1. A table cell is never split from its header row
2. A figure caption is always stored as metadata of its parent figure chunk
3. A numbered list is always kept as a single LDU unless it exceeds max_tokens
4. Section headers are stored as parent metadata on all child chunks
5. Cross-references are resolved and stored as chunk relationships
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
import re

from src.models.extracted_document import ExtractedDocument, TextBlock, TableBlock, FigureBlock
from src.models.ldu import LDU
from src.models.enums import ChunkType
from src.models.provenance import PageRef, BoundingBox


# Token estimation (approximate: 1 token ≈ 4 characters)
TOKEN_ESTIMATE_RATIO = 4


class ChunkingRules:
    """Chunking rules for semantic document processing."""
    
    def __init__(self, max_chars: int = 800, min_chars: int = 100):
        self.max_chars = max_chars
        self.min_chars = min_chars
    
    @staticmethod
    def detect_boundaries(text: str) -> Set['ChunkBoundaryType']:
        """Detect chunk boundaries in text."""
        from src.models.enums import ChunkBoundaryType
        boundaries = set()
        
        # Check for paragraph boundary (double newline)
        if '\n\n' in text:
            boundaries.add(ChunkBoundaryType.PARAGRAPH)
        
        # Check for sentence boundary (period followed by space)
        if '. ' in text:
            boundaries.add(ChunkBoundaryType.SENTENCE)
        
        # Check for section boundary (numbered sections)
        import re
        if re.search(r'^\d+(\.\d+)*\.', text, re.MULTILINE):
            boundaries.add(ChunkBoundaryType.SECTION)
        
        # Check for table boundary
        if '|' in text or re.search(r'\|.*\|', text):
            boundaries.add(ChunkBoundaryType.TABLE)
        
        return boundaries
    
    @staticmethod
    def split_by_size(text: str, max_size: int, min_size: int = 50) -> List[str]:
        """Split text into chunks by size."""
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + max_size, len(text))
            
            # Try to split at sentence boundary
            if end < len(text):
                # Find last period or newline
                for i in range(end - 1, max(end - 100, start), -1):
                    if text[i] in '.!':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end
        
        return chunks
    
    @staticmethod
    def semantic_chunk(text: str, max_chars: int = 800) -> List[str]:
        """Perform semantic chunking on text."""
        # Use simple size-based chunking for now
        return ChunkingRules.split_by_size(text, max_chars)
    
    @staticmethod
    def split_with_overlap(text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text with overlap between chunks."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start = end - overlap
        
        return chunks


@dataclass
class ChunkContext:
    """Context information for chunking decisions."""
    current_section: Optional[str] = None
    section_stack: List[str] = None
    
    def __init__(self):
        self.current_section = None
        self.section_stack = []
    
    def push_section(self, section: str):
        self.section_stack.append(section)
        self.current_section = section
    
    def pop_section(self):
        if self.section_stack:
            self.section_stack.pop()
            self.current_section = self.section_stack[-1] if self.section_stack else None
    
    def get_parent_sections(self) -> List[str]:
        """Get all parent sections for metadata inheritance."""
        return self.section_stack.copy()


def is_section_header(text: str) -> Tuple[bool, Optional[str]]:
    """
    Detect if text is a section header.
    
    Returns:
        Tuple of (is_header, header_text)
    """
    text = text.strip()
    
    # Pattern 1: Numbered sections like "1.", "1.1", "2.3.4", etc.
    numbered_pattern = r'^(\d+(\.\d+)*)\.?\s+'
    match = re.match(numbered_pattern, text)
    if match:
        return True, text
    
    # Pattern 2: ALL CAPS headers (at least 3 chars)
    if text.isupper() and len(text) >= 3 and not text.isdigit():
        return True, text
    
    # Pattern 3: Title case with common header keywords
    header_keywords = [
        'introduction', 'background', 'summary', 'conclusion',
        'methodology', 'results', 'discussion', 'recommendations',
        'appendix', 'references', 'acknowledgements'
    ]
    lower_text = text.lower()
    for keyword in header_keywords:
        if lower_text.startswith(keyword):
            return True, text
    
    return False, None


def is_numbered_list(text: str) -> bool:
    """
    Detect if text is part of a numbered list.
    
    Handles: 1., 2), 3., a), b), (i), etc.
    """
    patterns = [
        r'^\d+[\.\)]\s+',           # 1. or 1)
        r'^[a-z][\.\)]\s+',          # a. or a)
        r'^\([ivxlcdm]+\)\s+',       # (i) or (iv)
        r'^\([A-Z]\)\s+',            # (A) or (B)
    ]
    
    for pattern in patterns:
        if re.match(pattern, text.strip()):
            return True
    return False


def extract_list_items(text: str) -> List[str]:
    """
    Extract individual items from a numbered list.
    
    Returns list of individual items.
    """
    lines = text.split('\n')
    items = []
    
    for line in lines:
        line = line.strip()
        # Remove the list prefix
        cleaned = re.sub(r'^(?:\d+[\.\)]|[a-z][\.\)]|\([ivxlcdm]+\)|\([A-Z]\))\s+', '', line)
        if cleaned:
            items.append(cleaned)
    
    return items


def estimate_tokens(text: str) -> int:
    """Estimate token count from text (approximate)."""
    return len(text) // TOKEN_ESTIMATE_RATIO


def extract_cross_references(text: str) -> List[str]:
    """
    Extract cross-references from text.
    
    Finds patterns like: "see Table 1", "Figure 2.3", "section 4.2", etc.
    """
    patterns = [
        r'(?:see|refer to|as shown in|as illustrated in)\s+(?:table|figure|section|appendix)\s+(\d+(?:\.\d+)*)',
        r'(?:table|figure|section|appendix)\s+(\d+(?:\.\d+)*)',
    ]
    
    references = []
    text_lower = text.lower()
    
    for pattern in patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            # Get the full reference
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            context = text[start:end]
            references.append(context)
    
    return references


def detect_data_types(content: str) -> List[str]:
    """
    Detect data types present in content.
    
    Returns list of detected types: 'financial', 'statistical', 'textual', etc.
    """
    content_lower = content.lower()
    detected = []
    
    # Financial indicators
    financial_patterns = ['birr', 'etb', '$', 'usd', 'eur', 'budget', 'revenue', 'expense', 'expenditure', 'balance', 'profit', 'loss']
    if any(p in content_lower for p in financial_patterns):
        detected.append('financial')
    
    # Statistical indicators
    stat_patterns = ['percent', '%', 'average', 'total', 'sum', 'count', 'rate', 'index', 'growth', 'decline']
    if any(p in content_lower for p in stat_patterns):
        detected.append('statistical')
    
    # Temporal indicators
    temp_patterns = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december', 'fiscal year', 'quarter', 'q1', 'q2', 'q3', 'q4']
    if any(p in content_lower for p in temp_patterns):
        detected.append('temporal')
    
    # Entity indicators (names, places, organizations)
    entity_patterns = ['corporation', 'company', 'bank', 'ministry', 'department', 'agency', 'institute']
    if any(p in content_lower for p in entity_patterns):
        detected.append('entity')
    
    # Default to textual if nothing specific detected
    if not detected:
        detected.append('textual')
    
    return detected
