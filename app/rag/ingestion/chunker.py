"""Split extracted content into retrieval-sized chunks."""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings
from app.rag.ingestion.models import ExtractedChunk

settings = get_settings()


def chunk_extracted_content(chunks: list[ExtractedChunk]) -> list[ExtractedChunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    result: list[ExtractedChunk] = []
    for chunk in chunks:
        if chunk.chunk_type in ("table", "image"):
            result.append(chunk)
            continue

        splits = splitter.split_text(chunk.content)
        for i, text in enumerate(splits):
            if not text.strip():
                continue
            result.append(
                ExtractedChunk(
                    content=text,
                    chunk_type=chunk.chunk_type,
                    page=chunk.page,
                    metadata={**chunk.metadata, "split_index": i},
                )
            )
    return result
