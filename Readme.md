# Document Intelligence Refinery

A comprehensive document processing pipeline for extracting, chunking, and querying diverse document types from Ethiopian government and corporate sectors.

## Overview

The Document Intelligence Refinery is a 5-stage pipeline that:

1. **Triage & Profile** - Analyzes documents and classifies them into categories
2. **Route to Strategy** - Selects appropriate extraction strategy based on document characteristics
3. **Extract Content** - Uses multi-strategy extraction (Fast Text, Layout-Aware, Vision)
4. **Semantic Chunking** - Segments content into meaningful chunks with PageIndex
5. **Query & Answer** - Enables natural language querying with full provenance

## Features

- **Multi-Strategy Extraction**: Support for Strategy A (Fast Text), Strategy B (Layout Model), Strategy C (Vision Model)
- **Document Classification**: Four document classes (Financial, Government/Legal, Technical, Structured Data)
- **Semantic Chunking**: Intelligent content segmentation with layout-aware boundaries
- **Full Provenance**: Complete tracking from source to answer
- **Confidence Scoring**: Multi-factor confidence calculations for quality assessment

## Quick Start

### Installation

```bash
# Install dependencies
pip install -e .

# Or install from pyproject.toml
pip install pdfplumber pydantic
```

### Running the Pipeline

#### Basic Usage

```python
from src.agents.triage import TriageAgent
from src.agents.extractor import ExtractionRouter

# Initialize
triage = TriageAgent()
router = ExtractionRouter(confidence_threshold=0.65)

# Process a document
pdf_path = "Data/raw/Annual_Report_JUNE-2017.pdf"
profile = triage.classify(pdf_path)
result = router.extract(pdf_path, profile)

print(f"Extraction confidence: {result.confidence}")
print(f"Text blocks: {len(result.document.text_blocks)}")
```

#### Query Mode

```python
from src.embeddings.embedder import DummyEmbedder
from src.embeddings.vector_store import InMemoryVectorStore
from src.answering.answer_generator import GroundedAnswerGenerator

# After extraction and chunking
embedder = DummyEmbedder()
embedded_chunks = embedder.embed(chunks)

store = InMemoryVectorStore()
store.add(embedded_chunks)

# Query
retrieved = store.retrieve(
    query="What was the total revenue?",
    embedder=embedder,
    top_k=3,
)

generator = GroundedAnswerGenerator(min_confidence=0.5)
answer = generator.generate(query, retrieved)

print(answer.text)
```

### Running Tests

```bash
# Run all tests
pytest test/ -v

# Run specific test file
pytest test/test_triage.py -v

# Run with coverage
pytest test/ --cov=src
```

## Project Structure

```
document-intelligence-refinery/
├── src/
│   ├── agents/              # Agent implementations
│   │   ├── triage.py        # Document triage and classification
│   │   ├── extractor.py    # Extraction router
│   │   ├── chunker.py      # Content chunking
│   │   └── indexer.py      # Index building
│   ├── strategies/         # Extraction strategies
│   │   ├── fast_text.py    # Strategy A: Fast text
│   │   ├── mineru_layout.py # Strategy B: Layout model
│   │   └── vision.py       # Strategy C: Vision model
│   ├── chunking/           # Chunking engine
│   │   ├── rules.py        # Chunking rules
│   │   └── engine.py       # Chunking engine
│   ├── models/             # Data models
│   │   ├── document_profile.py
│   │   ├── page_index.py
│   │   ├── ldu.py          # Layout Detection Unit
│   │   └── enums.py        # Enumerations
│   ├── storage/            # Storage layer
│   │   ├── ledger.py       # Extraction ledger
│   │   └── vector_store.py # Vector storage
│   └── utils/              # Utilities
│       ├── pdf_metrics.py   # PDF analysis
│       └── hashing.py       # Document hashing
├── test/                   # Unit tests
│   ├── test_triage.py
│   ├── test_confidence.py
│   ├── test_chunking_rules.py
│   └── test_pageindex.py
├── docs/                   # Documentation
│   ├── DOMAIN_NOTES.md
│   ├── architecture.md
│   ├── cost_analysis.md
│   └── qa_examples.md
├── Data/
│   ├── raw/                # Source documents
│   └── processed/          # Processed output
├── .refinery/              # Pipeline data
│   ├── profiles/           # Document profiles
│   └── extraction_ledger.jsonl
└── rubric/                 # Configuration
    └── extract_rules.yaml
```

## Document Classes

| Class | Description | Example Documents |
|-------|-------------|------------------|
| **A** | Annual Financial Reports | Annual reports, Audited statements |
| **B** | Government/Legal | Budget documents, Audit findings |
| **C** | Technical Assessment | Security procedures, Survey reports |
| **D** | Structured Data Reports | CPI indices, Statistical reports |

## Extraction Strategies

| Strategy | Cost/Page | Best For | Speed |
|----------|-----------|----------|-------|
| **A** (Fast Text) | $0.001 | Simple native PDFs | ~1-2s |
| **B** (Layout) | $0.005 | Complex layouts, tables | ~3-5s |
| **C** (Vision) | $0.020 | Scanned documents | ~10-15s |

## Configuration

### Environment Variables

```bash
# Optional: Set API keys for cloud services
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

### Confidence Thresholds

```python
# Default thresholds
HIGH_CONFIDENCE = 0.95    # Auto-approve
MEDIUM_CONFIDENCE = 0.80  # Review recommended  
LOW_CONFIDENCE = 0.65     # Manual review required
```

## Documentation

- [Architecture Diagram](docs/architecture.md) - System architecture
- [Domain Notes](docs/DOMAIN_NOTES.md) - Decision trees and failure modes
- [Cost Analysis](docs/cost_analysis.md) - Cost estimates by strategy
- [Q&A Examples](docs/qa_examples.md) - Example queries with provenance

## Development

### Running the Batch Processor

```bash
python scripts/generate_profiles.py
```

This processes documents and generates:
- Document profiles in `.refinery/profiles/`
- Extraction ledger at `.refinery/extraction_ledger.jsonl`

### Adding New Documents

1. Place PDF in `Data/raw/`
2. Run the triage agent to generate profile
3. Extract content using appropriate strategy
4. Query using natural language

## License

MIT License
