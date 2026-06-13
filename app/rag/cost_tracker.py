"""Token counting and cost estimation for OpenAI API calls."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import tiktoken

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# USD per 1M tokens — updated for current OpenAI pricing
MODEL_PRICING: dict[str, dict[str, float]] = {
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
}


@dataclass
class TokenUsage:
    operation: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def cost_usd(self) -> float:
        pricing = MODEL_PRICING.get(self.model, {"input": 0.0, "output": 0.0})
        input_cost = (self.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (self.output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 8)


@dataclass
class CostAccumulator:
    """Accumulates costs across multiple API calls within a single request."""
    usages: list[TokenUsage] = field(default_factory=list)

    def add(self, usage: TokenUsage) -> None:
        self.usages.append(usage)

    @property
    def total_tokens(self) -> int:
        return sum(u.total_tokens for u in self.usages)

    @property
    def total_cost_usd(self) -> float:
        return round(sum(u.cost_usd for u in self.usages), 8)

    @property
    def total_latency_ms(self) -> int:
        return sum(u.latency_ms for u in self.usages)

    @property
    def embedding_tokens(self) -> int:
        return sum(u.total_tokens for u in self.usages if u.operation == "embed")

    @property
    def chat_input_tokens(self) -> int:
        return sum(u.input_tokens for u in self.usages if u.operation == "chat")

    @property
    def chat_output_tokens(self) -> int:
        return sum(u.output_tokens for u in self.usages if u.operation == "chat")


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


class Timer:
    """Context manager for measuring elapsed time in milliseconds."""

    def __init__(self) -> None:
        self.elapsed_ms: int = 0
        self._start: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self.elapsed_ms = int((time.perf_counter() - self._start) * 1000)
