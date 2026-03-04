import pdfplumber

def analyze_pdf_metrics(pdf_path: str) -> dict:
    """Analyze PDF and return metrics for triage classification."""
    total_chars = 0
    total_pages = 0
    image_area = 0.0
    page_area = 0.0
    total_tables = 0
    table_area = 0.0
    text_sample_parts = []
    form_field_count = 0
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            total_pages += 1

            # Page area (points^2)
            page_area += page.width * page.height

            # Text extraction
            text = page.extract_text() or ""
            total_chars += len(text)
            
            # Collect text sample (first 1000 chars per page, max 5000 total)
            if len(text_sample_parts) < 5000:
                text_sample_parts.append(text[:1000])

            # Images
            for img in page.images:
                image_area += img["width"] * img["height"]

            # Tables
            tables = page.extract_tables()
            if tables:
                total_tables += len(tables)
                # Estimate table area (heuristic: assume 50% of page area per table)
                table_area += (page.width * page.height * 0.5) * len(tables)

    avg_chars_per_page = total_chars / max(total_pages, 1)
    image_area_ratio = image_area / max(page_area, 1)
    table_area_ratio = table_area / max(page_area, 1)
    
    # Column count estimation (basic heuristic)
    # Check if text has multiple distinct x-position clusters
    column_count = _estimate_column_count(pdf_path)

    return {
        "pages": total_pages,
        "avg_chars_per_page": avg_chars_per_page,
        "image_area_ratio": image_area_ratio,
        "text_sample": " ".join(text_sample_parts),
        "table_count": total_tables,
        "table_area_ratio": table_area_ratio,
        "form_fields": form_field_count,
        "column_count": column_count,
    }


def _estimate_column_count(pdf_path: str) -> int:
    """Estimate number of columns in the document."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Sample first few pages
            sample_pages = min(3, len(pdf.pages))
            x_positions = []
            
            for i in range(sample_pages):
                text = pdf.pages[i].extract_text()
                if not text:
                    continue
                    
                # Extract character positions (rough approximation)
                # This is a simple heuristic - in reality would need more sophisticated analysis
                lines = text.split('\n')
                for line in lines[:20]:  # Check first 20 lines per page
                    if len(line) > 50:  # Only consider substantial lines
                        # Estimate based on indentation patterns
                        leading_spaces = len(line) - len(line.lstrip())
                        if leading_spaces > 20:
                            x_positions.append(leading_spaces)
            
            if not x_positions:
                return 1
            
            # Count distinct x-position clusters
            clusters = 1
            sorted_positions = sorted(set(x_positions))
            for i in range(1, len(sorted_positions)):
                if sorted_positions[i] - sorted_positions[i-1] > 30:
                    clusters += 1
            
            return min(clusters, 4)  # Cap at 4 columns
    except Exception:
        return 1