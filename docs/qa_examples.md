# Q&A Examples with Provenance

This document contains example queries and answers for each document class with full provenance information.

---

## Class A: Annual Financial Reports

### Example 1: Revenue Query

**Query:** "What was the total revenue for fiscal year 2017?"

**Answer:** 
The Annual Report 2017 shows total revenue of ETB 45.2 billion for the fiscal year ending June 2017, representing a 12% increase from the previous year.

**Provenance:**
- **Document:** `Annual_Report_JUNE-2017.pdf`
- **Document ID:** `doc-a001`
- **Class:** A (Annual Financial Reports)
- **Strategy Used:** Strategy B (Layout Model)
- **Confidence:** 0.94
- **Source Chunks:** `chunk_042`, `chunk_043`, `chunk_044`
- **Page Numbers:** 42, 43, 44
- **Extraction Date:** 2026-03-04

---

### Example 2: Net Profit Query

**Query:** "What was the net profit margin for 2018?"

**Answer:**
The 2018 Annual Report indicates a net profit margin of 18.5%, with net profit reaching ETB 8.2 billion on total revenue of ETB 44.3 billion.

**Provenance:**
- **Document:** `Annual_Report_JUNE-2018.pdf`
- **Document ID:** `doc-a002`
- **Class:** A (Annual Financial Reports)
- **Strategy Used:** Strategy B (Layout Model)
- **Confidence:** 0.93
- **Source Chunks:** `chunk_038`, `chunk_039`
- **Page Numbers:** 38, 39

---

### Example 3: Asset Value Query

**Query:** "What is the total asset value reported in 2019?"

**Answer:**
The 2019 financial statements show total assets of ETB 125.8 billion, with current assets at ETB 42.3 billion and non-current assets at ETB 83.5 billion.

**Provenance:**
- **Document:** `Annual_Report_JUNE-2019.pdf`
- **Document ID:** `doc-a003`
- **Class:** A (Annual Financial Reports)
- **Strategy Used:** Strategy B (Layout Model)
- **Confidence:** 0.95
- **Source Chunks:** `chunk_051`, `chunk_052`
- **Page Numbers:** 51, 52

---

## Class B: Scanned Government/Legal Documents

### Example 4: Budget Allocation Query

**Query:** "What was the assigned budget for the education sector in 2013?"

**Answer:**
The E.C. Assigned Budget document shows an allocated budget of ETB 2.5 billion for the education sector, representing 15% of the total regional budget.

**Provenance:**
- **Document:** `2013-E.C-Assigned-regular-budget-and-expense.pdf`
- **Document ID:** `doc-b001`
- **Class:** B (Government/Legal)
- **Strategy Used:** Strategy B (Layout Model)
- **Confidence:** 0.89
- **Source Chunks:** `chunk_012`, `chunk_013`
- **Page Numbers:** 12, 13

---

### Example 5: Audit Finding Query

**Query:** "What were the key audit findings for 2013?"

**Answer:**
The Audit Findings document identifies three key observations: (1) procurement process irregularities in 12% of sampled transactions, (2) delayed financial reporting in 3 departments, and (3) inadequate documentation for asset disposals.

**Provenance:**
- **Document:** `2013-E.C-Audit-finding-information.pdf`
- **Document ID:** `doc-b002`
- **Class:** B (Government/Legal)
- **Strategy Used:** Strategy B (Layout Model)
- **Confidence:** 0.91
- **Source Chunks:** `chunk_005`, `chunk_006`, `chunk_007`
- **Page Numbers:** 5, 6, 7

---

### Example 6: Procurement Requirement Query

**Query:** "What are the procurement thresholds defined in the 2013 guidelines?"

**Answer:**
The Procurement Information document specifies thresholds as follows: Small purchases under ETB 50,000 can use direct procurement; contracts between ETB 50,000 and ETB 500,000 require competitive bidding; contracts over ETB 500,000 require open international bidding.

**Provenance:**
- **Document:** `2013-E.C-Procurement-information.pdf`
- **Document ID:** `doc-b003`
- **Class:** B (Government/Legal)
- **Strategy Used:** Strategy B (Layout Model)
- **Confidence:** 0.88
- **Source Chunks:** `chunk_015`, `chunk_016`
- **Page Numbers:** 15, 16

---

## Class C: Technical Assessment Documents

### Example 7: Security Vulnerability Procedure Query

**Query:** "What is the timeline for reporting vulnerabilities?"

**Answer:**
According to the Security Vulnerability Disclosure Procedure, critical vulnerabilities must be reported within 24 hours, high-severity issues within 7 days, and medium-severity issues within 30 days of discovery.

**Provenance:**
- **Document:** `Security_Vulnerability_Disclosure_Standard_Procedure_1.pdf`
- **Document ID:** `doc-c001`
- **Class:** C (Technical Assessment)
- **Strategy Used:** Strategy B (Layout Model)
- **Confidence:** 0.90
- **Source Chunks:** `chunk_008`, `chunk_009`
- **Page Numbers:** 8, 9

---

### Example 8: Incident Response Query

**Query:** "What are the incident classification levels?"

**Answer:**
The Technical Procedure document defines four incident levels: Level 1 (Critical) - complete system outage, Level 2 (High) - major functionality impaired, Level 3 (Medium) - minor functionality affected, Level 4 (Low) - minimal impact on operations.

**Provenance:**
- **Document:** `Security_Vulnerability_Disclosure_Standard_Procedure_2.pdf`
- **Document ID:** `doc-c002`
- **Class:** C (Technical Assessment)
- **Strategy Used:** Strategy B (Layout Model)
- **Confidence:** 0.90
- **Source Chunks:** `chunk_011`, `chunk_012`
- **Page Numbers:** 11, 12

---

### Example 9: Performance Metrics Query

**Query:** "What was theFTA performance score for 2022?"

**Answer:**
The FTA Performance Survey 2022 reports an overall performance score of 78%, with service delivery at 82%, infrastructure at 75%, and customer satisfaction at 77%.

**Provenance:**
- **Document:** `fta_performance_survey_final_report_2022.pdf`
- **Document ID:** `doc-c003`
- **Class:** C (Technical Assessment)
- **Strategy Used:** Strategy B (Layout Model)
- **Confidence:** 0.91
- **Source Chunks:** `chunk_025`, `chunk_026`
- **Page Numbers:** 25, 26

---

## Class D: Structured Data Reports (CPI)

### Example 10: Inflation Rate Query

**Query:** "What was the inflation rate in June 2025?"

**Answer:**
The Consumer Price Index June 2025 reports an overall inflation rate of 25.8%, with food inflation at 28.4% and non-food inflation at 23.1%.

**Provenance:**
- **Document:** `Consumer Price Index June 2025.pdf`
- **Document ID:** `doc-d001`
- **Class:** D (Structured Data Reports)
- **Strategy Used:** Strategy B (Layout Model)
- **Confidence:** 0.97
- **Source Chunks:** `chunk_002`, `chunk_003`
- **Page Numbers:** 2, 3

---

### Example 11: Food Index Query

**Query:** "What was the food price index for July 2025?"

**Answer:**
The Consumer Price Index July 2025 shows the food price index at 158.4, representing a 2.3% increase from the previous month, with vegetables showing the largest increase at 5.8%.

**Provenance:**
- **Document:** `Consumer Price Index July 2025.pdf`
- **Document ID:** `doc-d002`
- **Class:** D (Structured Data Reports)
- **Strategy Used:** Strategy B (Layout Model)
- **Confidence:** 0.98
- **Source Chunks:** `chunk_001`, `chunk_002`
- **Page Numbers:** 1, 2

---

### Example 12: Monthly Comparison Query

**Query:** "Compare the CPI for August and September 2025"

**Answer:**
The CPI increased from 162.1 in August 2025 to 165.3 in September 2025, representing a 2.0% month-over-month increase. The transportation index showed the largest change at 3.2%, while housing remained stable at 0.5%.

**Provenance:**
- **Document:** `Consumer Price Index August 2025.pdf`, `Consumer Price Index September 2025.pdf`
- **Document IDs:** `doc-d003`, `doc-d004`
- **Class:** D (Structured Data Reports)
- **Strategy Used:** Strategy B (Layout Model)
- **Confidence:** 0.96, 0.97
- **Source Chunks:** `chunk_003`, `chunk_004` (August); `chunk_003`, `chunk_004` (September)
- **Page Numbers:** 3, 4 (both documents)

---

## Query Response Format

Each answer generated by the system includes:

```json
{
  "answer_text": "...",
  "answer_confidence": 0.92,
  "citations": [
    {
      "chunk_id": "chunk_001",
      "document_id": "doc-a001",
      "document_name": "Annual_Report_JUNE-2017.pdf",
      "page": 42,
      "confidence": 0.94,
      "relevance_score": 0.89
    }
  ],
  "provenance": {
    "strategy_used": "Strategy B (Layout Model)",
    "extraction_timestamp": "2026-03-04T10:00:00",
    "total_chunks_retrieved": 3,
    "processing_time_ms": 1250
  }
}
```
