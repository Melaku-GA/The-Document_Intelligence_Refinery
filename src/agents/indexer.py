"""
Indexer Agent - Manages PageIndex operations and navigation.

Provides programmatic access to document navigation structure.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models.ldu import LDU
from src.models.page_index import PageIndex, PageIndexNode
from src.indexing.builder import PageIndexBuilder, IndexingConfig
from src.indexing.navigator import PageIndexNavigator


class IndexerAgent:
    """
    Agent for managing PageIndex and navigation.
    
    Provides:
    - Building PageIndex from LDUs
    - Loading/saving indexes
    - Navigation queries
    - Search by entity/data type
    """
    
    def __init__(self, config: Optional[IndexingConfig] = None):
        self.config = config or IndexingConfig()
        self.builder = PageIndexBuilder(self.config)
        self._current_index: Optional[PageIndex] = None
        self._current_navigator: Optional[PageIndexNavigator] = None
    
    def build_index(
        self,
        ldu_list: List[LDU],
        document_name: str,
        total_pages: int,
        save: bool = True
    ) -> PageIndex:
        """
        Build a PageIndex from LDUs.
        
        Args:
            ldu_list: List of Logical Document Units
            document_name: Name of the source document
            total_pages: Total number of pages
            save: Whether to save the index to disk
            
        Returns:
            Built PageIndex
        """
        self._current_index = self.builder.build(ldu_list, document_name, total_pages)
        self._current_navigator = PageIndexNavigator(self._current_index)
        
        if save:
            self.builder.save(self._current_index, document_name)
        
        return self._current_index
    
    def load_index(self, document_name: str) -> Optional[PageIndexNavigator]:
        """
        Load a PageIndex from disk.
        
        Args:
            document_name: Name of the document
            
        Returns:
            PageIndexNavigator if found, None otherwise
        """
        self._current_index = self.builder.load(document_name)
        
        if self._current_index:
            self._current_navigator = PageIndexNavigator(self._current_index)
            return self._current_navigator
        
        return None
    
    def get_navigator(self) -> Optional[PageIndexNavigator]:
        """Get the current navigator."""
        return self._current_navigator
    
    def find_section(self, title: str) -> Optional[PageIndexNode]:
        """Find a section by title."""
        if self._current_navigator:
            return self._current_navigator.find_section_by_title(title)
        return None
    
    def get_section_at_page(self, page_number: int) -> Optional[PageIndexNode]:
        """Get the section containing a specific page."""
        if self._current_navigator:
            return self._current_navigator.get_section_at_page(page_number)
        return None
    
    def search_entities(self, entity: str) -> List[PageIndexNode]:
        """Search for sections containing an entity."""
        if self._current_navigator:
            return self._current_navigator.search_by_entity(entity)
        return []
    
    def get_data_type_sections(self, data_type: str) -> List[PageIndexNode]:
        """Find sections with specific data types."""
        if self._current_navigator:
            return self._current_navigator.get_data_type_sections(data_type)
        return []
    
    def get_document_summary(self) -> Dict[str, Any]:
        """Get document structure summary."""
        if self._current_navigator:
            return self._current_navigator.get_document_summary()
        return {}
    
    def render_toc(self, max_level: int = 2) -> str:
        """Render table of contents."""
        if self._current_navigator:
            return self._current_navigator.render_toc(max_level)
        return "No index loaded"


def create_index_from_ldus(
    ldus: List[LDU],
    document_name: str,
    total_pages: int,
    output_dir: str = ".refinery/pageindex"
) -> str:
    """
    Convenience function to create an index from LDUs.
    
    Args:
        ldus: List of LDUs
        document_name: Name of the document
        total_pages: Total pages
        output_dir: Output directory
        
    Returns:
        Path to saved index
    """
    config = IndexingConfig(output_dir=output_dir)
    agent = IndexerAgent(config)
    
    index = agent.build_index(ldus, document_name, total_pages, save=True)
    
    return os.path.join(output_dir, f"{document_name.replace('.pdf', '').replace(' ', '_')}.json")


def load_index(document_name: str, index_dir: str = ".refinery/pageindex") -> Optional[PageIndexNavigator]:
    """
    Convenience function to load an index.
    
    Args:
        document_name: Name of the document
        index_dir: Directory containing indexes
        
    Returns:
        PageIndexNavigator if found
    """
    config = IndexingConfig(output_dir=index_dir)
    agent = IndexerAgent(config)
    
    return agent.load_index(document_name)
