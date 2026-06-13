"""Per-user ChromaDB vector store with relevance filtering."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings
from app.rag.ingestion.models import ExtractedChunk

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class RetrievedChunk:
    content: str
    chunk_type: str
    page: int | None
    document_id: int
    document_name: str
    score: float
    metadata: dict


class UserVectorStore:
    def __init__(self, user_id: int) -> None:
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(settings.chroma_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection_name = f"user_{user_id}"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        chunks: list[ExtractedChunk],
        embeddings: list[list[float]],
        document_id: int,
        document_name: str,
    ) -> int:
        if not chunks:
            return 0

        ids = [str(uuid.uuid4()) for _ in chunks]
        documents = [c.content for c in chunks]
        metadatas = [
            {
                "chunk_type": c.chunk_type,
                "page": c.page if c.page is not None else -1,
                "document_id": document_id,
                "document_name": document_name,
                **{k: str(v) for k, v in c.metadata.items()},
            }
            for c in chunks
        ]

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(
            "Stored %d chunks in collection %s for document %d",
            len(chunks), self.collection_name, document_id,
        )
        return len(chunks)

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        document_ids: list[int] | None = None,
        min_score: float | None = None,
    ) -> list[RetrievedChunk]:
        collection_count = self.collection.count()
        logger.info(
            "Querying %s: %d total vectors, filter doc_ids=%s",
            self.collection_name, collection_count, document_ids,
        )

        if collection_count == 0:
            logger.warning("Collection %s is empty", self.collection_name)
            return []

        where_filter = None
        if document_ids:
            where_filter = {"document_id": {"$in": document_ids}}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection_count),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        retrieved: list[RetrievedChunk] = []
        if not results["documents"] or not results["documents"][0]:
            logger.warning("ChromaDB returned no results for %s", self.collection_name)
            return retrieved

        threshold = min_score if min_score is not None else settings.min_relevance_score

        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = 1.0 - dist
            logger.debug("Chunk score=%.4f, threshold=%.4f, type=%s", score, threshold, meta.get("chunk_type"))
            if score < threshold:
                continue

            page = meta.get("page", -1)
            retrieved.append(
                RetrievedChunk(
                    content=doc,
                    chunk_type=meta.get("chunk_type", "text"),
                    page=page if page != -1 else None,
                    document_id=int(meta.get("document_id", 0)),
                    document_name=meta.get("document_name", ""),
                    score=score,
                    metadata=meta,
                )
            )

        logger.info("Retrieved %d chunks (threshold=%.2f)", len(retrieved), threshold)
        return retrieved

    def get_collection_stats(self) -> dict:
        return {
            "name": self.collection_name,
            "count": self.collection.count(),
        }

    def delete_document(self, document_id: int) -> None:
        try:
            self.collection.delete(where={"document_id": document_id})
        except Exception:
            pass
