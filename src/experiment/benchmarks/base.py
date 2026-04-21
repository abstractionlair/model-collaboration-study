"""Benchmark abstraction: Task, ScoreResult, Benchmark protocol.

Small by design — this layer is what the runner iterates over.
Task is pure data; Benchmark holds the scoring state (reference
solutions, test cases, evaluation harness) and exposes it by
task_id. Keeps adapters composable and keeps Task lightweight
enough that the runner can snapshot it in a run manifest.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol


@dataclass(frozen=True)
class Task:
    """One benchmark task instance, as seen by the runner.

    `query_text` is what gets passed to `run(expr, client,
    query_text, ...)`. Benchmarks are responsible for ensuring
    the query does NOT leak ground truth (hidden test cases,
    canonical solutions, etc.) into the text a macro-model sees
    — that would break the selector-as-oracle discipline at the
    adapter boundary.
    """

    id: str
    query_text: str


@dataclass(frozen=True)
class ScoreResult:
    """Outcome of scoring one response against one task.

    `passed` is the binary pass/fail (most Phase 1 benchmarks
    are binary). `fraction` gives partial credit for benchmarks
    like LiveCodeBench where fractional scoring is natural
    (fraction of declared tests that passed). For binary
    benchmarks, `fraction == 1.0` iff `passed`.

    `detail` is an optional human-readable string explaining the
    outcome (e.g., "AssertionError at test case 3", "execution
    timed out"). Kept in the record for trace inspection and
    capability-failure analysis.
    """

    passed: bool
    fraction: float
    detail: str = ""


class Benchmark(Protocol):
    """Interface every adapter implements.

    Adapters are expected to be constructed once (with whatever
    initialization their source data requires) and then queried
    per task. They should be stateless wrt scoring — calling
    `score(task_id, response)` twice with the same inputs must
    yield the same result.
    """

    name: str

    def tasks(self) -> Iterable[Task]:
        """Yield all tasks in this benchmark's current scope."""
        ...

    def score(self, task_id: str, response: str) -> ScoreResult:
        """Score `response` against the task identified by `task_id`.

        Raises KeyError if `task_id` is not in this benchmark.
        """
        ...
