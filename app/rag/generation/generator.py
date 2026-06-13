"""LLM answer generation with retrieved context and cost tracking."""

from __future__ import annotations

import logging
from collections.abc import Generator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.rag.cost_tracker import CostAccumulator, Timer, TokenUsage, count_tokens
from app.rag.storage.vector_store import RetrievedChunk

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on provided document context.
The context may include text passages, tables (in markdown), and image descriptions extracted from PDFs.

Rules:
- Answer only from the provided context. If the answer is not in the context, say you don't have enough information.
- When referencing tables or images, mention the page number when available.
- Cite which part of the context you used (e.g. [Source 1], [Source 2]).
- Be clear, accurate, and concise."""


def _build_context(context_chunks: list[RetrievedChunk]) -> str:
    parts = []
    for i, chunk in enumerate(context_chunks, 1):
        page_info = f" (page {chunk.page})" if chunk.page else ""
        parts.append(
            f"[Source {i}] Type: {chunk.chunk_type}{page_info} "
            f"| Doc: {chunk.document_name}\n{chunk.content}"
        )
    return "\n\n".join(parts)


class RAGGenerator:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        self.llm = ChatOpenAI(
            model=settings.openai_chat_model,
            openai_api_key=settings.openai_api_key,
            temperature=0.2,
        )
        self.streaming_llm = ChatOpenAI(
            model=settings.openai_chat_model,
            openai_api_key=settings.openai_api_key,
            temperature=0.2,
            streaming=True,
        )

    def _build_messages(
        self, query: str, context_chunks: list[RetrievedChunk]
    ) -> list[SystemMessage | HumanMessage]:
        context = _build_context(context_chunks)
        return [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"),
        ]

    def generate(
        self,
        query: str,
        context_chunks: list[RetrievedChunk],
        cost_acc: CostAccumulator | None = None,
    ) -> str:
        if not context_chunks:
            return "I don't have any indexed documents to answer from. Please upload and process PDFs first."

        messages = self._build_messages(query, context_chunks)

        input_text = SYSTEM_PROMPT + _build_context(context_chunks) + query
        input_tokens = count_tokens(input_text, settings.openai_chat_model)

        with Timer() as timer:
            response = self.llm.invoke(messages)

        answer = response.content or ""

        if cost_acc:
            output_tokens = count_tokens(answer, settings.openai_chat_model)
            cost_acc.add(TokenUsage(
                operation="chat",
                model=settings.openai_chat_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=timer.elapsed_ms,
            ))

        return answer

    def stream(
        self,
        query: str,
        context_chunks: list[RetrievedChunk],
    ) -> Generator[str, None, None]:
        if not context_chunks:
            yield "I don't have any indexed documents to answer from."
            return

        messages = self._build_messages(query, context_chunks)
        for chunk in self.streaming_llm.stream(messages):
            if chunk.content:
                yield chunk.content
