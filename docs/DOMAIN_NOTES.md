# Document Intelligence Refinery - Domain Notes

## Extraction Strategy Decision Tree

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EXTRACTION STRATEGY SELECTION                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  INPUT DOCUMENT ASSESSMENT    │
                    └───────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
           ┌──────────────────┐           ┌──────────────────┐
           │  Is it NATIVE   │           │  Is it SCANNED  │
           │  DIGITAL PDF?   │           │  (image-based)? │
           └──────────────────┘           └──────────────────┘
                    │                               │
         ┌──────────┴──────────┐           ┌─────────┴─────────┐
         ▼                     ▼           ▼                   ▼
   ┌─────────┐           ┌─────────┐  ┌─────────┐        ┌─────────┐
   │  YES    │           │   NO    │  │  YES    │        │   NO    │
   └─────────┘           └─────────┘  └─────────┘        └─────────┘
         │                     │           │                   │
         ▼                     ▼           ▼                   ▼
   ┌───────────┐         ┌───────────┐ ┌───────────┐      ┌───────────┐
   │ Has clear │         │ Is it     │ │ Contains │      │ Is it     │
   │ text      │         │ complex   │ │ tables/  │      │ complex   │
   │ layer?    │         │ layout?   │ │ charts?  │      │ layout?   │
   └───────────┘         └───────────┘ └───────────┘      └───────────┘
         │                     │           │                   │
    ┌────┴────┐          ┌────┴────┐      ┌────┴────┐     ┌────┴────┐
    ▼         ▼          ▼         ▼      ▼         ▼     ▼         ▼
 STRATEGY   STRATEGY  STRATEGY   STRATEGY STRATEGY  STRATEGY STRATEGY  STRATEGY
    A          B          B         C        C        B         C
```

### Strategy Selection Logic

| Condition | Recommended Strategy | Rationale |
|-----------|---------------------|-----------|
| Native digital + clear text + simple layout | **Strategy A** (Fast Text) | Direct text extraction is fastest and most accurate |
| Native digital + complex layout | **Strategy B** (Layout Model) | Layout preservation critical for comprehension |
| Scanned + good quality + simple | **Strategy B** (Layout Model) | OCR + layout analysis handles these well |
| Scanned + complex/handwritten | **Strategy C** (Vision Model) | Visual context needed for interpretation |
| Mixed content (text + images) | **Strategy C** (Vision Model) | Full visual understanding required |
| Financial tables + native | **Strategy B** (Layout Model) | Table structure preservation essential |
| Government forms + scanned | **Strategy C** (Vision Model) | Form field detection requires visual cues |

---

## Failure Modes Observed Across Document Types

### Class A: Annual Financial Reports

| Failure Mode | Description | Mitigation |
|--------------|-------------|------------|
| **Table Parsing Failure** | Financial tables extracted as unstructured text | Strategy B with table detection |
| **Number Precision Loss** | Large financial numbers truncated or misread | Use layout-aware extraction with coordinate preservation |
| **Multi-column Layout Confusion** | Column headers misaligned with data | Maintain spatial relationship in extraction |
| **Currency Symbol Loss** | Birr (ETB) symbols not preserved | Configure character encoding for Ethiopian currency |

### Class B: Scanned Government/Legal Documents

| Failure Mode | Description | Mitigation |
|--------------|-------------|------------|
| **OCR Accuracy Degradation** | Low-quality scans produce errors | Pre-process with image enhancement |
| **Handwritten Annotation Ignored** | Notes/marks in margins missed | Strategy C with visual element detection |
| **Stamp/Seal Overlap** | Official stamps obscure text | Multi-pass extraction with noise reduction |
| **Language Script Issues** | Amharic text recognition failures | Use language-specific OCR models |
| **Faded Text** | Old documents have degraded ink | Contrast enhancement preprocessing |

### Class C: Technical Assessment Documents

| Failure Mode | Description | Mitigation |
|--------------|-------------|------------|
| **Diagram Loss** | Technical drawings not extracted | Strategy C with image-to-text for diagrams |
| **Code Snippet Corruption** | Programming code fragmented | Preserve whitespace and special characters |
| **Equation Breakdown** | Mathematical formulas broken | Use specialized formula recognition |
| **Mixed Language Confusion** | English/Amharic text boundaries unclear | Language detection before processing |

### Class D: Structured Data Reports (CPI, Budgets)

| Failure Mode | Description | Mitigation |
|--------------|-------------|------------|
| **Row/Column Misalignment** | Data shifted from headers | Use table structure recovery |
| **Metadata Extraction Failure** | Report metadata not captured | Enhanced header/footer parsing |
| **Date Format Inconsistency** | Multiple date formats not normalized | Post-processing date normalization |
| **Missing Units** | Measurement units lost in extraction | Preserve unit context from source |

---

## Pipeline Diagram

```mermaid
flowchart TB
    subgraph INPUT["INPUT STAGE"]
        DOC[("Document Input")]
        PDF[("PDF Parsing")]
    end

    subgraph TRIAGE["STAGE 1: TRIAGE & PROFILING"]
        ANALYZE[("Analyze Document")]
        CLASSIFY{("Classify Document")}
        PROFILE[("Generate Profile")]
    end

    subgraph STRATEGY["STAGE 2: STRATEGY ROUTING"]
        ROUTE{("Route to Strategy")}
        STRAT_A["Strategy A: Fast Text"]
        STRAT_B["Strategy B: Layout Model"]
        STRAT_C["Strategy C: Vision Model"]
    end

    subgraph EXTRACT["STAGE 3: EXTRACTION"]
        PARSE[("Parse Document")]
        VALIDATE[("Validate Output")]
        CONFD[("Calculate Confidence")]
    end

    subgraph CHUNK["STAGE 4: CHUNKING"]
        SEGMENT[("Segment Content")]
        RULES[("Apply Rules")]
        INDEX[("Build Index")]
    end

    subgraph OUTPUT["STAGE 5: OUTPUT & STORAGE"]
        STORE[("Store Results")]
        LEDGER[("Update Ledger")]
        READY[("Ready for Query")]
    end

    DOC --> PDF
    PDF --> TRIAGE
    ANALYZE --> CLASSIFY
    CLASSIFY --> PROFILE
    
    PROFILE --> ROUTE
    ROUTE -->|Simple Digital| STRAT_A
    ROUTE -->|Layout-Rich| STRAT_B
    ROUTE -->|Scanned/Complex| STRAT_C
    
    STRAT_A --> EXTRACT
    STRAT_B --> EXTRACT
    STRAT_C --> EXTRACT
    
    PARSE --> VALIDATE
    VALIDATE --> CONFD
    CONFD --> CHUNK
    
    SEGMENT --> RULES
    RULES --> INDEX
    INDEX --> OUTPUT
    
    STORE --> LEDGER
    LEDGER --> READY
```

---

## Strategy Comparison Matrix

| Aspect | Strategy A (Fast Text) | Strategy B (Layout) | Strategy C (Vision) |
|--------|----------------------|--------------------|--------------------|
| **Speed** | ~1-2 sec/page | ~3-5 sec/page | ~10-15 sec/page |
| **Cost** | $0.001/page | $0.005/page | $0.02/page |
| **Best For** | Simple reports | Complex layouts | Scanned documents |
| **Accuracy (Text)** | 99% | 97% | 95% |
| **Accuracy (Layout)** | 70% | 95% | 90% |
| **Table Support** | Basic | Full | Good |
| **Image Extraction** | None | Basic | Full |
| **OCR Required** | No | Optional | Yes |

---

## Document Class Characteristics

### Class A: Annual Financial Reports
- **Typical Size**: 50-300 pages
- **Characteristics**: Native digital, complex tables, financial terminology
- **Recommended Strategy**: Strategy B (Layout Model)
- **Key Features**: Multi-sheet tables, charts, audit disclaimers

### Class B: Scanned Government/Legal
- **Typical Size**: 10-50 pages
- **Characteristics**: Often scanned, formal structure, Amharic/English
- **Recommended Strategy**: Strategy C (Vision Model)
- **Key Features**: Official stamps, legal language, form fields

### Class C: Technical Assessment
- **Typical Size**: 20-100 pages
- **Characteristics**: Mixed content, technical diagrams, code
- **Recommended Strategy**: Strategy C (Vision Model)
- **Key Features**: Diagrams, tables, technical terminology

### Class D: Structured Data Reports
- **Typical Size**: 5-20 pages
- **Characteristics**: Highly structured, data-heavy, consistent format
- **Recommended Strategy**: Strategy B (Layout Model)
- **Key Features**: Tables, charts, time-series data

---

## Operational Notes

1. **Confidence Thresholds**:
   - > 0.95: High confidence - auto-approve
   - 0.80-0.95: Medium confidence - review recommended
   - < 0.80: Low confidence - manual review required

2. **Retry Logic**:
   - Strategy A failures → retry with Strategy B
   - Strategy B failures → retry with Strategy C
   - Strategy C failures → flag for manual processing

3. **Batch Processing**:
   - Group by document class for efficiency
   - Process similar strategies in parallel
   - Monitor API rate limits
