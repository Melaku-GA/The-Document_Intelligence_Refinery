"""
Content hashing utilities for RAG-optimized knowledge chunks.

Provides deterministic hashing for LDUs to enable provenance verification
even when pages shift in the document.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional


def generate_content_hash(content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate a deterministic hash for chunk content.
    
    Args:
        content: The text content of the chunk
        metadata: Optional metadata to include in hash calculation
        
    Returns:
        A SHA-256 hash string (truncated to 16 chars for brevity)
    """
    # Normalize content: lowercase, strip whitespace
    normalized = content.lower().strip()
    
    # Create a stable representation including metadata
    hash_input = normalized
    if metadata:
        # Sort keys for deterministic ordering
        meta_str = json.dumps(metadata, sort_keys=True, default=str)
        hash_input = f"{normalized}|{meta_str}"
    
    # Generate SHA-256 hash
    full_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    
    # Return first 16 characters for brevity while maintaining uniqueness
    return full_hash[:16]


def generate_spatial_hash(page_number: int, bbox: Optional[Dict[str, float]]) -> str:
    """
    Generate a spatial hash for bounding box-based provenance.
    
    This enables tracking content position even if the page shifts.
    
    Args:
        page_number: The page number (1-indexed)
        bbox: Bounding box with x0, y0, x1, y1 coordinates
        
    Returns:
        A spatial hash string
    """
    if bbox is None:
        return f"p{page_number}_none"
    
    # Round coordinates to reduce noise from OCR variations
    x0_r = round(bbox.get('x0', 0), 2)
    y0_r = round(bbox.get('y0', 0), 2)
    x1_r = round(bbox.get('x1', 0), 2)
    y1_r = round(bbox.get('y1', 0), 2)
    
    spatial_str = f"p{page_number}_{x0_r}_{y0_r}_{x1_r}_{y1_r}"
    return hashlib.md5(spatial_str.encode('utf-8')).hexdigest()[:12]


def generate_chunk_id(document_name: str, content_hash: str, sequence: int) -> str:
    """
    Generate a unique chunk ID combining document, content, and sequence.
    
    Args:
        document_name: Name of the source document
        content_hash: The content hash
        sequence: Sequence number of this chunk in the document
        
    Returns:
        A unique chunk identifier
    """
    # Create short document identifier
    doc_id = document_name.replace('.pdf', '').replace(' ', '_')[:20]
    return f"{doc_id}_{content_hash}_{sequence:04d}"


def verify_provenance(
    content: str,
    stored_hash: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Verify that content matches a stored provenance hash.
    
    Args:
        content: The content to verify
        stored_hash: The previously stored hash
        metadata: Optional metadata used in original hash
        
    Returns:
        True if hash matches, False otherwise
    """
    computed_hash = generate_content_hash(content, metadata)
    return computed_hash == stored_hash
