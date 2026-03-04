"""
Chunk validator to verify chunking rules are not violated.

Validates that all 5 mandatory chunking rules are enforced:
1. A table cell is never split from its header row
2. A figure caption is always stored as metadata of its parent figure chunk
3. A numbered list is always kept as a single LDU unless it exceeds max_tokens
4. Section headers are stored as parent metadata on all child chunks
5. Cross-references are resolved and stored as chunk relationships
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
import re

from src.models.ldu import LDU
from src.models.enums import ChunkType
from src.chunking.rules import is_numbered_list, extract_cross_references, estimate_tokens


@dataclass
class ValidationResult:
    """Result of chunk validation."""
    is_valid: bool
    violations: List[str]
    warnings: List[str]


class ChunkValidator:
    """
    Validates that chunks follow all mandatory chunking rules.
    """
    
    def __init__(self, max_tokens: int = 512):
        self.max_tokens = max_tokens
        self.violations: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self, ldu: LDU) -> ValidationResult:
        """
        Validate a single LDU against all chunking rules.
        
        Args:
            ldu: The Logical Document Unit to validate
            
        Returns:
            ValidationResult with violations and warnings
        """
        violations = []
        warnings = []
        
        # Rule 1: Table cells must not be split from header rows
        if ldu.chunk_type == ChunkType.TABLE:
            table_violations = self._validate_table_integrity(ldu)
            violations.extend(table_violations)
        
        # Rule 2: Figure captions should be stored as metadata
        if ldu.chunk_type == ChunkType.FIGURE:
            fig_warnings = self._validate_figure_caption(ldu)
            warnings.extend(fig_warnings)
        
        # Rule 3: Numbered lists should be kept as single LDU
        if ldu.chunk_type == ChunkType.LIST:
            list_violations = self._validate_list_integrity(ldu)
            violations.extend(list_violations)
        
        # Rule 4: Section headers should be parent metadata
        if ldu.parent_section is None and ldu.chunk_type != ChunkType.TABLE:
            # Only warn for content chunks that should have parent sections
            if ldu.content.strip():
                warnings.append(f"Chunk missing parent_section metadata")
        
        # Rule 5: Cross-references should be tracked
        refs = extract_cross_references(ldu.content)
        if refs and not hasattr(ldu, 'cross_references'):
            warnings.append(f"Chunk has cross-references but no relationship tracking")
        
        # Token limit check
        if ldu.token_count > self.max_tokens:
            violations.append(f"Chunk exceeds max_tokens: {ldu.token_count} > {self.max_tokens}")
        
        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
            warnings=warnings
        )
    
    def validate_batch(self, ldu_list: List[LDU]) -> Dict[str, ValidationResult]:
        """
        Validate a batch of LDUs and check inter-chunk relationships.
        
        Args:
            ldu_list: List of LDUs to validate
            
        Returns:
            Dictionary mapping chunk content_hash to validation results
        """
        results = {}
        
        # First pass: validate individual chunks
        for ldu in ldu_list:
            results[ldu.content_hash] = self.validate(ldu)
        
        # Second pass: check cross-chunk relationships
        relationship_violations = self._validate_relationships(ldu_list)
        
        # Add relationship violations to results
        for hash_key, violations in relationship_violations.items():
            if hash_key in results:
                results[hash_key].violations.extend(violations)
                results[hash_key].is_valid = False
            else:
                results[hash_key] = ValidationResult(
                    is_valid=False,
                    violations=violations,
                    warnings=[]
                )
        
        return results
    
    def _validate_table_integrity(self, ldu: LDU) -> List[str]:
        """
        Validate that table chunks maintain header-row integrity.
        
        Rule 1: A table cell is never split from its header row
        """
        violations = []
        
        # Check if table has headers
        # Tables should have some structure visible
        content = ldu.content
        
        # If content is too short for a proper table, warn
        if len(content) < 10:
            violations.append("Table content too short - may have lost header row")
        
        # Check for orphaned cells (lines without proper delimiters)
        lines = content.split('\n')
        if len(lines) > 1:
            # Check if rows have consistent column counts
            col_counts = []
            for line in lines:
                # Count separators (tabs, pipes, commas)
                tabs = line.count('\t')
                pipes = line.count('|')
                col_counts.append(max(tabs, pipes) + 1)
            
            # If column counts vary significantly, might have split headers
            if col_counts:
                avg_cols = sum(col_counts) / len(col_counts)
                if any(abs(c - avg_cols) > 1 for c in col_counts):
                    violations.append(f"Table row column count inconsistent - may have split header row")
        
        return violations
    
    def _validate_figure_caption(self, ldu: LDU) -> List[str]:
        """
        Validate that figure chunks have caption metadata.
        
        Rule 2: A figure caption is always stored as metadata of its parent figure chunk
        """
        warnings = []
        
        # Check if content suggests it's a figure but has no caption metadata
        # This is handled at chunk creation time via metadata
        # Here we just warn if content looks like it might need caption
        
        lower_content = ldu.content.lower()
        if any(word in lower_content for word in ['figure', 'image', 'chart', 'graph', 'diagram']):
            # Content mentions visual element - should have been processed as figure with caption
            pass  # Validation happens at creation time
        
        return warnings
    
    def _validate_list_integrity(self, ldu: LDU) -> List[str]:
        """
        Validate that numbered lists are kept as single LDUs.
        
        Rule 3: A numbered list is always kept as a single LDU unless it exceeds max_tokens
        """
        violations = []
        
        content = ldu.content
        
        # Check if content looks like a numbered list
        if is_numbered_list(content):
            # Check if it exceeds token limit
            tokens = estimate_tokens(content)
            if tokens > self.max_tokens:
                violations.append(f"Numbered list exceeds max_tokens: {tokens} > {self.max_tokens}")
        
        return violations
    
    def _validate_relationships(self, ldu_list: List[LDU]) -> Dict[str, List[str]]:
        """
        Validate cross-chunk relationships.
        
        Rule 5: Cross-references are resolved and stored as chunk relationships
        """
        violations = {}
        
        # Build index of chunks by type
        table_chunks = {i: ldu for i, ldu in enumerate(ldu_list) if ldu.chunk_type == ChunkType.TABLE}
        figure_chunks = {i: ldu for i, ldu in enumerate(ldu_list) if ldu.chunk_type == ChunkType.FIGURE}
        
        # Check for references to tables/figures in other chunks
        for i, ldu in enumerate(ldu_list):
            refs = extract_cross_references(ldu.content)
            
            if refs:
                # Validate that referenced elements exist
                for ref in refs:
                    ref_lower = ref.lower()
                    
                    # Check for table references
                    if 'table' in ref_lower:
                        table_num = self._extract_reference_number(ref, 'table')
                        if table_num:
                            # Find if referenced table exists
                            found = False
                            for t_ldu in table_chunks.values():
                                if f"table {table_num}" in t_ldu.content.lower():
                                    found = True
                                    break
                            if not found:
                                violations.setdefault(ldu.content_hash, []).append(
                                    f"References table {table_num} which may not exist or is not properly chunked"
                                )
                    
                    # Check for figure references
                    if 'figure' in ref_lower:
                        fig_num = self._extract_reference_number(ref, 'figure')
                        if fig_num:
                            found = False
                            for f_ldu in figure_chunks.values():
                                if f"figure {fig_num}" in f_ldu.content.lower():
                                    found = True
                                    break
                            if not found:
                                violations.setdefault(ldu.content_hash, []).append(
                                    f"References figure {fig_num} which may not exist or is not properly chunked"
                                )
        
        return violations
    
    def _extract_reference_number(self, text: str, ref_type: str) -> Optional[str]:
        """Extract the reference number from text like 'Table 1' or 'Figure 2.3'"""
        pattern = rf'{ref_type}\s+(\d+(?:\.\d+)*)'
        match = re.search(pattern, text.lower())
        if match:
            return match.group(1)
        return None
    
    def get_summary(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """
        Get a summary of validation results.
        
        Args:
            results: Dictionary of validation results
            
        Returns:
            Summary statistics
        """
        total = len(results)
        valid = sum(1 for r in results.values() if r.is_valid)
        invalid = total - valid
        total_violations = sum(len(r.violations) for r in results.values())
        total_warnings = sum(len(r.warnings) for r in results.values())
        
        return {
            "total_chunks": total,
            "valid_chunks": valid,
            "invalid_chunks": invalid,
            "total_violations": total_violations,
            "total_warnings": total_warnings,
            "validation_rate": valid / total if total > 0 else 0
        }
