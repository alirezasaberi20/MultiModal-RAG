"""OpenAI embeddings and vision-based image captioning with cost tracking."""

from __future__ import annotations

import base64
import logging
import time
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from openai import OpenAI

from app.config import get_settings
from app.rag.cost_tracker import CostAccumulator, Timer, TokenUsage, count_tokens
from app.rag.ingestion.models import ExtractedChunk

logger = logging.getLogger(__name__)
settings = get_settings()

MIN_IMAGE_BYTES = 2_000
MAX_IMAGES_PER_DOC = 20
VISION_DELAY_SECONDS = 1.5


class MultimodalEmbedder:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set. Add it to your .env file.")
        self.embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            openai_api_key=settings.openai_api_key,
        )
        self.vision_client = OpenAI(api_key=settings.openai_api_key)
        self.vision_model = settings.openai_vision_model

    def _caption_image(
        self, image_path: Path, cost_acc: CostAccumulator | None = None
    ) -> str:
        try:
            image_bytes = image_path.read_bytes()

            if len(image_bytes) < MIN_IMAGE_BYTES:
                logger.info("Skipping tiny image (%d bytes): %s", len(image_bytes), image_path.name)
                return f"Small decorative image: {image_path.name}"

            b64 = base64.b64encode(image_bytes).decode("utf-8")
            suffix = image_path.suffix.lower().lstrip(".")
            mime = "image/jpeg" if suffix in ("jpg", "jpeg") else f"image/{suffix or 'png'}"

            prompt_text = (
                "Describe this image from a document in detail. "
                "Include any visible text, charts, diagrams, or data. "
                "Be concise but complete enough for search retrieval."
            )

            with Timer() as timer:
                response = self.vision_client.chat.completions.create(
                    model=self.vision_model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt_text},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime};base64,{b64}",
                                        "detail": "low",
                                    },
                                },
                            ],
                        }
                    ],
                    max_tokens=300,
                )

            if cost_acc and response.usage:
                cost_acc.add(TokenUsage(
                    operation="vision",
                    model=self.vision_model,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    latency_ms=timer.elapsed_ms,
                ))

            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.warning("Vision caption failed for %s: %s", image_path, exc)
            return f"Image at {image_path.name}"

    def prepare_for_embedding(
        self,
        chunks: list[ExtractedChunk],
        cost_acc: CostAccumulator | None = None,
    ) -> list[ExtractedChunk]:
        prepared: list[ExtractedChunk] = []
        image_count = 0

        for chunk in chunks:
            if chunk.chunk_type == "image":
                image_path = chunk.metadata.get("image_path")
                if not image_path:
                    prepared.append(chunk)
                    continue

                image_count += 1
                if image_count > MAX_IMAGES_PER_DOC:
                    logger.info("Reached image cap (%d), skipping: %s", MAX_IMAGES_PER_DOC, image_path)
                    prepared.append(ExtractedChunk(
                        content=f"[Image on page {chunk.page}] (skipped — cap reached)",
                        chunk_type="image",
                        page=chunk.page,
                        metadata=chunk.metadata,
                    ))
                    continue

                if image_count > 1:
                    time.sleep(VISION_DELAY_SECONDS)

                caption = self._caption_image(Path(image_path), cost_acc)
                content = f"[Image description] {caption}"
                prepared.append(ExtractedChunk(
                    content=content,
                    chunk_type="image",
                    page=chunk.page,
                    metadata={**chunk.metadata, "caption": caption},
                ))
            else:
                prepared.append(chunk)

        if image_count > 0:
            logger.info("Captioned %d images (cap: %d)", min(image_count, MAX_IMAGES_PER_DOC), MAX_IMAGES_PER_DOC)

        return prepared

    def embed_texts(
        self,
        texts: list[str],
        cost_acc: CostAccumulator | None = None,
    ) -> list[list[float]]:
        total_tokens = sum(count_tokens(t, settings.openai_embedding_model) for t in texts)

        batch_size = 100
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            with Timer() as timer:
                result = self.embeddings.embed_documents(batch)
            all_embeddings.extend(result)

            if cost_acc:
                batch_tokens = sum(count_tokens(t, settings.openai_embedding_model) for t in batch)
                cost_acc.add(TokenUsage(
                    operation="embed",
                    model=settings.openai_embedding_model,
                    input_tokens=batch_tokens,
                    output_tokens=0,
                    latency_ms=timer.elapsed_ms,
                ))

        return all_embeddings
