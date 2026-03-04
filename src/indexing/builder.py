"""
PageIndex tree builder - Creates hierarchical navigation structure.

Builds a smart table of contents from chunked documents.
"""

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from src.models.ldu import LDU
from src.models.page_index import PageIndex, PageIndexNode
from src.models.enums import ChunkType
from src.chunking.rules import detect_data_types, is_section_header


@dataclass
class IndexingConfig:
    """Configuration for the indexer."""
    output_dir: str = ".refinery/pageindex"
    min_section_pages: int = 1
    max_depth: int = 4  # Maximum section nesting level
    extract_entities: bool = True
    
    # Entity extraction patterns
    entity_patterns = {
        'organization': r'\b[A-Z][a-zA-Z]*(?:Corporation|Company|Bank|Ministry|Agency|Institute|Authority)\b',
        'financial': r'\b(?:Birr|ETB|\$|USD|EUR)\s*[\d,]+(?:\.\d{2})?\b',
        'date': r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
        'number': r'\b\d+(?:\.\d+)?(?:\s*%|\s*billion|\s*million|\s*thousand)?\b',
    }


class PageIndexBuilder:
    """
    Builds hierarchical navigation structure from LDUs.
    
    Creates a smart table of contents with:
    - Section titles and page ranges
    - Child sections
    - Key entities per section
    - Data types present
    - Optional summaries
    """
    
    def __init__(self, config: Optional[IndexingConfig] = None):
        self.config = config or IndexingConfig()
    
    def build(self, ldu_list: List[LDU], document_name: str, total_pages: int) -> PageIndex:
        """
        Build PageIndex from list of LDUs.
        
        Args:
            ldu_list: List of Logical Document Units
            document_name: Name of the source document
            total_pages: Total number of pages in the document
            
        Returns:
            PageIndex with hierarchical navigation structure
        """
        index = PageIndex(
            document_name=document_name,
            total_pages=total_pages,
            metadata={"build_config": self.config.__dict__}
        )
        
        # Group LDUs by section
        sections = self._identify_sections(ldu_list)
        
        # Build hierarchical structure
        root_nodes = self._build_tree(sections, ldu_list)
        
        # Add sections to index
        for node in root_nodes:
            index.add_section(node)
        
        return index
    
    def _identify_sections(self, ldu_list: List[LDU]) -> List[Dict[str, Any]]:
        """
        Identify sections from LDUs based on section headers and content.
        
        Returns list of section dictionaries with:
        - title
        - page_start
        - page_end
        - level
        - ldu_indices
        """
        sections = []
        current_section = None
        
        for i, ldu in enumerate(ldu_list):
            # Check if this is a section header
            is_header, header_text = is_section_header(ldu.content)
            
            if is_header:
                # Determine section level from numbering
                level = self._get_section_level(ldu.content)
                
                # Close previous section if exists
                if current_section:
                    current_section['page_end'] = ldu.page_refs[0].page_number - 1
                
                # Start new section
                current_section = {
                    'title': header_text,
                    'page_start': ldu.page_refs[0].page_number,
                    'page_end': 0,  # Will be updated
                    'level': level,
                    'ldu_indices': [i]
                }
                sections.append(current_section)
            elif current_section:
                # Add to current section
                current_section['ldu_indices'].append(i)
        
        # Close last section
        if current_section:
            if current_section['page_end'] == 0:
                last_ldu = ldu_list[-1]
                current_section['page_end'] = last_ldu.page_refs[-1].page_number if last_ldu.page_refs else current_section['page_start']
        
        return sections
    
    def _get_section_level(self, text: str) -> int:
        """Determine section level from numbering (1, 1.1, 1.1.1, etc.)."""
        # Pattern for numbered sections
        match = re.match(r'^(\d+(\.\d+)*)', text.strip())
        if match:
            num_dots = match.group(1).count('.')
            return num_dots + 1
        
        # ALL CAPS = top level
        if text.isupper():
            return 1
        
        # Default to top level
        return 1
    
    def _build_tree(
        self,
        sections: List[Dict[str, Any]],
        ldu_list: List[LDU]
    ) -> List[PageIndexNode]:
        """
        Build hierarchical tree from flat section list.
        """
        if not sections:
            return []
        
        # Build nodes
        nodes = []
        for section in sections:
            node = self._create_node(section, ldu_list)
            nodes.append(node)
        
        # Organize into hierarchy
        root_nodes = []
        stack = []  # Stack of (level, node) tuples
        
        for node in nodes:
            # Pop stack until we find parent
            while stack and stack[-1][0] >= node.level:
                stack.pop()
            
            if stack:
                # Add as child
                parent = stack[-1][1]
                parent.add_child(node)
            else:
                # Top level
                root_nodes.append(node)
            
            stack.append((node.level, node))
        
        return root_nodes
    
    def _create_node(
        self,
        section: Dict[str, Any],
        ldu_list: List[LDU]
    ) -> PageIndexNode:
        """Create a PageIndexNode from section data."""
        title = section['title']
        page_start = section['page_start']
        page_end = section.get('page_end', page_start)
        level = section.get('level', 1)
        ldu_indices = section.get('ldu_indices', [])
        
        # Get content for entity extraction
        content_parts = []
        for idx in ldu_indices:
            if idx < len(ldu_list):
                content_parts.append(ldu_list[idx].content)
        
        full_content = ' '.join(content_parts)
        
        # Extract key entities
        key_entities = []
        if self.config.extract_entities:
            key_entities = self._extract_entities(full_content)
        
        # Detect data types
        data_types = detect_data_types(full_content)
        
        return PageIndexNode(
            title=title,
            page_start=page_start,
            page_end=page_end,
            level=level,
            key_entities=key_entities[:10],  # Limit to 10 entities
            data_types_present=data_types,
            summary=None  # Could add LLM-based summarization
        )
    
    def _extract_entities(self, content: str) -> List[str]:
        """Extract key entities from content."""
        entities = []
        
        for entity_type, pattern in self.config.entity_patterns.items():
            matches = re.findall(pattern, content)
            entities.extend(matches)
        
        # Deduplicate and limit
        unique_entities = list(set(entities))[:20]
        return unique_entities
    
    def save(self, index: PageIndex, document_name: str):
        """Save PageIndex to JSON file."""
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        # Create document ID
        doc_id = document_name.replace('.pdf', '').replace(' ', '_')
        output_path = os.path.join(self.config.output_dir, f"{doc_id}.json")
        
        # Get navigation tree
        tree = index.get_navigation_tree()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(tree, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def load(self, document_name: str) -> Optional[PageIndex]:
        """Load PageIndex from JSON file."""
        doc_id = document_name.replace('.pdf', '').replace(' ', '_')
        output_path = os.path.join(self.config.output_dir, f"{doc_id}.json")
        
        if not os.path.exists(output_path):
            return None
        
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reconstruct PageIndex
        index = PageIndex(
            document_name=data['document_name'],
            total_pages=data['total_pages'],
            metadata=data.get('metadata', {})
        )
        
        # Reconstruct nodes
        for section_data in data.get('sections', []):
            node = self._reconstruct_node(section_data)
            index.add_section(node)
        
        return index
    
    def _reconstruct_node(self, data: Dict[str, Any]) -> PageIndexNode:
        """Reconstruct a PageIndexNode from dictionary."""
        node = PageIndexNode(
            title=data['title'],
            page_start=data['page_start'],
            page_end=data['page_end'],
            level=data.get('level', 1),
            key_entities=data.get('key_entities', []),
            summary=data.get('summary'),
            data_types_present=data.get('data_types_present', [])
        )
        
        # Reconstruct children
        for child_data in data.get('child_sections', []):
            child_node = self._reconstruct_node(child_data)
            node.add_child(child_node)
        
        return node
