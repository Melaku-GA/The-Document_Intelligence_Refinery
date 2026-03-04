"""
Vector store integration for RAG retrieval.

Supports ChromaDB and FAISS for local, free-tier vector storage.
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.models.ldu import LDU
from src.models.embedding import EmbeddedChunk
from src.embeddings.embedder import Embedder, DummyEmbedder


# Try to import optional dependencies
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


@dataclass
class VectorStoreConfig:
    """Configuration for vector store."""
    backend: str = "chroma"  # "chroma", "faiss", or "memory"
    persist_directory: str = ".refinery/vector_store"
    collection_name: str = "document_chunks"
    embedding_dim: int = 384
    index_type: str = "flat"  # For FAISS: flat, ivf, hnsw


class VectorStore(ABC):
    """Abstract base class for vector stores."""
    
    @abstractmethod
    def add(self, embedded_chunks: List[EmbeddedChunk]):
        """Add embedded chunks to the store."""
        pass
    
    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[float, EmbeddedChunk]]:
        """Search for similar chunks."""
        pass
    
    @abstractmethod
    def save(self):
        """Persist the vector store to disk."""
        pass
    
    @abstractmethod
    def load(self):
        """Load the vector store from disk."""
        pass


class InMemoryVectorStore(VectorStore):
    """
    Simple in-memory vector store (fallback).
    """
    
    def __init__(self, config: Optional[VectorStoreConfig] = None):
        self.config = config or VectorStoreConfig()
        self.chunks: List[EmbeddedChunk] = []
        self.embeddings: List[np.ndarray] = []
    
    def add(self, embedded_chunks: List[EmbeddedChunk]):
        """Add embedded chunks to the store."""
        for chunk in embedded_chunks:
            self.chunks.append(chunk)
            self.embeddings.append(np.array(chunk.vector))
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[float, EmbeddedChunk]]:
        """Search for similar chunks using cosine similarity."""
        if not self.embeddings:
            return []
        
        query_vec = np.array(query_embedding)
        
        # Compute cosine similarities
        similarities = []
        for i, emb in enumerate(self.embeddings):
            sim = self._cosine_similarity(query_vec, emb)
            similarities.append((sim, self.chunks[i]))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        # Apply filters if provided
        if filters:
            filtered = []
            for sim, chunk in similarities:
                if self._matches_filters(chunk, filters):
                    filtered.append((sim, chunk))
            similarities = filtered
        
        return similarities[:top_k]
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot / (norm1 * norm2))
    
    def _matches_filters(self, chunk: EmbeddedChunk, filters: Dict[str, Any]) -> bool:
        """Check if chunk matches filters."""
        for key, value in filters.items():
            chunk_value = chunk.metadata.get(key)
            if chunk_value != value:
                return False
        return True
    
    def save(self):
        """Persist to disk (simple JSON format)."""
        os.makedirs(self.config.persist_directory, exist_ok=True)
        
        data = {
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "vector": c.vector,
                    "metadata": c.metadata
                }
                for c in self.chunks
            ]
        }
        
        path = os.path.join(self.config.persist_directory, f"{self.config.collection_name}.json")
        with open(path, 'w') as f:
            json.dump(data, f)
    
    def load(self):
        """Load from disk."""
        path = os.path.join(self.config.persist_directory, f"{self.config.collection_name}.json")
        
        if not os.path.exists(path):
            return
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        self.chunks = [
            EmbeddedChunk(
                chunk_id=c["chunk_id"],
                vector=c["vector"],
                metadata=c["metadata"]
            )
            for c in data["chunks"]
        ]
        self.embeddings = [np.array(c.vector) for c in self.chunks]


class ChromaDBVectorStore(VectorStore):
    """
    ChromaDB vector store implementation.
    """
    
    def __init__(self, config: Optional[VectorStoreConfig] = None):
        if not CHROMADB_AVAILABLE:
            raise ImportError("chromadb not installed. Install with: pip install chromadb")
        
        self.config = config or VectorStoreConfig()
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.config.persist_directory
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.config.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def add(self, embedded_chunks: List[EmbeddedChunk]):
        """Add embedded chunks to ChromaDB."""
        ids = [c.chunk_id for c in embedded_chunks]
        embeddings = [c.vector for c in embedded_chunks]
        documents = [c.metadata.get("text", "") for c in embedded_chunks]
        metadatas = [c.metadata for c in embedded_chunks]
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[float, EmbeddedChunk]]:
        """Search ChromaDB for similar chunks."""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filters
        )
        
        # Convert to format expected by pipeline
        output = []
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i]
                # Convert distance to similarity (1 - distance for cosine)
                similarity = 1 - distance
                
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                text = results["documents"][0][i] if results["documents"] else ""
                
                chunk = EmbeddedChunk(
                    chunk_id=chunk_id,
                    vector=results["embeddings"][0][i] if results["embeddings"] else [],
                    metadata=metadata
                )
                
                output.append((similarity, chunk))
        
        return output
    
    def save(self):
        """ChromaDB auto-persists."""
        pass
    
    def load(self):
        """ChromaDB auto-loads."""
        pass


class FAISSVectorStore(VectorStore):
    """
    FAISS vector store implementation.
    """
    
    def __init__(self, config: Optional[VectorStoreConfig] = None):
        if not FAISS_AVAILABLE:
            raise ImportError("faiss not installed. Install with: pip install faiss-cpu")
        
        self.config = config or VectorStoreConfig()
        self.chunks: List[EmbeddedChunk] = []
        self.index: Optional[faiss.Index] = None
        
        # Create index
        self._create_index()
    
    def _create_index(self):
        """Create FAISS index based on config."""
        dim = self.config.embedding_dim
        
        if self.config.index_type == "flat":
            # Flat index - exact search
            self.index = faiss.IndexFlatIP(dim)  # Inner product for cosine similarity
        elif self.config.index_type == "hnsw":
            # HNSW index - approximate search
            self.index = faiss.IndexHNSWFlat(dim, 32)
        else:
            # Default to flat
            self.index = faiss.IndexFlatIP(dim)
    
    def add(self, embedded_chunks: List[EmbeddedChunk]):
        """Add embedded chunks to FAISS index."""
        # Normalize vectors for cosine similarity
        vectors = np.array([c.vector for c in embedded_chunks], dtype=np.float32)
        
        # L2 normalize for cosine similarity with inner product
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        vectors = vectors / norms
        
        # Add to index
        self.index.add(vectors)
        
        # Store chunks
        self.chunks.extend(embedded_chunks)
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[float, EmbeddedChunk]]:
        """Search FAISS for similar chunks."""
        if self.index.ntotal == 0:
            return []
        
        # Normalize query
        query_vec = np.array([query_embedding], dtype=np.float32)
        norms = np.linalg.norm(query_vec, axis=1, keepdims=True)
        norms[norms == 0] = 1
        query_vec = query_vec / norms
        
        # Search
        distances, indices = self.index.search(query_vec, top_k)
        
        # Convert to output format
        output = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(self.chunks):
                similarity = float(distances[0][i])
                chunk = self.chunks[idx]
                
                # Apply filters
                if filters and not self._matches_filters(chunk, filters):
                    continue
                
                output.append((similarity, chunk))
        
        return output
    
    def _matches_filters(self, chunk: EmbeddedChunk, filters: Dict[str, Any]) -> bool:
        """Check if chunk matches filters."""
        for key, value in filters.items():
            chunk_value = chunk.metadata.get(key)
            if chunk_value != value:
                return False
        return True
    
    def save(self):
        """Save FAISS index to disk."""
        os.makedirs(self.config.persist_directory, exist_ok=True)
        
        # Save index
        index_path = os.path.join(self.config.persist_directory, f"{self.config.collection_name}.index")
        faiss.write_index(self.index, index_path)
        
        # Save chunk metadata
        data = {
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "vector": c.vector,
                    "metadata": c.metadata
                }
                for c in self.chunks
            ]
        }
        
        meta_path = os.path.join(self.config.persist_directory, f"{self.config.collection_name}_meta.json")
        with open(meta_path, 'w') as f:
            json.dump(data, f)
    
    def load(self):
        """Load FAISS index from disk."""
        index_path = os.path.join(self.config.persist_directory, f"{self.config.collection_name}.index")
        meta_path = os.path.join(self.config.persist_directory, f"{self.config.collection_name}_meta.json")
        
        if not os.path.exists(index_path):
            return
        
        # Load index
        self.index = faiss.read_index(index_path)
        
        # Load metadata
        with open(meta_path, 'r') as f:
            data = json.load(f)
        
        self.chunks = [
            EmbeddedChunk(
                chunk_id=c["chunk_id"],
                vector=c["vector"],
                metadata=c["metadata"]
            )
            for c in data["chunks"]
        ]


def create_vector_store(
    config: Optional[VectorStoreConfig] = None,
    embedder: Optional[Embedder] = None
) -> Tuple[VectorStore, Embedder]:
    """
    Factory function to create vector store.
    
    Args:
        config: Vector store configuration
        embedder: Embedder to use (creates DummyEmbedder if not provided)
        
    Returns:
        Tuple of (vector_store, embedder)
    """
    config = config or VectorStoreConfig()
    embedder = embedder or DummyEmbedder()
    
    # Try to create the requested backend
    if config.backend == "chroma" and CHROMADB_AVAILABLE:
        store = ChromaDBVectorStore(config)
    elif config.backend == "faiss" and FAISS_AVAILABLE:
        store = FAISSVectorStore(config)
    else:
        # Fall back to in-memory
        store = InMemoryVectorStore(config)
    
    return store, embedder


class ChunkIngestor:
    """
    Handles ingestion of LDUs into vector store.
    """
    
    def __init__(self, vector_store: VectorStore, embedder: Embedder):
        self.vector_store = vector_store
        self.embedder = embedder
    
    def ingest_ldus(self, ldu_list: List[LDU], document_name: str) -> int:
        """
        Ingest LDUs into vector store.
        
        Args:
            ldu_list: List of LDUs to ingest
            document_name: Name of the source document
            
        Returns:
            Number of chunks ingested
        """
        # Convert LDUs to DocumentChunks for embedding
        from src.models.chunk import DocumentChunk
        
        chunks = []
        for ldu in ldu_list:
            # Get first page reference
            page = ldu.page_refs[0].page_number if ldu.page_refs else 0
            
            doc_chunk = DocumentChunk(
                chunk_id=ldu.content_hash,
                text=ldu.content,
                page=page,
                bbox=None,  # Could extract from page_refs
                confidence=1.0  # Default since LDU doesn't have confidence
            )
            chunks.append(doc_chunk)
        
        # Embed chunks
        embedded = self.embedder.embed(chunks)
        
        # Add metadata
        for i, emb in enumerate(embedded):
            emb.metadata["document_name"] = document_name
            emb.metadata["chunk_type"] = ldu_list[i].chunk_type.value
            emb.metadata["parent_section"] = ldu_list[i].parent_section
            emb.metadata["page_refs"] = [p.page_number for p in ldu_list[i].page_refs]
        
        # Add to vector store
        self.vector_store.add(embedded)
        
        return len(embedded)
    
    def save(self):
        """Persist vector store."""
        self.vector_store.save()
