import uuid
from typing import List

from src.models.extracted_document import ExtractedDocument, TextBlock
from src.models.chunk import DocumentChunk


class LayoutAwareChunker:
    def __init__(self, max_chars: int = 800):
        self.max_chars = max_chars

    def chunk(self, document: ExtractedDocument) -> List[DocumentChunk]:
        """
        Chunk text blocks while preserving page order and layout flow.
        """
        chunks: List[DocumentChunk] = []

        # 1️⃣ Sort blocks: page → vertical position (bbox top)
        # TextBlock uses page_ref.page_number and page_ref.bbox
        sorted_blocks = sorted(
            document.text_blocks,
            key=lambda b: (
                b.page_ref.page_number,
                b.page_ref.bbox.y0 if b.page_ref.bbox else 0,
            ),
        )

        buffer = []
        buffer_len = 0

        for block in sorted_blocks:
            block_text = block.text.strip()

            if buffer_len + len(block_text) > self.max_chars:
                chunks.append(self._flush(buffer))
                buffer = []
                buffer_len = 0

            buffer.append(block)
            buffer_len += len(block_text)

        if buffer:
            chunks.append(self._flush(buffer))

        return chunks

    def _flush(self, blocks: List[TextBlock]) -> DocumentChunk:
        combined_text = "\n".join(b.text for b in blocks)
        # TextBlock from Pydantic model doesn't have confidence, use default
        avg_conf = 0.9  # Default confidence for Pydantic TextBlocks

        # Get page number and bbox from page_ref
        first_block = blocks[0]
        page = first_block.page_ref.page_number
        bbox = None
        if first_block.page_ref.bbox:
            bbox = [
                first_block.page_ref.bbox.x0,
                first_block.page_ref.bbox.y0,
                first_block.page_ref.bbox.x1,
                first_block.page_ref.bbox.y1,
            ]

        return DocumentChunk(
            chunk_id=str(uuid.uuid4()),
            text=combined_text,
            page=page,
            bbox=bbox,
            confidence=avg_conf,
        )
