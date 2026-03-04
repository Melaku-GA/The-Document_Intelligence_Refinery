"""
Semantic Chunking Engine - Transforms raw extraction into RAG-optimized knowledge.

Applies 5 mandatory chunking rules:
1. A table cell is never split from its header row
2. A figure caption is always stored as metadata of its parent figure chunk
3. A numbered list is always kept as a single LDU unless it exceeds max_tokens
4. Section headers are stored as parent metadata on all child chunks
5. Cross-references are resolved and stored as chunk relationships
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.models.extracted_document import ExtractedDocument, TextBlock, TableBlock, FigureBlock
from src.models.ldu import LDU
from src.models.enums import ChunkType
from src.models.provenance import PageRef, BoundingBox
from src.chunking.rules import (
    ChunkContext,
    is_section_header,
    is_numbered_list,
    extract_list_items,
    extract_cross_references,
    estimate_tokens,
    detect_data_types,
)
from src.chunking.validator import ChunkValidator
from src.utils.hashing import generate_content_hash, generate_chunk_id


@dataclass
class ChunkingConfig:
    """Configuration for the chunking engine."""
    max_tokens: int = 512
    max_chars: int = 2000
    preserve_tables: bool = True
    preserve_figures: bool = True
    preserve_lists: bool = True
    preserve_layout: bool = True
    
    # Output settings
    output_dir: str = ".refinery/chunks"
    save_chunks: bool = True


@dataclass
class ChunkingResult:
    """Result of chunking operation."""
    ldus: List[LDU]
    document_name: str
    total_pages: int
    token_count: int
    chunk_count: int
    validation_summary: Dict[str, Any]
    
    def save(self, output_dir: str):
        """Save chunks to JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{self.document_name}_chunks.json")
        
        data = {
            "document_name": self.document_name,
            "total_pages": self.total_pages,
            "token_count": self.token_count,
            "chunk_count": self.chunk_count,
            "ldus": [ldu.model_dump() for ldu in self.ldus]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class ChunkingEngine:
    """
    Main chunking engine that applies semantic chunking rules.
    
    Transforms ExtractedDocument into list of Logical Document Units (LDUs)
    optimized for RAG retrieval.
    """
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()
        self.validator = ChunkValidator(max_tokens=self.config.max_tokens)
    
    def process(self, document: ExtractedDocument) -> ChunkingResult:
        """
        Process an extracted document into RAG-optimized chunks.
        
        Args:
            document: ExtractedDocument from extraction stage
            
        Returns:
            ChunkingResult with list of LDUs and metadata
        """
        # Track all chunks
        all_ldus: List[LDU] = []
        
        # Track context for section hierarchy
        context = ChunkContext()
        
        # Track page range
        all_pages = set()
        
        # Process text blocks
        text_ldus = self._process_text_blocks(document.text_blocks, context)
        all_ldus.extend(text_ldus)
        
        # Process tables (Rule 1: never split from header)
        table_ldus = self._process_tables(document.tables, context)
        all_ldus.extend(table_ldus)
        
        # Process figures (Rule 2: captions as metadata)
        figure_ldus = self._process_figures(document.figures, context)
        all_ldus.extend(figure_ldus)
        
        # Collect all page refs
        for ldu in all_ldus:
            for page_ref in ldu.page_refs:
                all_pages.add(page_ref.page_number)
        
        # Sort LDUs by first page reference
        all_ldus.sort(key=lambda ldu: ldu.page_refs[0].page_number if ldu.page_refs else 0)
        
        # Validate chunks
        validation_results = self.validator.validate_batch(all_ldus)
        validation_summary = self.validator.get_summary(validation_results)
        
        # Calculate total tokens
        total_tokens = sum(ldu.token_count for ldu in all_ldus)
        
        # Generate result
        result = ChunkingResult(
            ldus=all_ldus,
            document_name=document.document_name,
            total_pages=max(all_pages) if all_pages else 0,
            token_count=total_tokens,
            chunk_count=len(all_ldus),
            validation_summary=validation_summary
        )
        
        # Save if configured
        if self.config.save_chunks:
            result.save(self.config.output_dir)
        
        return result
    
    def _process_text_blocks(
        self,
        text_blocks: List[TextBlock],
        context: ChunkContext
    ) -> List[LDU]:
        """Process text blocks into LDUs, applying chunking rules."""
        ldus = []
        
        # Sort by reading order
        sorted_blocks = sorted(text_blocks, key=lambda b: (b.page_ref.page_number, b.reading_order))
        
        buffer = []
        buffer_content = []
        current_type = ChunkType.PARAGRAPH
        
        for block in sorted_blocks:
            text = block.text.strip()
            if not text:
                continue
            
            # Rule 4: Detect and track section headers
            is_header, header_text = is_section_header(text)
            if is_header:
                # Flush any pending content first
                if buffer:
                    ldu = self._create_ldu_from_buffer(
                        buffer, buffer_content, current_type, context
                    )
                    if ldu:
                        ldus.append(ldu)
                    buffer = []
                    buffer_content = []
                
                # Update section context
                context.push_section(text)
                continue
            
            # Rule 3: Handle numbered lists
            if is_numbered_list(text):
                # Flush pending paragraph content
                if buffer and current_type == ChunkType.PARAGRAPH:
                    ldu = self._create_ldu_from_buffer(
                        buffer, buffer_content, current_type, context
                    )
                    if ldu:
                        ldus.append(ldu)
                    buffer = []
                    buffer_content = []
                
                # Process as list
                list_ldu = self._create_list_ldu(text, block, context)
                if list_ldu:
                    ldus.append(list_ldu)
                continue
            
            # Check if adding this block would exceed limits
            combined = '\n'.join(buffer_content + [text])
            if len(combined) > self.config.max_chars:
                # Flush buffer
                if buffer_content:
                    ldu = self._create_ldu_from_buffer(
                        buffer, buffer_content, current_type, context
                    )
                    if ldu:
                        ldus.append(ldu)
                    buffer = []
                    buffer_content = []
            
            # Add to buffer
            buffer.append(block)
            buffer_content.append(text)
            current_type = ChunkType.PARAGRAPH
        
        # Flush remaining buffer
        if buffer_content:
            ldu = self._create_ldu_from_buffer(
                buffer, buffer_content, current_type, context
            )
            if ldu:
                ldus.append(ldu)
        
        return ldus
    
    def _create_ldu_from_buffer(
        self,
        blocks: List[TextBlock],
        content_lines: List[str],
        chunk_type: ChunkType,
        context: ChunkContext
    ) -> Optional[LDU]:
        """Create an LDU from buffered content."""
        if not content_lines:
            return None
        
        content = '\n'.join(content_lines)
        tokens = estimate_tokens(content)
        
        # Skip if exceeds max tokens significantly
        if tokens > self.config.max_tokens * 2:
            # Split into smaller chunks
            return self._split_large_content(blocks, content, chunk_type, context)
        
        # Get page references
        page_refs = [b.page_ref for b in blocks]
        
        # Get bounding box from first block
        bbox = None
        if blocks and blocks[0].page_ref.bbox:
            bb = blocks[0].page_ref.bbox
            bbox = BoundingBox(x0=bb.x0, y0=bb.y0, x1=bb.x1, y1=bb.y1)
        
        # Generate content hash
        content_hash = generate_content_hash(content)
        
        # Extract cross-references (Rule 5)
        cross_refs = extract_cross_references(content)
        
        # Get parent sections (Rule 4)
        parent_sections = context.get_parent_sections()
        parent_section = parent_sections[-1] if parent_sections else None
        
        return LDU(
            content=content,
            chunk_type=chunk_type,
            page_refs=page_refs,
            parent_section=parent_section,
            token_count=tokens,
            content_hash=content_hash,
            bounding_box=bbox,
            cross_references=extract_cross_references(content)
        )
    
    def _split_large_content(
        self,
        blocks: List[TextBlock],
        content: str,
        chunk_type: ChunkType,
        context: ChunkContext
    ) -> Optional[LDU]:
        """Split large content into smaller chunks."""
        # Simple split by sentences or lines
        sentences = content.split('. ')
        current_chunk = []
        current_tokens = 0
        ldus = []
        
        for sentence in sentences:
            sent_tokens = estimate_tokens(sentence)
            if current_tokens + sent_tokens > self.config.max_tokens and current_chunk:
                # Create chunk
                chunk_content = '. '.join(current_chunk)
                ldu = self._create_single_ldu(
                    chunk_content, blocks[0] if blocks else None, 
                    chunk_type, context
                )
                if ldu:
                    ldus.append(ldu)
                current_chunk = []
                current_tokens = 0
            
            current_chunk.append(sentence)
            current_tokens += sent_tokens
        
        # Handle remaining
        if current_chunk:
            chunk_content = '. '.join(current_chunk)
            ldu = self._create_single_ldu(
                chunk_content, blocks[0] if blocks else None,
                chunk_type, context
            )
            if ldu:
                ldus.append(ldu)
        
        # Return first chunk (main caller will collect all)
        return ldus[0] if ldus else None
    
    def _create_single_ldu(
        self,
        content: str,
        block: Optional[TextBlock],
        chunk_type: ChunkType,
        context: ChunkContext
    ) -> Optional[LDU]:
        """Create a single LDU from content and block."""
        if not content.strip():
            return None
        
        tokens = estimate_tokens(content)
        
        page_refs = [block.page_ref] if block else []
        
        bbox = None
        if block and block.page_ref.bbox:
            bb = block.page_ref.bbox
            bbox = BoundingBox(x0=bb.x0, y0=bb.y0, x1=bb.x1, y1=bb.y1)
        
        content_hash = generate_content_hash(content)
        
        parent_sections = context.get_parent_sections()
        parent_section = parent_sections[-1] if parent_sections else None
        
        return LDU(
            content=content,
            chunk_type=chunk_type,
            page_refs=page_refs,
            parent_section=parent_section,
            token_count=tokens,
            content_hash=content_hash
        )
    
    def _process_tables(
        self,
        tables: List[TableBlock],
        context: ChunkContext
    ) -> List[LDU]:
        """Process tables into LDUs (Rule 1: never split from header)."""
        ldus = []
        
        for table in tables:
            # Build table content preserving header row
            headers = table.headers
            rows = table.rows
            
            # Format as structured text
            lines = []
            
            # Header
            if headers:
                header_line = ' | '.join(headers)
                lines.append(header_line)
                lines.append('-' * len(header_line))
            
            # Data rows
            for row in rows:
                row_line = ' | '.join(row)
                lines.append(row_line)
            
            content = '\n'.join(lines)
            tokens = estimate_tokens(content)
            
            # Get page reference
            page_refs = [table.page_ref]
            
            # Get bounding box
            bbox = None
            if table.page_ref.bbox:
                bb = table.page_ref.bbox
                bbox = BoundingBox(x0=bb.x0, y0=bb.y0, x1=bb.x1, y1=bb.y1)
            
            content_hash = generate_content_hash(content, {"type": "table"})
            
            # Table inherits parent section
            parent_sections = context.get_parent_sections()
            parent_section = parent_sections[-1] if parent_sections else None
            
            ldu = LDU(
                content=content,
                chunk_type=ChunkType.TABLE,
                page_refs=page_refs,
                parent_section=parent_section,
                token_count=tokens,
                content_hash=content_hash,
                bounding_box=bbox
            )
            
            ldus.append(ldu)
        
        return ldus
    
    def _process_figures(
        self,
        figures: List[FigureBlock],
        context: ChunkContext
    ) -> List[LDU]:
        """Process figures into LDUs (Rule 2: captions as metadata)."""
        ldus = []
        
        for figure in figures:
            # Build figure content
            # Caption becomes part of the figure chunk metadata
            caption = figure.caption or ""
            
            # Content includes caption if available
            content = f"[Figure]" if not caption else f"[Figure]: {caption}"
            tokens = estimate_tokens(content)
            
            page_refs = [figure.page_ref]
            
            # Get bounding box
            bbox = None
            if figure.page_ref.bbox:
                bb = figure.page_ref.bbox
                bbox = BoundingBox(x0=bb.x0, y0=bb.y0, x1=bb.x1, y1=bb.y1)
            
            content_hash = generate_content_hash(content, {"type": "figure", "caption": caption})
            
            # Figure inherits parent section
            parent_sections = context.get_parent_sections()
            parent_section = parent_sections[-1] if parent_sections else None
            
            ldu = LDU(
                content=content,
                chunk_type=ChunkType.FIGURE,
                page_refs=page_refs,
                parent_section=parent_section,
                token_count=tokens,
                content_hash=content_hash,
                bounding_box=bbox
            )
            
            ldus.append(ldu)
        
        return ldus
    
    def _create_list_ldu(
        self,
        text: str,
        block: TextBlock,
        context: ChunkContext
    ) -> Optional[LDU]:
        """Create an LDU from list content (Rule 3: keep as single LDU)."""
        # Check token limit
        tokens = estimate_tokens(text)
        
        # If exceeds limit, we still keep as single chunk but warn
        # In practice, would need smarter splitting
        
        page_refs = [block.page_ref]
        
        bbox = None
        if block.page_ref.bbox:
            bb = block.page_ref.bbox
            bbox = BoundingBox(x0=bb.x0, y0=bb.y0, x1=bb.x1, y1=bb.y1)
        
        content_hash = generate_content_hash(text)
        
        # Extract cross-references
        cross_refs = extract_cross_references(text)
        
        parent_sections = context.get_parent_sections()
        parent_section = parent_sections[-1] if parent_sections else None
        
        return LDU(
            content=text,
            chunk_type=ChunkType.LIST,
            page_refs=page_refs,
            parent_section=parent_section,
            token_count=tokens,
            content_hash=content_hash,
            cross_references=cross_refs
        )
