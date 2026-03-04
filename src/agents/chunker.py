"""
Chunking Agent - Orchestrates the semantic chunking process.

Transforms extracted documents into RAG-optimized LDUs.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models.extracted_document import ExtractedDocument
from src.models.ldu import LDU
from src.chunking.engine import ChunkingEngine, ChunkingConfig, ChunkingResult
from src.indexing.builder import PageIndexBuilder, IndexingConfig
from src.indexing.navigator import PageIndexNavigator
from src.storage.vector_store import (
    VectorStore,
    VectorStoreConfig,
    ChunkIngestor,
    create_vector_store
)
from src.embeddings.embedder import Embedder, DummyEmbedder


class ChunkingAgent:
    """
    Agent that orchestrates the chunking process.
    
    Takes extracted documents and produces:
    - LDUs (Logical Document Units) with content hashes
    - PageIndex for navigation
    - Ingested vectors for semantic search
    """
    
    def __init__(
        self,
        chunking_config: Optional[ChunkingConfig] = None,
        indexing_config: Optional[IndexingConfig] = None,
        vector_store_config: Optional[VectorStoreConfig] = None,
        embedder: Optional[Embedder] = None
    ):
        self.chunking_engine = ChunkingEngine(chunking_config)
        self.indexing_builder = PageIndexBuilder(indexing_config)
        
        # Set up vector store
        self.vector_store, self.embedder = create_vector_store(
            vector_store_config, embedder
        )
        self.chunk_ingestor = ChunkIngestor(self.vector_store, self.embedder)
        
        # Output directories
        self.chunks_dir = chunking_config.output_dir if chunking_config else ".refinery/chunks"
        self.index_dir = indexing_config.output_dir if indexing_config else ".refinery/pageindex"
    
    def process(
        self,
        extracted_doc: ExtractedDocument,
        ingest_to_vector: bool = True
    ) -> Dict[str, Any]:
        """
        Process an extracted document through chunking and indexing.
        
        Args:
            extracted_doc: ExtractedDocument from extraction stage
            ingest_to_vector: Whether to ingest chunks into vector store
            
        Returns:
            Dictionary with processing results:
            - ldus: List of LDUs
            - chunk_count: Number of chunks created
            - token_count: Total token count
            - validation_summary: Validation results
            - pageindex_path: Path to saved PageIndex
        """
        # Step 1: Chunk the document
        chunking_result = self.chunking_engine.process(extracted_doc)
        
        print(f"📑 Created {chunking_result.chunk_count} chunks from {extracted_doc.document_name}")
        print(f"   Total tokens: {chunking_result.token_count}")
        print(f"   Validation: {chunking_result.validation_summary.get('valid_chunks', 0)}/{chunking_result.validation_summary.get('total_chunks', 0)} valid")
        
        # Step 2: Build PageIndex
        page_index = self.indexing_builder.build(
            ldu_list=chunking_result.ldus,
            document_name=extracted_doc.document_name,
            total_pages=chunking_result.total_pages
        )
        
        # Save PageIndex
        index_path = self.indexing_builder.save(page_index, extracted_doc.document_name)
        print(f"📊 PageIndex saved to: {index_path}")
        
        # Step 3: Ingest to vector store (optional)
        if ingest_to_vector:
            ingested = self.chunk_ingestor.ingest_ldus(
                chunking_result.ldus,
                extracted_doc.document_name
            )
            print(f"🔢 Ingested {ingested} chunks to vector store")
            
            # Persist vector store
            self.chunk_ingestor.save()
        
        # Return results
        return {
            "ldus": chunking_result.ldus,
            "chunk_count": chunking_result.chunk_count,
            "token_count": chunking_result.token_count,
            "validation_summary": chunking_result.validation_summary,
            "pageindex_path": index_path,
            "total_pages": chunking_result.total_pages
        }
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the vector store for relevant chunks.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of search results with chunk data
        """
        # Embed query
        query_embedding = self.embedder.embed_query(query)
        
        # Search
        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filters=filters
        )
        
        # Format results
        output = []
        for similarity, chunk in results:
            output.append({
                "chunk_id": chunk.chunk_id,
                "similarity": similarity,
                "metadata": chunk.metadata,
                "text": chunk.metadata.get("text", "")
            })
        
        return output
    
    def get_pageindex(self, document_name: str) -> Optional[PageIndexNavigator]:
        """
        Get PageIndex navigator for a document.
        
        Args:
            document_name: Name of the document
            
        Returns:
            PageIndexNavigator if found, None otherwise
        """
        page_index = self.indexing_builder.load(document_name)
        
        if page_index:
            return PageIndexNavigator(page_index)
        
        return None


def load_extracted_document(path: str) -> Optional[ExtractedDocument]:
    """
    Load an extracted document from JSON file.
    
    Args:
        path: Path to the JSON file
        
    Returns:
        ExtractedDocument if found, None otherwise
    """
    if not os.path.exists(path):
        return None
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return ExtractedDocument(**data)


def process_document_from_file(
    extraction_path: str,
    chunking_config: Optional[ChunkingConfig] = None
) -> Dict[str, Any]:
    """
    Process a document from an extraction file.
    
    Args:
        path: Path to the extraction JSON file
        chunking_config: Optional chunking configuration
        
    Returns:
        Processing results dictionary
    """
    # Load extracted document
    extracted_doc = load_extracted_document(extraction_path)
    
    if not extracted_doc:
        raise FileNotFoundError(f"Extraction file not found: {extraction_path}")
    
    # Process
    agent = ChunkingAgent(chunking_config=chunking_config)
    return agent.process(extracted_doc)
