"""Tests for cost tracking utilities."""

from app.rag.cost_tracker import CostAccumulator, Timer, TokenUsage, count_tokens


class TestTokenUsage:
    def test_total_tokens(self):
        usage = TokenUsage(
            operation="chat", model="gpt-4o-mini",
            input_tokens=100, output_tokens=50,
        )
        assert usage.total_tokens == 150

    def test_cost_calculation_gpt4o_mini(self):
        usage = TokenUsage(
            operation="chat", model="gpt-4o-mini",
            input_tokens=1_000_000, output_tokens=1_000_000,
        )
        assert usage.cost_usd == 0.15 + 0.60

    def test_cost_calculation_embedding(self):
        usage = TokenUsage(
            operation="embed", model="text-embedding-3-small",
            input_tokens=1_000_000, output_tokens=0,
        )
        assert usage.cost_usd == 0.02

    def test_unknown_model_zero_cost(self):
        usage = TokenUsage(
            operation="chat", model="unknown-model",
            input_tokens=1000, output_tokens=500,
        )
        assert usage.cost_usd == 0.0


class TestCostAccumulator:
    def test_empty_accumulator(self):
        acc = CostAccumulator()
        assert acc.total_tokens == 0
        assert acc.total_cost_usd == 0.0

    def test_accumulate_multiple(self):
        acc = CostAccumulator()
        acc.add(TokenUsage("embed", "text-embedding-3-small", 100, 0, 10))
        acc.add(TokenUsage("chat", "gpt-4o-mini", 200, 50, 100))
        assert acc.total_tokens == 350
        assert acc.embedding_tokens == 100
        assert acc.chat_input_tokens == 200
        assert acc.chat_output_tokens == 50


class TestCountTokens:
    def test_count_simple_text(self):
        tokens = count_tokens("Hello, world!")
        assert tokens > 0

    def test_empty_string(self):
        assert count_tokens("") == 0


class TestTimer:
    def test_timer_measures_time(self):
        import time
        with Timer() as t:
            time.sleep(0.05)
        assert t.elapsed_ms >= 40
