from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExtractedChunk:
    content: str
    chunk_type: str  # text | table | image
    page: int | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ParsedDocument:
    source_path: Path
    chunks: list[ExtractedChunk]
    page_count: int = 0
