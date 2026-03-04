#!/usr/bin/env python3
"""
Batch processing script to generate document profiles and extraction ledger entries.
"""

import json
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.triage import TriageAgent, save_profile
from src.agents.extractor import ExtractionRouter
from src.chunking.layout_chunker import LayoutAwareChunker
from src.agents.indexer import IndexerAgent
from src.embeddings.embedder import DummyEmbedder
from src.storage.vector_store import InMemoryVectorStore
from src.models.ldu import LDU, LDUType
from src.models.enums import ChunkType


# Define document corpus with at least 12 documents
# Class A: Annual Financial Reports (3+)
# Class B: Scanned Government/Legal (3+)
# Class C: Technical Assessment (3+)
# Class D: Structured Data Reports (3+)

DOCUMENTS = [
    # Class A: Annual Financial Reports
    {"path": "Data/raw/Annual_Report_JUNE-2017.pdf", "class": "A", "name": "Annual Report 2017"},
    {"path": "Data/raw/Annual_Report_JUNE-2018.pdf", "class": "A", "name": "Annual Report 2018"},
    {"path": "Data/raw/Annual_Report_JUNE-2019.pdf", "class": "A", "name": "Annual Report 2019"},
    {"path": "Data/raw/2018_Audited_Financial_Statement_Report.pdf", "class": "A", "name": "Audited Financial Statement 2018"},
    {"path": "Data/raw/2020_Audited_Financial_Statement_Report.pdf", "class": "A", "name": "Audited Financial Statement 2020"},
    
    # Class B: Scanned Government/Legal
    {"path": "Data/raw/2013-E.C-Assigned-regular-budget-and-expense.pdf", "class": "B", "name": "E.C Budget 2013"},
    {"path": "Data/raw/2013-E.C-Audit-finding-information.pdf", "class": "B", "name": "Audit Findings 2013"},
    {"path": "Data/raw/2013-E.C-Procurement-information.pdf", "class": "B", "name": "Procurement Info 2013"},
    {"path": "Data/raw/tax_expenditure_ethiopia_2021_22.pdf", "class": "B", "name": "Tax Expenditure 2021-22"},
    
    # Class C: Technical Assessment
    {"path": "Data/raw/Security_Vulnerability_Disclosure_Standard_Procedure_1.pdf", "class": "C", "name": "Security Vulnerability Procedure 1"},
    {"path": "Data/raw/Security_Vulnerability_Disclosure_Standard_Procedure_2.pdf", "class": "C", "name": "Security Vulnerability Procedure 2"},
    {"path": "Data/raw/fta_performance_survey_final_report_2022.pdf", "class": "C", "name": "FTA Performance Survey 2022"},
    {"path": "Data/raw/20191010_Pharmaceutical-Manufacturing-Opportunites-in-Ethiopia_VF.pdf", "class": "C", "name": "Pharmaceutical Manufacturing Opportunities"},
    
    # Class D: Structured Data Reports
    {"path": "Data/raw/Consumer Price Index June 2025.pdf", "class": "D", "name": "CPI June 2025"},
    {"path": "Data/raw/Consumer Price Index July 2025.pdf", "class": "D", "name": "CPI July 2025"},
    {"path": "Data/raw/Consumer Price Index August 2025.pdf", "class": "D", "name": "CPI August 2025"},
    {"path": "Data/raw/Consumer Price Index September 2025.pdf", "class": "D", "name": "CPI September 2025"},
]


def chunk_to_ldu(chunk) -> LDU:
    """Convert DocumentChunk to LDU for indexing."""
    return LDU(
        ldu_type=LDUType.PARAGRAPH,
        content=chunk.text,
        chunk_type=ChunkType.PARAGRAPH,
        page=chunk.page,
        page_refs=[],
        parent_section=None,
        bounding_box=None,
        cross_references=[],
        token_count=len(chunk.text.split()),
        content_hash=f"hash_{chunk.chunk_id}"
    )


def process_documents():
    """Process all documents and generate profiles."""
    print("=" * 60)
    print("Document Intelligence Refinery - Batch Processing")
    print("=" * 60)
    
    triage = TriageAgent()
    router = ExtractionRouter(confidence_threshold=0.65)
    chunker = LayoutAwareChunker(max_chars=800)
    indexer = IndexerAgent()
    embedder = DummyEmbedder()
    
    profiles = []
    extraction_results = []
    
    # Create extraction ledger entries
    ledger_entries = []
    
    for doc in DOCUMENTS:
        doc_path = doc["path"]
        doc_name = doc["name"]
        doc_class = doc["class"]
        
        print(f"\nProcessing: {doc_name}")
        print(f"  Path: {doc_path}")
        print(f"  Class: {doc_class}")
        
        try:
            # Step 1: Triage and classification
            profile = triage.classify(doc_path)
            
            # Update the expected class
            profile.actual_class = doc_class
            
            # Save profile
            profile_path = save_profile(profile)
            print(f"  Profile saved: {profile_path}")
            
            profiles.append({
                "name": doc_name,
                "class": doc_class,
                "profile": profile
            })
            
            # Step 2: Extract content
            result = router.extract(doc_path, profile)
            print(f"  Extraction confidence: {result.confidence:.2f}")
            print(f"  Text blocks: {len(result.document.text_blocks)}")
            print(f"  Strategy used: {result.strategy_used}")
            
            # Step 3: Chunk the document
            chunks = chunker.chunk(result.document)
            print(f"  Chunks produced: {len(chunks)}")
            
            # Step 4: Build PageIndex
            total_pages = profile.page_count
            # Convert chunks to LDUs for indexing
            ldu_list = [chunk_to_ldu(c) for c in chunks]
            page_index = indexer.build_index(ldu_list, doc_name, total_pages)
            print(f"  PageIndex built: {len(page_index.sections)} sections")
            
            # Step 5: Embed chunks for vector store
            embedded_chunks = embedder.embed(chunks)
            vector_store = InMemoryVectorStore()
            vector_store.add(embedded_chunks)
            print(f"  Vectors stored: {len(vector_store)}")
            
            extraction_results.append({
                "name": doc_name,
                "class": doc_class,
                "result": result
            })
            
            # Create ledger entry
            ledger_entry = {
                "timestamp": datetime.now().isoformat(),
                "document_id": profile.document_id,
                "document_name": doc_name,
                "document_class": doc_class,
                "page_count": profile.page_count,
                "strategy_used": result.strategy_used.value if hasattr(result.strategy_used, 'value') else str(result.strategy_used),
                "confidence": result.confidence,
                "text_blocks": len(result.document.text_blocks),
                "extraction_time": result.extraction_time,
                "is_native_digital": profile.is_native_digital,
                "has_tables": profile.has_tables,
                "has_images": profile.has_images,
            }
            ledger_entries.append(ledger_entry)
            
        except Exception as e:
            print(f"  ERROR: {str(e)}")
            # Create error ledger entry
            ledger_entry = {
                "timestamp": datetime.now().isoformat(),
                "document_name": doc_name,
                "document_class": doc_class,
                "status": "error",
                "error": str(e)
            }
            ledger_entries.append(ledger_entry)
    
    # Write extraction ledger
    ledger_path = ".refinery/extraction_ledger.jsonl"
    with open(ledger_path, 'w', encoding='utf-8') as f:
        for entry in ledger_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"\nExtraction ledger saved: {ledger_path}")
    print(f"Total documents processed: {len([e for e in ledger_entries if 'status' not in e])}")
    print(f"Total errors: {len([e for e in ledger_entries if 'status' in e and e['status'] == 'error'])}")
    
    return profiles, extraction_results, ledger_entries


if __name__ == "__main__":
    profiles, results, ledger = process_documents()
    print("\n" + "=" * 60)
    print("Processing Complete!")
    print("=" * 60)
