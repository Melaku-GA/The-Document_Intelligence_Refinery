"""
Unit tests for PageIndex.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.page_index import PageIndex, PageIndexNode


class TestPageIndexNode:
    """Test cases for PageIndexNode."""

    def test_node_creation(self):
        """Test PageIndexNode can be created."""
        node = PageIndexNode(
            title="Introduction",
            page_start=1,
            page_end=5
        )
        
        assert node.title == "Introduction"
        assert node.page_start == 1
        assert node.page_end == 5

    def test_add_child(self):
        """Test adding child nodes."""
        parent = PageIndexNode(title="Main", page_start=1, page_end=10)
        child = PageIndexNode(title="Section 1", page_start=1, page_end=3)
        
        parent.add_child(child)
        
        assert len(parent.child_sections) == 1

    def test_get_all_pages(self):
        """Test getting all pages in a node and children."""
        parent = PageIndexNode(title="Main", page_start=1, page_end=10)
        child1 = PageIndexNode(title="Section 1", page_start=1, page_end=3)
        child2 = PageIndexNode(title="Section 2", page_start=4, page_end=6)
        
        parent.add_child(child1)
        parent.add_child(child2)
        
        pages = parent.get_all_pages()
        
        assert len(pages) == 6
        assert 1 in pages
        assert 6 in pages

    def test_find_section_at_page(self):
        """Test finding section at a specific page."""
        parent = PageIndexNode(title="Main", page_start=1, page_end=10)
        child = PageIndexNode(title="Section 1", page_start=3, page_end=5)
        
        parent.add_child(child)
        
        found = parent.find_section_at_page(4)
        
        assert found is not None
        assert found.title == "Section 1"


class TestPageIndex:
    """Test cases for PageIndex."""

    def test_page_index_initialization(self):
        """Test PageIndex can be initialized."""
        index = PageIndex(
            document_name="test.pdf",
            total_pages=10
        )
        
        assert index.document_name == "test.pdf"
        assert index.total_pages == 10

    def test_add_section(self):
        """Test adding sections to PageIndex."""
        index = PageIndex(
            document_name="test.pdf",
            total_pages=10
        )
        
        section = PageIndexNode(title="Chapter 1", page_start=1, page_end=5)
        index.add_section(section)
        
        assert len(index.root_sections) == 1

    def test_find_section_at_page(self):
        """Test finding section at a specific page."""
        index = PageIndex(
            document_name="test.pdf",
            total_pages=10
        )
        
        section = PageIndexNode(title="Chapter 1", page_start=1, page_end=5)
        index.add_section(section)
        
        found = index.find_section_at_page(3)
        
        assert found is not None
        assert found.title == "Chapter 1"

    def test_navigation_tree(self):
        """Test getting navigation tree."""
        index = PageIndex(
            document_name="test.pdf",
            total_pages=10
        )
        
        section = PageIndexNode(title="Chapter 1", page_start=1, page_end=5)
        index.add_section(section)
        
        tree = index.get_navigation_tree()
        
        assert tree["document_name"] == "test.pdf"
        assert tree["total_pages"] == 10
        assert len(tree["sections"]) == 1


class TestPageIndexMetadata:
    """Test cases for PageIndex metadata."""

    def test_metadata_storage(self):
        """Test metadata can be stored."""
        index = PageIndex(
            document_name="test.pdf",
            total_pages=10
        )
        
        index.metadata["created_at"] = "2026-03-04"
        index.metadata["extraction_method"] = "Strategy B"
        
        assert index.metadata["created_at"] == "2026-03-04"
        assert index.metadata["extraction_method"] == "Strategy B"

    def test_metadata_in_navigation_tree(self):
        """Test metadata is included in navigation tree."""
        index = PageIndex(
            document_name="test.pdf",
            total_pages=10
        )
        
        index.metadata["version"] = "1.0"
        
        tree = index.get_navigation_tree()
        
        assert tree["metadata"]["version"] == "1.0"


class TestHierarchicalStructure:
    """Test cases for hierarchical structure."""

    def test_nested_sections(self):
        """Test nested section hierarchy."""
        root = PageIndexNode(title="Document", page_start=1, page_end=20)
        chapter1 = PageIndexNode(title="Chapter 1", page_start=1, page_end=10, level=1)
        section1 = PageIndexNode(title="Section 1.1", page_start=1, page_end=5, level=2)
        
        chapter1.add_child(section1)
        root.add_child(chapter1)
        
        assert len(root.child_sections) == 1
        assert len(chapter1.child_sections) == 1

    def test_multiple_chapters(self):
        """Test multiple chapters at same level."""
        index = PageIndex(
            document_name="book.pdf",
            total_pages=100
        )
        
        index.add_section(PageIndexNode(title="Chapter 1", page_start=1, page_end=20))
        index.add_section(PageIndexNode(title="Chapter 2", page_start=21, page_end=40))
        index.add_section(PageIndexNode(title="Chapter 3", page_start=41, page_end=60))
        
        assert len(index.root_sections) == 3


class TestKeyEntities:
    """Test cases for key entities."""

    def test_key_entities_storage(self):
        """Test key entities can be stored in nodes."""
        node = PageIndexNode(
            title="Finance Section",
            page_start=10,
            page_end=15
        )
        
        node.key_entities = ["revenue", "profit", "loss", "budget"]
        
        assert len(node.key_entities) == 4
        assert "revenue" in node.key_entities


class TestDataTypes:
    """Test cases for data types."""

    def test_data_types_present(self):
        """Test data types can be stored in nodes."""
        node = PageIndexNode(
            title="Data Section",
            page_start=5,
            page_end=8
        )
        
        node.data_types_present = ["financial", "statistical"]
        
        assert "financial" in node.data_types_present
        assert "statistical" in node.data_types_present


class TestEdgeCases:
    """Test cases for edge cases."""

    def test_empty_index(self):
        """Test operations on empty index."""
        index = PageIndex(
            document_name="empty.pdf",
            total_pages=0
        )
        
        found = index.find_section_at_page(1)
        
        assert found is None

    def test_page_out_of_range(self):
        """Test finding section when page is out of range."""
        index = PageIndex(
            document_name="test.pdf",
            total_pages=10
        )
        
        section = PageIndexNode(title="Chapter 1", page_start=1, page_end=5)
        index.add_section(section)
        
        found = index.find_section_at_page(99)
        
        assert found is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
