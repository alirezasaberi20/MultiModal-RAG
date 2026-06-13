"""Orchestrates the full multimodal RAG pipeline per user with cost tracking."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Generator
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Document, UsageLog
from app.rag.cost_tracker import CostAccumulator, Timer
from app.rag.ingestion.chunker import chunk_extracted_content
from app.rag.ingestion.pdf_parser import PDFParser
from app.rag.storage.vector_store import UserVectorStore
from app.schemas import ChatResponse, CostBreakdown, SourceChunk

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGPipeline:
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        self.user_dir = settings.user_storage_root / str(user_id)
        self.documents_dir = self.user_dir / "documents"
        self.images_dir = self.user_dir / "images"
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)

        self.parser = PDFParser(images_output_dir=self.images_dir)
        self._embedder = None
        self._generator = None
        self._vector_store = None

    @property
    def embedder(self):
        if self._embedder is None:
            from app.rag.embedding.embedder import MultimodalEmbedder
            self._embedder = MultimodalEmbedder()
        return self._embedder

    @property
    def generator(self):
        if self._generator is None:
            from app.rag.generation.generator import RAGGenerator
            self._generator = RAGGenerator()
        return self._generator

    @property
    def vector_store(self):
        if self._vector_store is None:
            self._vector_store = UserVectorStore(user_id=self.user_id)
        return self._vector_store

    def save_upload(self, filename: str, content: bytes) -> Path:
        safe_name = f"{uuid.uuid4().hex}_{Path(filename).name}"
        dest = self.documents_dir / safe_name
        dest.write_bytes(content)
        return dest

    def ingest_document(self, db: Session, document: Document) -> int:
        document.status = "processing"
        db.commit()

        start_ms = int(time.perf_counter() * 1000)
        cost_acc = CostAccumulator()

        try:
            pdf_path = Path(document.file_path)
            parsed = self.parser.parse(pdf_path, document_id=document.id)
            chunked = chunk_extracted_content(parsed.chunks)
            prepared = self.embedder.prepare_for_embedding(chunked, cost_acc)

            if not prepared:
                document.status = "failed"
                document.error_message = "No extractable content found in PDF."
                db.commit()
                return 0

            texts = [c.content for c in prepared]
            embeddings = self.embedder.embed_texts(texts, cost_acc)
            count = self.vector_store.add_chunks(
                chunks=prepared,
                embeddings=embeddings,
                document_id=document.id,
                document_name=document.original_name,
            )

            elapsed_ms = int(time.perf_counter() * 1000) - start_ms
            document.status = "ready"
            document.chunk_count = count
            document.processing_time_ms = elapsed_ms
            document.error_message = None
            db.commit()

            self._log_usage(db, cost_acc)

            logger.info(
                "Ingested document %s: %d chunks, %d tokens, $%.6f, %dms",
                document.id, count, cost_acc.total_tokens,
                cost_acc.total_cost_usd, elapsed_ms,
            )
            return count

        except Exception as exc:
            logger.exception("Ingestion failed for document %s", document.id)
            document.status = "failed"
            document.error_message = str(exc)
            db.commit()
            return 0

    def query(
        self,
        query: str,
        document_ids: list[int] | None = None,
    ) -> ChatResponse:
        cost_acc = CostAccumulator()

        with Timer() as embed_timer:
            query_embedding = self.embedder.embeddings.embed_query(query)

        from app.rag.cost_tracker import TokenUsage, count_tokens
        cost_acc.add(TokenUsage(
            operation="embed",
            model=settings.openai_embedding_model,
            input_tokens=count_tokens(query, settings.openai_embedding_model),
            output_tokens=0,
            latency_ms=embed_timer.elapsed_ms,
        ))

        retrieved = self.vector_store.query(
            query_embedding=query_embedding,
            top_k=settings.top_k_results,
            document_ids=document_ids,
        )

        answer = self.generator.generate(query, retrieved, cost_acc)

        sources = [
            SourceChunk(
                content=c.content[:500] + ("..." if len(c.content) > 500 else ""),
                chunk_type=c.chunk_type,
                page=c.page,
                document_name=c.document_name,
                score=round(c.score, 4),
            )
            for c in retrieved
        ]

        cost_breakdown = CostBreakdown(
            embedding_tokens=cost_acc.embedding_tokens,
            chat_input_tokens=cost_acc.chat_input_tokens,
            chat_output_tokens=cost_acc.chat_output_tokens,
            total_tokens=cost_acc.total_tokens,
            estimated_cost_usd=round(cost_acc.total_cost_usd, 6),
            latency_ms=cost_acc.total_latency_ms,
        )

        return ChatResponse(
            answer=answer,
            sources=sources,
            cost=cost_breakdown,
        )

    def stream_query(
        self,
        query: str,
        document_ids: list[int] | None = None,
    ) -> Generator[str, None, None]:
        query_embedding = self.embedder.embeddings.embed_query(query)

        retrieved = self.vector_store.query(
            query_embedding=query_embedding,
            top_k=settings.top_k_results,
            document_ids=document_ids,
        )

        yield from self.generator.stream(query, retrieved)

    def delete_document_vectors(self, document_id: int) -> None:
        self.vector_store.delete_document(document_id)

    def delete_document_files(self, file_path: str) -> None:
        path = Path(file_path)
        if path.exists():
            path.unlink()

    def _log_usage(self, db: Session, cost_acc: CostAccumulator) -> None:
        if not settings.cost_tracking_enabled:
            return
        for usage in cost_acc.usages:
            log = UsageLog(
                user_id=self.user_id,
                operation=usage.operation,
                model=usage.model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
                cost_usd=usage.cost_usd,
                latency_ms=usage.latency_ms,
            )
            db.add(log)
        db.commit()
