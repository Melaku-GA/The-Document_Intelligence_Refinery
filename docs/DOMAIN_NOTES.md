## Triage Heuristics (v1)

- Documents with avg_chars_per_page < 10 and image_area_ratio > 0.5
  are classified as scanned_image.
- Documents with avg_chars_per_page > 100 and image_area_ratio < 0.2
  are classified as native_digital.
- Mixed cases are classified as mixed and routed to layout-aware extraction.

These thresholds were validated empirically on representative PDFs.