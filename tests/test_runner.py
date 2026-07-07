"""Unit tests for `experiment/runner.py`.

Uses `ApiClient` with a stubbed `_call_anthropic` so per-task
cost attribution can exercise the CallRecord path without
actual network calls. Verifies the runner:
- Iterates tasks in order and accumulates per-task TaskResults.
- Snapshots `client.calls` per task to derive cost attribution.
- Applies pricing correctly.
- Fails loudly when a call's model has no pricing entry.
- Catches exceptions and records them as aborts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable
from unittest.mock import MagicMock

import pytest

from src.executor.api_client import ApiClient
from src.experiment.benchmarks import ScoreResult, Task
from src.experiment.runner import run_condition
from src.experiment.spec import (
    BudgetTier,
    ConditionSpec,
    PricingEntry,
    PricingTable,
)
from src.protocols.conditions import condition_a


@dataclass
class _StubBench:
    """Minimal in-memory Benchmark for runner tests."""

    name: str = "stub"
    _tasks: list[Task] = field(default_factory=list)
    _scores: dict[str, ScoreResult] = field(default_factory=dict)

    def tasks(self) -> Iterable[Task]:
        return list(self._tasks)

    def score(self, task_id: str, response: str) -> ScoreResult:
        return self._scores.get(
            task_id,
            ScoreResult(passed=False, fraction=0.0, detail="unknown"),
        )


_PRICING = PricingTable(
    entries={
        "claude-test": PricingEntry(
            "claude-test", input_per_1m=1.0, output_per_1m=2.0,
        ),
    },
)


def _stub_anthropic_client(
    response_text: str = "some code",
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> ApiClient:
    """Construct an ApiClient whose Anthropic call returns a
    canned response with specified token counts."""
    client = ApiClient(max_retries=0, backoff_base=0, backoff_max=0)
    client._route = lambda model: "anthropic"  # type: ignore[method-assign]
    client._call_anthropic = MagicMock(  # type: ignore[method-assign]
        return_value=(response_text, input_tokens, output_tokens),
    )
    return client


def test_runner_iterates_tasks_and_records_per_task() -> None:
    bench = _StubBench(
        _tasks=[
            Task(id="t1", query_text="what is 1+1?"),
            Task(id="t2", query_text="what is 2+2?"),
        ],
        _scores={
            "t1": ScoreResult(passed=True, fraction=1.0),
            "t2": ScoreResult(passed=False, fraction=0.0),
        },
    )
    client = _stub_anthropic_client(response_text="some code")
    condition = ConditionSpec(
        name="A", label="a", protocol=condition_a("claude-test"),
        budget_tier=BudgetTier.X, models=["claude-test"],
    )
    results = run_condition(condition, bench, client, _PRICING)

    assert len(results.task_results) == 2
    assert [r.task_id for r in results.task_results] == ["t1", "t2"]
    assert results.task_results[0].passed
    assert not results.task_results[1].passed
    for r in results.task_results:
        assert r.successful_calls == 1
        assert r.infra_failures == 0
        assert r.capability_failures == 0
        assert r.aborted is None


def test_runner_applies_pricing() -> None:
    """Per-task dollars should come from `pricing.cost()` applied
    to the slice of `client.calls` for that task."""
    bench = _StubBench(
        _tasks=[Task(id="t1", query_text="q")],
        _scores={"t1": ScoreResult(passed=True, fraction=1.0)},
    )
    # 1M input tokens @ $1/1M + 0.5M output @ $2/1M = $2.00
    client = _stub_anthropic_client(
        response_text="some code",
        input_tokens=1_000_000,
        output_tokens=500_000,
    )
    condition = ConditionSpec(
        name="A", label="a", protocol=condition_a("claude-test"),
        budget_tier=BudgetTier.X, models=["claude-test"],
    )
    results = run_condition(condition, bench, client, _PRICING)
    assert results.task_results[0].dollars == 2.0
    assert results.total_dollars == 2.0


def test_runner_raises_on_unpriced_model() -> None:
    """A call from a model with no pricing entry must abort the run
    loudly — NOT contribute $0 to the compute-matched dollar totals.
    Budget matching is load-bearing for the study design; silently
    dropped calls would make a condition look cheaper than it is."""
    bench = _StubBench(
        _tasks=[Task(id="t1", query_text="q")],
        _scores={"t1": ScoreResult(passed=True, fraction=1.0)},
    )
    client = _stub_anthropic_client(response_text="some code")
    condition = ConditionSpec(
        name="A", label="a", protocol=condition_a("claude-test"),
        budget_tier=BudgetTier.X, models=["claude-test"],
    )
    # Pricing table that does NOT cover "claude-test".
    other_pricing = PricingTable(
        entries={
            "some-other-model": PricingEntry(
                "some-other-model", input_per_1m=1.0, output_per_1m=2.0,
            ),
        },
    )
    with pytest.raises(ValueError, match="claude-test"):
        run_condition(condition, bench, client, other_pricing)


def test_runner_records_aborts_as_failures_not_exceptions() -> None:
    """CapabilityFailure at the API layer (e.g., empty response)
    should be caught and recorded as an abort — not propagated.
    """
    bench = _StubBench(
        _tasks=[Task(id="t1", query_text="q")],
        _scores={"t1": ScoreResult(passed=True, fraction=1.0)},
    )
    # Empty response → ApiClient raises CapabilityFailure.
    client = _stub_anthropic_client(response_text="   ")
    condition = ConditionSpec(
        name="A", label="a", protocol=condition_a("claude-test"),
        budget_tier=BudgetTier.X, models=["claude-test"],
    )
    results = run_condition(condition, bench, client, _PRICING)
    r = results.task_results[0]
    assert r.aborted is not None
    assert "capability_failure" in r.aborted
    assert not r.passed
    # The CallRecord for the capability failure should still count.
    assert r.capability_failures == 1


def test_runner_pass_rate_ignores_aborted_tasks() -> None:
    """pass_rate is computed over non-aborted tasks; abort_count
    is surfaced separately."""
    bench = _StubBench(
        _tasks=[
            Task(id="t1", query_text="q1"),
            Task(id="t2", query_text="q2"),
        ],
        _scores={
            "t1": ScoreResult(passed=True, fraction=1.0),
            "t2": ScoreResult(passed=True, fraction=1.0),
        },
    )
    client = _stub_anthropic_client(response_text="some code")
    condition = ConditionSpec(
        name="A", label="a", protocol=condition_a("claude-test"),
        budget_tier=BudgetTier.X, models=["claude-test"],
    )
    results = run_condition(condition, bench, client, _PRICING)
    assert results.pass_rate == 1.0
    assert results.abort_count == 0
