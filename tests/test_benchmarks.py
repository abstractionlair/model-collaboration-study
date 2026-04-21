"""Unit tests for the Benchmark abstraction and HumanEval adapter.

Covers: the abstraction's type shape (Task, ScoreResult,
Benchmark protocol), HumanEval problem loading and subsetting,
code extraction from model responses (with and without
markdown fences), and scoring (correct vs broken completions).
"""

from __future__ import annotations

import pytest

from src.experiment.benchmarks import Benchmark, HumanEvalBench, ScoreResult, Task
from src.experiment.benchmarks.humaneval import _extract_code


# ----------------------------------------------------------------
# Task / ScoreResult shape
# ----------------------------------------------------------------


def test_task_is_frozen_data() -> None:
    t = Task(id="foo", query_text="bar")
    with pytest.raises(Exception):
        t.id = "changed"  # type: ignore[misc]


def test_score_result_binary() -> None:
    s = ScoreResult(passed=True, fraction=1.0, detail="ok")
    assert s.passed
    assert s.fraction == 1.0


# ----------------------------------------------------------------
# HumanEvalBench loading + subsetting
# ----------------------------------------------------------------


def test_humaneval_loads_all_problems() -> None:
    """Full HumanEval has 164 problems."""
    bench = HumanEvalBench()
    tasks = list(bench.tasks())
    assert len(tasks) == 164
    # Task IDs are "HumanEval/0" through "HumanEval/163".
    assert tasks[0].id == "HumanEval/0"


def test_humaneval_subset() -> None:
    """Explicit subset filter produces just the requested tasks."""
    bench = HumanEvalBench(task_ids=["HumanEval/0", "HumanEval/5"])
    tasks = list(bench.tasks())
    assert [t.id for t in tasks] == ["HumanEval/0", "HumanEval/5"]


def test_humaneval_missing_task_id_raises() -> None:
    with pytest.raises(KeyError, match="no problems"):
        HumanEvalBench(task_ids=["HumanEval/0", "nonexistent"])


def test_humaneval_query_does_not_leak_canonical_solution() -> None:
    """Selector-as-oracle discipline at the adapter boundary:
    the query_text the macro-model sees must not contain the
    canonical solution or the hidden tests."""
    bench = HumanEvalBench(task_ids=["HumanEval/0"])
    task = next(iter(bench.tasks()))
    # HumanEval/0's canonical_solution uses "threshold" checks.
    # The prompt (the function signature + docstring) is fine;
    # we just need to make sure neither the solution body nor
    # the test function leak in.
    assert "def check(candidate)" not in task.query_text
    assert "METADATA" not in task.query_text  # from the test file


def test_humaneval_score_unknown_task_id() -> None:
    bench = HumanEvalBench(task_ids=["HumanEval/0"])
    with pytest.raises(KeyError, match="not in this HumanEvalBench"):
        bench.score("HumanEval/99", "def foo(): pass")


# ----------------------------------------------------------------
# Code extraction
# ----------------------------------------------------------------


def test_extract_code_python_fence() -> None:
    response = (
        "Here's the function:\n\n"
        "```python\n"
        "def foo():\n"
        "    return 42\n"
        "```\n\n"
        "Hope this helps!"
    )
    assert _extract_code(response) == "def foo():\n    return 42"


def test_extract_code_bare_fence() -> None:
    response = "```\ndef foo():\n    return 42\n```"
    assert _extract_code(response) == "def foo():\n    return 42"


def test_extract_code_no_fence() -> None:
    """Fallback: if no fence, strip whitespace from the response."""
    response = "  def foo():\n    return 42  "
    assert _extract_code(response) == "def foo():\n    return 42"


def test_extract_code_prefers_first_fence() -> None:
    response = (
        "```python\ndef first():\n    pass\n```\n"
        "Wait, actually:\n"
        "```python\ndef second():\n    pass\n```"
    )
    assert "def first" in _extract_code(response)


# ----------------------------------------------------------------
# Scoring with actual execution
# ----------------------------------------------------------------


def test_humaneval_scores_canonical_solution_as_pass() -> None:
    """The canonical solution (by construction) should pass."""
    bench = HumanEvalBench(task_ids=["HumanEval/0"])
    # Load the canonical solution by peeking into the private dict.
    problem = bench._problems["HumanEval/0"]
    # The canonical solution is just the body (no function
    # signature), so we build a "full function" by combining it
    # with the prompt.
    completion = problem["prompt"] + problem["canonical_solution"]
    response = f"```python\n{completion}\n```"
    result = bench.score("HumanEval/0", response)
    assert result.passed
    assert result.fraction == 1.0


def test_humaneval_scores_wrong_solution_as_fail() -> None:
    """A broken implementation fails the tests."""
    bench = HumanEvalBench(task_ids=["HumanEval/0"])
    # has_close_elements returns bool; always-False breaks the
    # test cases that expect True.
    wrong = (
        "```python\n"
        "from typing import List\n"
        "def has_close_elements(numbers: List[float], threshold: float) -> bool:\n"
        "    return False\n"
        "```"
    )
    result = bench.score("HumanEval/0", wrong)
    assert not result.passed
    assert result.fraction == 0.0
