# Document Intelligence Refinery - Cost Analysis

## Executive Summary

This document provides detailed cost estimates for document processing using the three extraction strategies in the Document Intelligence Refinery. Costs are analyzed per document type and strategy tier.

---

## Strategy Cost Matrix

### Base Costs Per Page

| Strategy | Description | Cost Per Page | Setup Cost | Best Use Case |
|----------|-------------|---------------|------------|---------------|
| **Strategy A** | Fast Text Extraction | $0.001 | $0.00 | Native digital PDFs with clear text |
| **Strategy B** | Layout-Aware (Mineru) | $0.005 | $0.00 | Complex layouts, tables, native PDFs |
| **Strategy C** | Vision Model | $0.020 | $0.00 | Scanned documents, images, complex visuals |

### Document Class Cost Estimates

#### Class A: Annual Financial Reports (50-300 pages)

| Metric | Strategy A | Strategy B | Strategy C |
|--------|------------|------------|------------|
| **Avg Pages** | 150 | 150 | 150 |
| **Processing Time** | 3 min | 7.5 min | 25 min |
| **Cost per Doc** | $0.15 | $0.75 | $3.00 |
| **Accuracy (Text)** | 99% | 97% | 95% |
| **Accuracy (Layout)** | 70% | 95% | 90% |
| **Recommended** | ❌ | ✅ | ❌ |

**Recommendation**: Strategy B - Optimal balance of cost and layout preservation for financial tables.

#### Class B: Scanned Government/Legal (10-50 pages)

| Metric | Strategy A | Strategy B | Strategy C |
|--------|------------|------------|------------|
| **Avg Pages** | 25 | 25 | 25 |
| **Processing Time** | 30 sec | 2 min | 6 min |
| **Cost per Doc** | $0.025 | $0.125 | $0.50 |
| **Accuracy (Text)** | 60%* | 85% | 95% |
| **Accuracy (Layout)** | 40%* | 80% | 90% |
| **Recommended** | ❌ | ❌ | ✅ |

*Strategy A fails on scanned documents due to lack of OCR

**Recommendation**: Strategy C - Required for scanned documents with potential OCR needs.

#### Class C: Technical Assessment (20-100 pages)

| Metric | Strategy A | Strategy B | Strategy C |
|--------|------------|------------|------------|
| **Avg Pages** | 50 | 50 | 50 |
| **Processing Time** | 1 min | 4 min | 12 min |
| **Cost per Doc** | $0.05 | $0.25 | $1.00 |
| **Accuracy (Text)** | 95% | 95% | 97% |
| **Accuracy (Layout)** | 65% | 92% | 95% |
| **Recommended** | ❌ | ✅ | ✅ |

**Recommendation**: Strategy C for documents with diagrams, Strategy B for text-heavy technical docs.

#### Class D: Structured Data Reports (CPI, Budgets) (5-20 pages)

| Metric | Strategy A | Strategy B | Strategy C |
|--------|------------|------------|------------|
| **Avg Pages** | 10 | 10 | 10 |
| **Processing Time** | 15 sec | 45 sec | 2.5 min |
| **Cost per Doc** | $0.01 | $0.05 | $0.20 |
| **Accuracy (Text)** | 99% | 98% | 96% |
| **Accuracy (Tables)** | 60% | 95% | 90% |
| **Recommended** | ❌ | ✅ | ❌ |

**Recommendation**: Strategy B - Table structure preservation critical for data reports.

---

## Total Cost of Ownership

### Annual Processing Volume Estimates

Assuming a processing load of **500 documents per year**:

| Document Class | Volume | Avg Pages | Strategy | Cost/Doc | Annual Cost |
|---------------|--------|-----------|----------|----------|-------------|
| Class A (Financial) | 50 | 150 | B | $0.75 | $37.50 |
| Class B (Government) | 150 | 25 | C | $0.50 | $75.00 |
| Class C (Technical) | 100 | 50 | C | $1.00 | $100.00 |
| Class D (Structured) | 200 | 10 | B | $0.05 | $10.00 |

**Total Annual Cost: $222.50**

---

## Cost Optimization Strategies

### 1. Tiered Processing

```
┌─────────────────────────────────────────────────────────────┐
│                  TIERED PROCESSING FLOW                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Quick Triage    │
                    │  (Identify Type) │
                    └──────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
    ┌────────────┐     ┌────────────┐     ┌────────────┐
    │  Simple    │     │  Complex   │     │  Scanned   │
    │  Native    │     │  Layout    │     │  Complex   │
    └────────────┘     └────────────┘     └────────────┘
           │                  │                  │
           ▼                  ▼                  ▼
    ┌────────────┐     ┌────────────┐     ┌────────────┐
    │ STRATEGY A │     │ STRATEGY B │     │ STRATEGY C │
    │ $0.001/pg  │     │ $0.005/pg  │     │ $0.020/pg  │
    └────────────┘     └────────────┘     └────────────┘
```

### 2. Smart Retry Logic

| Initial Strategy | Failure Condition | Retry With | Additional Cost |
|-----------------|-------------------|------------|-----------------|
| Strategy A | Low text quality | Strategy B | +$0.004/page |
| Strategy B | Layout parse failure | Strategy C | +$0.015/page |
| Strategy C | Vision timeout | Strategy B | -$0.015/page |

### 3. Batch Processing Discounts

| Batch Size | Discount | Effective Rate (Strategy B) |
|------------|----------|----------------------------|
| 1-10 | 0% | $0.005/page |
| 11-50 | 10% | $0.0045/page |
| 51-100 | 20% | $0.004/page |
| 100+ | 30% | $0.0035/page |

---

## Cost Comparison by Document Size

### Strategy A (Fast Text)

| Document Size | Pages | Cost | Time | Suitable For |
|---------------|-------|------|------|--------------|
| Small | 1-10 | $0.01 | 10 sec | Simple reports |
| Medium | 11-50 | $0.05 | 50 sec | Memos, letters |
| Large | 51-100 | $0.10 | 2 min | Short reports |
| X-Large | 100+ | $0.10+ | 3+ min | Not recommended |

### Strategy B (Mineru Layout)

| Document Size | Pages | Cost | Time | Recommended For |
|---------------|-------|------|------|-----------------|
| Small | 1-10 | $0.05 | 30 sec | Forms, CPI reports |
| Medium | 11-50 | $0.25 | 2 min | Annual reports |
| Large | 51-100 | $0.50 | 5 min | Large reports |
| X-Large | 100+ | $0.50+ | 10+ min | Comprehensive docs |

### Strategy C (Vision Model)

| Document Size | Pages | Cost | Time | Best For |
|---------------|-------|------|------|----------|
| Small | 1-10 | $0.20 | 2 min | Scanned forms |
| Medium | 11-50 | $1.00 | 6 min | Scanned reports |
| Large | 51-100 | $2.00 | 15 min | Large scans |
| X-Large | 100+ | $2.00+ | 25+ min | Archive scanning |

---

## ROI Analysis

### Cost Savings by Avoiding Manual Processing

| Activity | Manual Cost | Automated Cost | Savings |
|----------|-------------|----------------|---------|
| Text Extraction | $0.50/page | $0.001-0.02/page | 96-99% |
| Table Extraction | $2.00/page | $0.005/page | 99.7% |
| Document Classification | $0.10/doc | $0.001/doc | 99% |
| Layout Analysis | $1.00/page | $0.005/page | 99.5% |

### Break-Even Analysis

- **Manual Processing Cost**: ~$2.00/page
- **Automated (Strategy A)**: ~$0.001/page
- **Break-even**: 1 page
- **Savings per 100-page document**: $199.90

---

## Budget Recommendations

### Small Team (10 docs/month)

| Item | Monthly Cost |
|------|--------------|
| Strategy A (20%) | $0.50 |
| Strategy B (50%) | $12.50 |
| Strategy C (30%) | $30.00 |
| **Total** | **$43.00/month** |

### Medium Team (50 docs/month)

| Item | Monthly Cost |
|------|--------------|
| Strategy A (15%) | $3.75 |
| Strategy B (50%) | $62.50 |
| Strategy C (35%) | $175.00 |
| **Total** | **$241.25/month** |

### Large Team (200 docs/month)

| Item | Monthly Cost |
|------|--------------|
| Strategy A (10%) | $10.00 |
| Strategy B (50%) | $250.00 |
| Strategy C (40%) | $800.00 |
| **Total** | **$1,060.00/month** |

---

## Appendix: Cost Calculation Formulas

```python
def calculate_cost(pages: int, strategy: Strategy) -> float:
    """
    Calculate processing cost for a document.
    
    Strategy A: $0.001 * pages
    Strategy B: $0.005 * pages
    Strategy C: $0.020 * pages
    """
    rates = {
        Strategy.A: 0.001,
        Strategy.B: 0.005,
        Strategy.C: 0.020
    }
    return rates[strategy] * pages


def calculate_total_annual_cost(documents: List[Document]) -> float:
    """Calculate total annual processing cost."""
    return sum(calculate_cost(doc.pages, doc.strategy) for doc in documents)
```
