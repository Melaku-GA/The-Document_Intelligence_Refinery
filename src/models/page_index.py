"""
PageIndex model for hierarchical navigation structure.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class PageIndexNode(BaseModel):
    """A node in the hierarchical page index tree."""
    title: str
    page_start: int
    page_end: int
    child_sections: List["PageIndexNode"] = []
    key_entities: List[str] = []
    summary: Optional[str] = None
    data_types_present: List[str] = []
    level: int = 1  # 1 = top-level section, 2 = subsection, etc.
    
    def add_child(self, child: "PageIndexNode"):
        """Add a child section to this node."""
        self.child_sections.append(child)
    
    def get_all_pages(self) -> List[int]:
        """Get all page numbers covered by this node and children."""
        pages = list(range(self.page_start, self.page_end + 1))
        for child in self.child_sections:
            pages.extend(child.get_all_pages())
        return sorted(set(pages))
    
    def find_section_at_page(self, page_number: int) -> Optional["PageIndexNode"]:
        """Find the section that contains a specific page."""
        if self.page_start <= page_number <= self.page_end:
            # Check children first
            for child in self.child_sections:
                result = child.find_section_at_page(page_number)
                if result:
                    return result
            return self
        return None


class PageIndex(BaseModel):
    """Hierarchical navigation structure (smart table of contents)."""
    document_name: str
    total_pages: int
    root_sections: List[PageIndexNode] = []
    metadata: Dict[str, Any] = {}
    
    def add_section(self, section: PageIndexNode):
        """Add a top-level section to the index."""
        self.root_sections.append(section)
    
    def find_section_at_page(self, page_number: int) -> Optional[PageIndexNode]:
        """Find the section that contains a specific page."""
        for section in self.root_sections:
            result = section.find_section_at_page(page_number)
            if result:
                return result
        return None
    
    def get_navigation_tree(self) -> Dict[str, Any]:
        """Get a dictionary representation of the navigation tree."""
        return {
            "document_name": self.document_name,
            "total_pages": self.total_pages,
            "sections": [self._node_to_dict(s) for s in self.root_sections],
            "metadata": self.metadata
        }
    
    def _node_to_dict(self, node: PageIndexNode) -> Dict[str, Any]:
        """Convert a node to dictionary format."""
        return {
            "title": node.title,
            "page_start": node.page_start,
            "page_end": node.page_end,
            "level": node.level,
            "key_entities": node.key_entities,
            "summary": node.summary,
            "data_types_present": node.data_types_present,
            "child_sections": [self._node_to_dict(c) for c in node.child_sections]
        }
