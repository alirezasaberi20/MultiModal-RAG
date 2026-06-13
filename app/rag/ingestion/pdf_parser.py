"""Extract text, tables, and images from PDF files."""

from __future__ import annotations

import io
import logging
from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber
from PIL import Image

from app.rag.ingestion.models import ExtractedChunk, ParsedDocument

logger = logging.getLogger(__name__)


def _table_to_markdown(table: list[list]) -> str:
    if not table:
        return ""
    rows = [[str(cell or "").strip() for cell in row] for row in table]
    if not rows:
        return ""
    header = rows[0]
    body = rows[1:] if len(rows) > 1 else []
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * len(header)) + " |",
    ]
    for row in body:
        padded = row + [""] * (len(header) - len(row))
        lines.append("| " + " | ".join(padded[: len(header)]) + " |")
    return "\n".join(lines)


class PDFParser:
    """Multimodal PDF parser using PyMuPDF and pdfplumber."""

    def __init__(self, images_output_dir: Path):
        self.images_output_dir = images_output_dir
        self.images_output_dir.mkdir(parents=True, exist_ok=True)

    def parse(self, pdf_path: Path, document_id: int) -> ParsedDocument:
        chunks: list[ExtractedChunk] = []
        page_count = 0

        with fitz.open(pdf_path) as doc:
            page_count = len(doc)
            for page_idx, page in enumerate(doc):
                page_num = page_idx + 1
                text = page.get_text("text").strip()
                if text:
                    chunks.append(
                        ExtractedChunk(
                            content=text,
                            chunk_type="text",
                            page=page_num,
                            metadata={"source": pdf_path.name},
                        )
                    )

                for img_idx, img_info in enumerate(page.get_images(full=True)):
                    try:
                        xref = img_info[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        ext = base_image.get("ext", "png")
                        image_name = f"doc{document_id}_p{page_num}_img{img_idx}.{ext}"
                        image_path = self.images_output_dir / image_name
                        image_path.write_bytes(image_bytes)

                        with Image.open(io.BytesIO(image_bytes)) as pil_img:
                            width, height = pil_img.size

                        chunks.append(
                            ExtractedChunk(
                                content=f"[Image on page {page_num}: {image_name}]",
                                chunk_type="image",
                                page=page_num,
                                metadata={
                                    "source": pdf_path.name,
                                    "image_path": str(image_path),
                                    "width": width,
                                    "height": height,
                                },
                            )
                        )
                    except Exception as exc:
                        logger.warning("Failed to extract image on page %s: %s", page_num, exc)

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    page_num = page_idx + 1
                    tables = page.extract_tables() or []
                    for table_idx, table in enumerate(tables):
                        md = _table_to_markdown(table)
                        if md.strip():
                            chunks.append(
                                ExtractedChunk(
                                    content=f"Table {table_idx + 1} (page {page_num}):\n{md}",
                                    chunk_type="table",
                                    page=page_num,
                                    metadata={
                                        "source": pdf_path.name,
                                        "table_index": table_idx,
                                    },
                                )
                            )
        except Exception as exc:
            logger.warning("Table extraction failed for %s: %s", pdf_path, exc)

        return ParsedDocument(source_path=pdf_path, chunks=chunks, page_count=page_count)
