import pdfplumber

def analyze_pdf_metrics(pdf_path: str) -> dict:
    total_chars = 0
    total_pages = 0
    image_area = 0.0
    page_area = 0.0

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            total_pages += 1

            # Page area (points^2)
            page_area += page.width * page.height

            # Text
            text = page.extract_text() or ""
            total_chars += len(text)

            # Images
            for img in page.images:
                image_area += img["width"] * img["height"]

    avg_chars_per_page = total_chars / max(total_pages, 1)
    image_area_ratio = image_area / max(page_area, 1)

    return {
        "pages": total_pages,
        "avg_chars_per_page": avg_chars_per_page,
        "image_area_ratio": image_area_ratio,
    }