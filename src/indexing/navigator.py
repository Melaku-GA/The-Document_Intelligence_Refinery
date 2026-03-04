"""
Navigator for PageIndex - Provides navigation and search capabilities.
"""

from typing import Any, Dict, List, Optional

from src.models.page_index import PageIndex, PageIndexNode


class PageIndexNavigator:
    """
    Provides navigation and search capabilities over PageIndex.
    
    Allows users to:
    - Find sections by title
    - Navigate to specific pages
    - Get section context
    - Search by entity
    """
    
    def __init__(self, index: PageIndex):
        self.index = index
    
    def find_section_by_title(self, title: str) -> Optional[PageIndexNode]:
        """
        Find a section by exact or partial title match.
        
        Args:
            title: Section title to search for
            
        Returns:
            PageIndexNode if found, None otherwise
        """
        title_lower = title.lower()
        
        # Search through all root sections and their children
        for section in self.index.root_sections:
            result = self._search_node(section, title_lower)
            if result:
                return result
        
        return None
    
    def _search_node(self, node: PageIndexNode, title_lower: str) -> Optional[PageIndexNode]:
        """Recursively search for title match."""
        if title_lower in node.title.lower():
            return node
        
        for child in node.child_sections:
            result = self._search_node(child, title_lower)
            if result:
                return result
        
        return None
    
    def get_section_at_page(self, page_number: int) -> Optional[PageIndexNode]:
        """
        Get the section that contains a specific page.
        
        Args:
            page_number: Page number to look up
            
        Returns:
            PageIndexNode containing the page, None if not found
        """
        return self.index.find_section_at_page(page_number)
    
    def get_page_range_for_section(self, title: str) -> Optional[tuple]:
        """
        Get the page range for a specific section.
        
        Args:
            title: Section title
            
        Returns:
            Tuple of (page_start, page_end) or None if not found
        """
        section = self.find_section_by_title(title)
        if section:
            return (section.page_start, section.page_end)
        return None
    
    def get_navigation_path(self, page_number: int) -> List[PageIndexNode]:
        """
        Get the navigation path to a specific page.
        
        Returns list of sections from root to the section containing the page.
        
        Args:
            page_number: Page number to navigate to
            
        Returns:
            List of PageIndexNodes representing the path
        """
        path = []
        
        # Find the immediate section
        section = self.get_section_at_page(page_number)
        if not section:
            return path
        
        # Build path by finding ancestors
        path.append(section)
        
        return path
    
    def search_by_entity(self, entity: str) -> List[PageIndexNode]:
        """
        Find sections containing a specific entity.
        
        Args:
            entity: Entity string to search for
            
        Returns:
            List of sections containing the entity
        """
        entity_lower = entity.lower()
        results = []
        
        for section in self.index.root_sections:
            self._search_entities(section, entity_lower, results)
        
        return results
    
    def _search_entities(
        self,
        node: PageIndexNode,
        entity_lower: str,
        results: List[PageIndexNode]
    ):
        """Recursively search for entities in sections."""
        # Check key entities
        for key_entity in node.key_entities:
            if entity_lower in key_entity.lower():
                results.append(node)
                break
        
        # Check children
        for child in node.child_sections:
            self._search_entities(child, entity_lower, results)
    
    def get_data_type_sections(self, data_type: str) -> List[PageIndexNode]:
        """
        Find sections that contain a specific data type.
        
        Args:
            data_type: Data type to search for (e.g., 'financial', 'statistical')
            
        Returns:
            List of sections with that data type
        """
        results = []
        
        for section in self.index.root_sections:
            self._search_data_types(section, data_type.lower(), results)
        
        return results
    
    def _search_data_types(
        self,
        node: PageIndexNode,
        data_type_lower: str,
        results: List[PageIndexNode]
    ):
        """Recursively search for data types in sections."""
        if data_type_lower in [dt.lower() for dt in node.data_types_present]:
            results.append(node)
        
        for child in node.child_sections:
            self._search_data_types(child, data_type_lower, results)
    
    def get_document_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the document structure.
        
        Returns:
            Dictionary with document statistics
        """
        total_sections = self._count_sections(self.index.root_sections)
        
        # Collect all data types
        all_data_types = set()
        all_entities = []
        
        for section in self.index.root_sections:
            self._collect_metadata(section, all_data_types, all_entities)
        
        return {
            "document_name": self.index.document_name,
            "total_pages": self.index.total_pages,
            "total_sections": total_sections,
            "data_types": list(all_data_types),
            "entity_count": len(all_entities)
        }
    
    def _count_sections(self, nodes: List[PageIndexNode]) -> int:
        """Count total sections including children."""
        count = len(nodes)
        for node in nodes:
            count += self._count_sections(node.child_sections)
        return count
    
    def _collect_metadata(
        self,
        node: PageIndexNode,
        data_types: set,
        entities: List[str]
    ):
        """Collect metadata from sections."""
        data_types.update(node.data_types_present)
        entities.extend(node.key_entities)
        
        for child in node.child_sections:
            self._collect_metadata(child, data_types, entities)
    
    def render_toc(self, max_level: int = 2) -> str:
        """
        Render a text-based table of contents.
        
        Args:
            max_level: Maximum depth to render
            
        Returns:
            Formatted table of contents string
        """
        lines = [f"Table of Contents - {self.index.document_name}"]
        lines.append(f"Total Pages: {self.index.total_pages}")
        lines.append("")
        
        for section in self.index.root_sections:
            self._render_node_toc(section, lines, 0, max_level)
        
        return '\n'.join(lines)
    
    def _render_node_toc(
        self,
        node: PageIndexNode,
        lines: List[str],
        depth: int,
        max_level: int
    ):
        """Render a node to the TOC."""
        if depth > max_level:
            return
        
        # Indentation
        indent = "  " * depth
        
        # Section title and page range
        line = f"{indent}{node.title} (p.{node.page_start}-{node.page_end})"
        lines.append(line)
        
        # Render children
        for child in node.child_sections:
            self._render_node_toc(child, lines, depth + 1, max_level)
