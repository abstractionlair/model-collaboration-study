"""Minimal experiment runner.

Drives a `ConditionSpec` against a `Benchmark`: iterates
tasks, calls `run()`, extracts the final response text, scores
it, and records per-task attribution (tokens, dollars,
telemetry, elapsed, capability/infra failures).

Deliberately minimal. Does NOT enforce `BudgetTier` caps — that
requires the dollar calibration that precedes Phase 1 kickoff
and is handled separately. Does NOT parallelize — runs tasks
sequentially. Good enough for framework-validation and small-
scale runs; will grow into the full runner as the
infrastructure track resumes.
"""

from __future__ import annotations

import logging
import time
import traceback
from dataclasses import dataclass, field
from typing import Any

from src.executor import (
    ApiClient,
    CapabilityFailure,
    InfrastructureError,
    InterpreterTelemetry,
    run,
)
from src.experiment.benchmarks.base import Benchmark, ScoreResult
from src.experiment.spec import ConditionSpec, PricingTable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TaskResult:
    """Outcome of running one ConditionSpec against one task."""

    task_id: str
    condition_name: str
    passed: bool
    fraction: float
    detail: str
    elapsed_seconds: float
    # Per-task token and cost rollups, derived from the slice of
    # `client.calls` produced during this task.
    input_tokens: int
    output_tokens: int
    dollars: float
    successful_calls: int
    capability_failures: int
    infra_failures: int
    # Non-fatal event counters from the interpreter.
    score_parse_failures: int
    pick_parse_failures: int
    weighted_vote_ties: int
    # If the macro-model aborted with an exception, this holds
    # the classification. None means the task completed (even if
    # it failed the score).
    aborted: str | None = None


@dataclass(frozen=True)
class ConditionResults:
    """Aggregate results for one ConditionSpec across all tasks."""

    condition_name: str
    task_results: list[TaskResult]

    @property
    def pass_rate(self) -> float:
        scored = [r for r in self.task_results if r.aborted is None]
        if not scored:
            return 0.0
        return sum(r.fraction for r in scored) / len(scored)

    @property
    def total_dollars(self) -> float:
        return sum(r.dollars for r in self.task_results)

    @property
    def abort_count(self) -> int:
        return sum(1 for r in self.task_results if r.aborted is not None)


def run_condition(
    condition: ConditionSpec,
    benchmark: Benchmark,
    client: ApiClient,
    pricing: PricingTable,
    seed: int = 0,
) -> ConditionResults:
    """Run a ConditionSpec against every task in a benchmark.

    Uses a shared `ApiClient` across all tasks (so CallRecord
    history accumulates); snapshots `len(client.calls)` before
    each task so per-task cost attribution is derivable from
    the slice.

    `seed` is passed to `run()` as the interpreter seed. For
    multi-seed runs, invoke this function multiple times with
    different seeds.
    """
    task_results: list[TaskResult] = []
    for task in benchmark.tasks():
        call_start = len(client.calls)
        t0 = time.monotonic()
        aborted: str | None = None
        telemetry: InterpreterTelemetry = InterpreterTelemetry()
        response_text = ""
        try:
            result, telemetry = run(
                condition.protocol, client, task.query_text, seed=seed,
            )
            response_text = result.text
        except CapabilityFailure as e:
            aborted = f"capability_failure: {e}"
        except InfrastructureError as e:
            aborted = f"infra_failure: {e}"
        except Exception as e:
            # Anything else is NOT a classified model/infra failure —
            # it may be a harness bug. Keep the sweep alive (one bad
            # task must not kill a long run) but record the full
            # traceback in the abort record and log it loudly, so a
            # code bug cannot masquerade as a model failure in the
            # aggregates.
            logger.exception(
                "unexpected exception (possible harness bug) "
                "task=%s condition=%s", task.id, condition.name,
            )
            aborted = (
                f"unexpected_error: {type(e).__name__}: {e}\n"
                f"{traceback.format_exc()}"
            )
        elapsed = time.monotonic() - t0

        # Score if we have a response at all. Aborted runs get a
        # ScoreResult with passed=False so the aggregate reflects
        # them as failures rather than as missing data.
        if aborted is None:
            score = benchmark.score(task.id, response_text)
        else:
            score = ScoreResult(
                passed=False, fraction=0.0, detail=aborted,
            )

        # Per-task call slice
        task_calls = client.calls[call_start:]
        input_tokens = sum(c.input_tokens for c in task_calls)
        output_tokens = sum(c.output_tokens for c in task_calls)
        # Fail loud on unpriced models. Compute-matched dollar
        # accounting is load-bearing for the study design: a call
        # silently contributing $0 makes a condition look cheaper
        # than it is, corrupting the $X/$2X/$4X budget comparison.
        unpriced = sorted({
            c.model for c in task_calls if c.model not in pricing.entries
        })
        if unpriced:
            raise ValueError(
                f"pricing table has no entry for model(s) {unpriced} "
                f"(task={task.id!r}, condition={condition.name!r}). "
                "Refusing to compute dollar totals that would silently "
                "omit these calls; add a PricingEntry for every model "
                "the condition can invoke."
            )
        dollars = sum(
            pricing.cost(c.model, c.input_tokens, c.output_tokens)
            for c in task_calls
        )
        task_results.append(TaskResult(
            task_id=task.id,
            condition_name=condition.name,
            passed=score.passed,
            fraction=score.fraction,
            detail=score.detail,
            elapsed_seconds=elapsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            dollars=dollars,
            successful_calls=sum(
                1 for c in task_calls if c.status == "success"
            ),
            capability_failures=sum(
                1 for c in task_calls if c.status == "capability_failure"
            ),
            infra_failures=sum(
                1 for c in task_calls if c.status == "infra_failure"
            ),
            score_parse_failures=telemetry.score_parse_failures,
            pick_parse_failures=telemetry.pick_parse_failures,
            weighted_vote_ties=telemetry.weighted_vote_ties,
            aborted=aborted,
        ))
        logger.info(
            "task=%s condition=%s pass=%s dollars=%.4f elapsed=%.1fs%s",
            task.id, condition.name, score.passed, dollars, elapsed,
            f" aborted={aborted}" if aborted else "",
        )

    return ConditionResults(
        condition_name=condition.name, task_results=task_results,
    )
