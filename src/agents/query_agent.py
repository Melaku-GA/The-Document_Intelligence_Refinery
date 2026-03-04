"""
Query Agent: LangGraph-style agent for querying document corpus.

Provides three main tools:
- pageindex_navigate: Navigate the PageIndex tree to locate sections
- semantic_search: Vector retrieval over the chunk store
- structured_query: SQL-like queries over extracted fact tables

Every answer includes provenance: document name, page number, bounding box.
"""

import json
import re
import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.indexing.navigator import PageIndexNavigator
from src.models.answer import Answer, Citation
from src.models.chunk import DocumentChunk
from src.models.embedding import EmbeddedChunk
from src.models.page_index import PageIndex
from src.models.provenance import BoundingBox, PageRef, ProvenanceChain
from src.storage.fact_table import ExtractedFact, FactTable
from src.storage.vector_store import VectorStore, InMemoryVectorStore
from src.embeddings.embedder import Embedder, DummyEmbedder


class QueryTool(str, Enum):
    """Available query tools."""
    PAGEINDEX_NAVIGATE = "pageindex_navigate"
    SEMANTIC_SEARCH = "semantic_search"
    STRUCTURED_QUERY = "structured_query"


@dataclass
class ProvenanceSource:
    """Source information for a query result."""
    document_name: str
    page_number: int
    bbox: Optional[Tuple[float, float, float, float]] = None
    chunk_id: Optional[str] = None
    section_title: Optional[str] = None
    confidence: float = 1.0


@dataclass
class QueryResult:
    """Result from a query tool."""
    tool: QueryTool
    content: str
    provenance: List[ProvenanceSource]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditResult:
    """Result of auditing a claim."""
    claim: str
    is_verified: bool
    verified_fact: Optional[ExtractedFact] = None
    sources: List[ProvenanceSource] = field(default_factory=list)
    status: str = ""  # "verified", "unverified", "partially_verified"
    explanation: str = ""


class PageIndexTool:
    """Tool for navigating the PageIndex tree."""
    
    def __init__(self, page_index: Optional[PageIndex] = None):
        self.page_index = page_index
        self.navigator = None
        if page_index:
            self.navigator = PageIndexNavigator(page_index)
    
    def set_page_index(self, page_index: PageIndex):
        """Set or update the page index."""
        self.page_index = page_index
        self.navigator = PageIndexNavigator(page_index)
    
    def find_section(self, query: str) -> QueryResult:
        """Find a section by title or keyword."""
        if not self.navigator:
            return QueryResult(
                tool=QueryTool.PAGEINDEX_NAVIGATE,
                content="No page index loaded",
                provenance=[]
            )
        
        # Try to find section by title
        section = self.navigator.find_section_by_title(query)
        
        if section:
            content = f"Found section: {section.title}\n"
            content += f"Pages: {section.page_start}-{section.page_end}\n"
            if section.summary:
                content += f"Summary: {section.summary}\n"
            if section.key_entities:
                content += f"Key entities: {', '.join(section.key_entities)}\n"
            
            provenance = [ProvenanceSource(
                document_name=self.page_index.document_name,
                page_number=section.page_start,
                section_title=section.title
            )]
            
            return QueryResult(
                tool=QueryTool.PAGEINDEX_NAVIGATE,
                content=content,
                provenance=provenance,
                metadata={"page_start": section.page_start, "page_end": section.page_end}
            )
        
        # Try searching by entity
        entities = self.navigator.search_by_entity(query)
        if entities:
            content = f"Found {len(entities)} sections containing '{query}':\n"
            provenance = []
            
            for entity in entities[:5]:  # Limit to 5
                content += f"\n- {entity.title} (pages {entity.page_start}-{entity.page_end})"
                provenance.append(ProvenanceSource(
                    document_name=self.page_index.document_name,
                    page_number=entity.page_start,
                    section_title=entity.title
                ))
            
            return QueryResult(
                tool=QueryTool.PAGEINDEX_NAVIGATE,
                content=content,
                provenance=provenance
            )
        
        return QueryResult(
            tool=QueryTool.PAGEINDEX_NAVIGATE,
            content=f"No section found matching '{query}'",
            provenance=[]
        )
    
    def get_page_section(self, page_number: int) -> QueryResult:
        """Get the section containing a specific page."""
        if not self.navigator:
            return QueryResult(
                tool=QueryTool.PAGEINDEX_NAVIGATE,
                content="No page index loaded",
                provenance=[]
            )
        
        section = self.navigator.get_section_at_page(page_number)
        
        if section:
            content = f"Page {page_number} is in section: {section.title}\n"
            content += f"Page range: {section.page_start}-{section.page_end}\n"
            
            provenance = [ProvenanceSource(
                document_name=self.page_index.document_name,
                page_number=page_number,
                section_title=section.title
            )]
            
            return QueryResult(
                tool=QueryTool.PAGEINDEX_NAVIGATE,
                content=content,
                provenance=provenance
            )
        
        return QueryResult(
            tool=QueryTool.PAGEINDEX_NAVIGATE,
            content=f"No section found for page {page_number}",
            provenance=[]
        )
    
    def get_toc(self) -> QueryResult:
        """Get the table of contents."""
        if not self.navigator:
            return QueryResult(
                tool=QueryTool.PAGEINDEX_NAVIGATE,
                content="No page index loaded",
                provenance=[]
            )
        
        toc = self.navigator.render_toc()
        
        provenance = [ProvenanceSource(
            document_name=self.page_index.document_name,
            page_number=1
        )]
        
        return QueryResult(
            tool=QueryTool.PAGEINDEX_NAVIGATE,
            content=toc,
            provenance=provenance
        )


class SemanticSearchTool:
    """Tool for vector-based semantic search."""
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[Embedder] = None
    ):
        self.vector_store = vector_store or InMemoryVectorStore()
        self.embedder = embedder or DummyEmbedder()
    
    def set_vector_store(self, vector_store: VectorStore):
        """Set or update the vector store."""
        self.vector_store = vector_store
    
    def set_embedder(self, embedder: Embedder):
        """Set or update the embedder."""
        self.embedder = embedder
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        min_confidence: float = 0.0
    ) -> QueryResult:
        """Perform semantic search over the chunk store."""
        # Embed the query
        query_embedding = self.embedder.embed_query(query)
        
        # Search the vector store
        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filters=filters
        )
        
        if not results:
            return QueryResult(
                tool=QueryTool.SEMANTIC_SEARCH,
                content=f"No results found for query: '{query}'",
                provenance=[]
            )
        
        # Build response
        content = f"Found {len(results)} relevant chunks:\n\n"
        provenance = []
        
        for i, (similarity, chunk) in enumerate(results):
            chunk_text = chunk.metadata.get("text", "")[:200]
            doc_name = chunk.metadata.get("document_name", "unknown")
            page = chunk.metadata.get("page", 0)
            bbox = chunk.metadata.get("bbox")
            conf = chunk.metadata.get("confidence", 1.0)
            
            if conf < min_confidence:
                continue
            
            content += f"[{i+1}] Score: {similarity:.3f} | Page {page} | {doc_name}\n"
            content += f"    {chunk_text}...\n\n"
            
            provenance.append(ProvenanceSource(
                document_name=doc_name,
                page_number=page,
                bbox=bbox if isinstance(bbox, tuple) else None,
                chunk_id=chunk.chunk_id,
                confidence=conf
            ))
        
        return QueryResult(
            tool=QueryTool.SEMANTIC_SEARCH,
            content=content,
            provenance=provenance,
            metadata={"results_count": len(results), "query": query}
        )
    
    def get_context(
        self,
        chunk_id: str,
        context_chars: int = 200
    ) -> QueryResult:
        """Get expanded context for a specific chunk."""
        # Search for the specific chunk
        # This is a simplified version - in production would have direct access
        return QueryResult(
            tool=QueryTool.SEMANTIC_SEARCH,
            content=f"Context for chunk {chunk_id}",
            provenance=[]
        )


class StructuredQueryTool:
    """Tool for SQL-like queries over fact tables."""
    
    def __init__(self, fact_table: Optional[FactTable] = None):
        self.fact_table = fact_table or FactTable()
    
    def set_fact_table(self, fact_table: FactTable):
        """Set or update the fact table."""
        self.fact_table = fact_table
    
    def query(
        self,
        query_type: str,
        filters: Dict[str, Any]
    ) -> QueryResult:
        """
        Query the fact table.
        
        query_type: "financial", "temporal", "metric", or "all"
        filters: dict with keys like document_name, key, min_confidence
        """
        category = query_type if query_type != "all" else None
        
        facts = self.fact_table.query(
            document_name=filters.get("document_name"),
            category=category,
            key=filters.get("key"),
            min_confidence=filters.get("min_confidence", 0.0)
        )
        
        if not facts:
            return QueryResult(
                tool=QueryTool.STRUCTURED_QUERY,
                content=f"No facts found for query: {query_type}",
                provenance=[]
            )
        
        # Build response
        content = f"Found {len(facts)} facts:\n\n"
        provenance = []
        
        for fact in facts:
            content += f"- {fact.key}: {fact.value}\n"
            content += f"  Category: {fact.category} | Page: {fact.page_number} | Confidence: {fact.confidence:.2f}\n"
            if fact.context:
                content += f"  Context: {fact.context[:100]}...\n"
            content += "\n"
            
            provenance.append(ProvenanceSource(
                document_name=fact.document_name,
                page_number=fact.page_number,
                bbox=fact.bbox,
                confidence=fact.confidence
            ))
        
        return QueryResult(
            tool=QueryTool.STRUCTURED_QUERY,
            content=content,
            provenance=provenance,
            metadata={"facts_count": len(facts), "query_type": query_type}
        )
    
    def get_financial_summary(self, document_name: str) -> QueryResult:
        """Get financial summary for a document."""
        facts = self.fact_table.get_financial_facts(document_name)
        
        if not facts:
            return QueryResult(
                tool=QueryTool.STRUCTURED_QUERY,
                content=f"No financial facts found for {document_name}",
                provenance=[]
            )
        
        content = f"Financial Summary for {document_name}:\n\n"
        provenance = []
        
        # Group by key
        by_key = {}
        for fact in facts:
            if fact.key not in by_key:
                by_key[fact.key] = []
            by_key[fact.key].append(fact)
        
        for key, key_facts in by_key.items():
            # Get the most recent (highest page number) or highest confidence
            best = max(key_facts, key=lambda f: (f.page_number, f.confidence))
            
            content += f"{key}: {best.value}\n"
            
            provenance.append(ProvenanceSource(
                document_name=best.document_name,
                page_number=best.page_number,
                bbox=best.bbox,
                confidence=best.confidence
            ))
        
        return QueryResult(
            tool=QueryTool.STRUCTURED_QUERY,
            content=content,
            provenance=provenance,
            metadata={"document_name": document_name, "facts_count": len(facts)}
        )


class QueryAgent:
    """
    LangGraph-style query agent with three tools.
    
    Coordinates between:
    - PageIndex navigation (structural search)
    - Semantic search (vector retrieval)
    - Structured query (fact table)
    
    Provides full provenance tracking for all answers.
    """
    
    def __init__(
        self,
        page_index: Optional[PageIndex] = None,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[Embedder] = None,
        fact_table: Optional[FactTable] = None
    ):
        # Initialize tools
        self.pageindex_tool = PageIndexTool(page_index)
        self.semantic_tool = SemanticSearchTool(vector_store, embedder)
        self.structured_tool = StructuredQueryTool(fact_table)
        
        # Default settings
        self.default_top_k = 5
        self.min_confidence = 0.3
    
    def set_page_index(self, page_index: PageIndex):
        """Set the page index for navigation."""
        self.pageindex_tool.set_page_index(page_index)
    
    def set_vector_store(self, vector_store: VectorStore, embedder: Embedder):
        """Set vector store and embedder for semantic search."""
        self.semantic_tool.set_vector_store(vector_store)
        self.semantic_tool.set_embedder(embedder)
    
    def set_fact_table(self, fact_table: FactTable):
        """Set the fact table for structured queries."""
        self.structured_tool.set_fact_table(fact_table)
    
    def query(
        self,
        query: str,
        use_tools: Optional[List[QueryTool]] = None,
        **kwargs
    ) -> Tuple[str, List[ProvenanceSource]]:
        """
        Execute a query using appropriate tools.
        
        Args:
            query: The user query
            use_tools: Which tools to use (default: all)
            **kwargs: Additional arguments for tools
            
        Returns:
            Tuple of (answer_text, provenance_sources)
        """
        if use_tools is None:
            use_tools = [
                QueryTool.SEMANTIC_SEARCH,
                QueryTool.STRUCTURED_QUERY,
                QueryTool.PAGEINDEX_NAVIGATE
            ]
        
        results = []
        all_provenance = []
        
        for tool in use_tools:
            result = self._execute_tool(tool, query, **kwargs)
            results.append(result)
            all_provenance.extend(result.provenance)
        
        # Combine results into answer
        answer = self._combine_results(results, query)
        
        return answer, all_provenance
    
    def _execute_tool(
        self,
        tool: QueryTool,
        query: str,
        **kwargs
    ) -> QueryResult:
        """Execute a specific tool."""
        
        if tool == QueryTool.PAGEINDEX_NAVIGATE:
            # Determine action from query
            if "page" in query.lower() and any(c.isdigit() for c in query):
                # Extract page number
                numbers = re.findall(r'\d+', query)
                if numbers:
                    return self.pageindex_tool.get_page_section(int(numbers[0]))
            return self.pageindex_tool.find_section(query)
        
        elif tool == QueryTool.SEMANTIC_SEARCH:
            return self.semantic_tool.search(
                query=query,
                top_k=kwargs.get("top_k", self.default_top_k),
                min_confidence=kwargs.get("min_confidence", self.min_confidence)
            )
        
        elif tool == QueryTool.STRUCTURED_QUERY:
            # Determine query type
            query_type = "all"
            if "financial" in query.lower() or "revenue" in query.lower() or "profit" in query.lower():
                query_type = "financial"
            elif "date" in query.lower() or "quarter" in query.lower() or "year" in query.lower():
                query_type = "temporal"
            elif "rate" in query.lower() or "percent" in query.lower() or "growth" in query.lower():
                query_type = "metric"
            
            filters = kwargs.get("filters", {})
            return self.structured_tool.query(query_type, filters)
        
        return QueryResult(
            tool=tool,
            content="Unknown tool",
            provenance=[]
        )
    
    def _combine_results(self, results: List[QueryResult], query: str) -> str:
        """Combine results from multiple tools into a coherent answer."""
        # Filter out empty results
        valid_results = [r for r in results if r.provenance]
        
        if not valid_results:
            return f"I couldn't find any relevant information for: '{query}'. Please try rephrasing your query."
        
        # Start with the most relevant result
        primary = valid_results[0]
        
        answer = primary.content
        
        # Add additional context from other tools if substantially different
        if len(valid_results) > 1:
            additional_info = []
            for r in valid_results[1:]:
                if r.content not in answer:
                    additional_info.append(r.content)
            
            if additional_info:
                answer += "\n\nAdditional Information:\n"
                answer += "\n---\n".join(additional_info)
        
        return answer


class AuditMode:
    """
    Audit mode for verifying claims against stored data.
    
    Given a claim, the system verifies it with source citation
    or flags it as "not found / unverifiable".
    """
    
    def __init__(
        self,
        fact_table: Optional[FactTable] = None,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[Embedder] = None
    ):
        self.fact_table = fact_table or FactTable()
        self.semantic_tool = SemanticSearchTool(vector_store, embedder)
    
    def set_fact_table(self, fact_table: FactTable):
        """Set the fact table."""
        self.fact_table = fact_table
    
    def set_vector_store(self, vector_store: VectorStore, embedder: Embedder):
        """Set vector store and embedder."""
        self.semantic_tool.set_vector_store(vector_store)
        self.semantic_tool.set_embedder(embedder)
    
    def verify_claim(self, claim: str, document_name: Optional[str] = None) -> AuditResult:
        """
        Verify a claim against stored data.
        
        Args:
            claim: The claim to verify (e.g., "The report states revenue was $4.2B in Q3")
            document_name: Optional specific document to check
            
        Returns:
            AuditResult with verification status and sources
        """
        # Parse the claim to extract key-value pairs
        extracted = self._parse_claim(claim)
        
        if not extracted:
            # Fall back to semantic search
            return self._verify_semantic(claim, document_name)
        
        # Try to verify each extracted fact
        verified_facts = []
        unverified_parts = []
        
        for key, value in extracted:
            is_verified, fact = self.fact_table.verify_fact(
                claim_key=key,
                claim_value=value,
                document_name=document_name
            )
            
            if is_verified and fact:
                verified_facts.append((key, value, fact))
            else:
                unverified_parts.append((key, value))
        
        # Build the audit result
        if verified_facts and not unverified_parts:
            # Fully verified
            sources = [
                ProvenanceSource(
                    document_name=f[2].document_name,
                    page_number=f[2].page_number,
                    bbox=f[2].bbox,
                    confidence=f[2].confidence
                )
                for f in verified_facts
            ]
            
            return AuditResult(
                claim=claim,
                is_verified=True,
                verified_fact=verified_facts[0][2] if verified_facts else None,
                sources=sources,
                status="verified",
                explanation=f"Claim verified: Found matching facts for '{verified_facts[0][0]}' = '{verified_facts[0][1]}'"
            )
        
        elif verified_facts and unverified_parts:
            # Partially verified
            sources = [
                ProvenanceSource(
                    document_name=f[2].document_name,
                    page_number=f[2].page_number,
                    bbox=f[2].bbox,
                    confidence=f[2].confidence
                )
                for f in verified_facts
            ]
            
            unverified_str = ", ".join([f"{k}={v}" for k, v in unverified_parts])
            
            return AuditResult(
                claim=claim,
                is_verified=False,
                verified_fact=verified_facts[0][2] if verified_facts else None,
                sources=sources,
                status="partially_verified",
                explanation=f"Partially verified. Verified: {verified_facts[0][0]}, Not found: {unverified_str}"
            )
        
        else:
            # Not verified - try semantic search
            return self._verify_semantic(claim, document_name)
    
    def _parse_claim(self, claim: str) -> List[Tuple[str, str]]:
        """
        Parse a claim to extract key-value pairs.
        
        E.g., "revenue was $4.2B" -> [("revenue", "$4.2B")]
        """
        facts = []
        
        # Financial patterns
        financial_patterns = [
            (r'revenue[:\s]+[\$€£]?([\d,\.]+)([BMKbmk]?)', 'revenue'),
            (r'profit[:\s]+[\$€£]?([\d,\.]+)([BMKbmk]?)', 'profit'),
            (r'assets?[:\s]+[\$€£]?([\d,\.]+)([BMKbmk]?)', 'assets'),
            (r'loss[:\s]+[\$€£]?([\d,\.]+)([BMKbmk]?)', 'loss'),
        ]
        
        # Metric patterns
        metric_patterns = [
            (r'growth[:\s]+([\d,\.]+)%', 'growth_rate'),
            (r'margin[:\s]+([\d,\.]+)%', 'margin'),
        ]
        
        # Temporal patterns
        temporal_patterns = [
            (r'Q([1-4])[\s]*(\d{4})', 'quarter'),
            (r'(FY|fiscal year)[\s]*(\d{4})', 'fiscal_year'),
        ]
        
        all_patterns = financial_patterns + metric_patterns + temporal_patterns
        
        for pattern, key in all_patterns:
            match = re.search(pattern, claim, re.IGNORECASE)
            if match:
                # Get the full matched value
                value = match.group(0).split(':')[-1].strip()
                if not value:
                    value = match.group(0)
                facts.append((key, value))
        
        return facts
    
    def _verify_semantic(
        self,
        claim: str,
        document_name: Optional[str] = None
    ) -> AuditResult:
        """Fall back to semantic search for verification."""
        filters = {"document_name": document_name} if document_name else None
        
        result = self.semantic_tool.search(
            query=claim,
            top_k=3,
            filters=filters,
            min_confidence=0.5
        )
        
        if result.provenance:
            # Found some related content
            return AuditResult(
                claim=claim,
                is_verified=False,
                sources=result.provenance,
                status="unverified",
                explanation="Could not find exact match in fact table. Related content found via semantic search."
            )
        
        # No relevant content found
        return AuditResult(
            claim=claim,
            is_verified=False,
            sources=[],
            status="not_found",
            explanation="No matching facts or related content found in the document corpus."
        )
    
    def batch_verify(self, claims: List[str], document_name: Optional[str] = None) -> List[AuditResult]:
        """
        Verify multiple claims at once.
        
        Args:
            claims: List of claims to verify
            document_name: Optional specific document
            
        Returns:
            List of AuditResults
        """
        return [self.verify_claim(claim, document_name) for claim in claims]


# Convenience functions

def create_query_agent(
    page_index_path: Optional[str] = None,
    vector_store_path: Optional[str] = None,
    fact_table_path: Optional[str] = None
) -> Tuple[QueryAgent, Optional[PageIndex], Optional[VectorStore], FactTable]:
    """
    Create a fully configured query agent.
    
    Loads persisted data from disk if available.
    
    Returns:
        Tuple of (query_agent, page_index, vector_store, fact_table)
    """
    from src.storage.vector_store import VectorStoreConfig, create_vector_store
    
    # Load page index if available
    page_index = None
    if page_index_path and Path(page_index_path).exists():
        with open(page_index_path, 'r') as f:
            page_index = PageIndex.model_validate_json(f.read())
    
    # Create vector store
    vector_store_config = VectorStoreConfig(
        persist_directory=vector_store_path or ".refinery/vector_store"
    )
    vector_store, embedder = create_vector_store(vector_store_config)
    
    # Load fact table
    fact_table = FactTable(fact_table_path or ".refinery/fact_table.db")
    
    # Create query agent
    agent = QueryAgent(
        page_index=page_index,
        vector_store=vector_store,
        embedder=embedder,
        fact_table=fact_table
    )
    
    return agent, page_index, vector_store, fact_table


def create_audit_mode(
    fact_table_path: Optional[str] = None,
    vector_store_path: Optional[str] = None
) -> Tuple[AuditMode, FactTable]:
    """
    Create an audit mode instance.
    
    Returns:
        Tuple of (audit_mode, fact_table)
    """
    from src.storage.vector_store import VectorStoreConfig, create_vector_store
    
    fact_table = FactTable(fact_table_path or ".refinery/fact_table.db")
    
    vector_store_config = VectorStoreConfig(
        persist_directory=vector_store_path or ".refinery/vector_store"
    )
    vector_store, embedder = create_vector_store(vector_store_config)
    
    audit_mode = AuditMode(
        fact_table=fact_table,
        vector_store=vector_store,
        embedder=embedder
    )
    
    return audit_mode, fact_table
