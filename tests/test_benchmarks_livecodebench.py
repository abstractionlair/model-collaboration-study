"""Unit tests for the LiveCodeBench adapter.

Uses hand-authored in-test datasets (JSONL in a tmp_path) so the
tests don't depend on `scripts/download_livecodebench.py` having
been run. The tests exercise real `python3` subprocess execution
against small programs -- no model output is mocked; we assemble
the 'response' directly and verify the scorer reacts correctly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.experiment.benchmarks import LiveCodeBenchBench, ScoreResult
from src.experiment.benchmarks.livecodebench import (
    _extract_code,
    _normalize_output,
    _outputs_match,
)


# ============================================================================
# Helpers
# ============================================================================


def _record(
    question_id: str,
    *,
    content: str = "Read an integer and print its square.",
    difficulty: str = "easy",
    platform: str = "atcoder",
    public_tests: list[dict[str, Any]] | None = None,
    private_tests: list[dict[str, Any]] | None = None,
    starter_code: str = "",
) -> dict[str, Any]:
    """Build a sanitised-LCB record matching the fetcher's output
    schema."""
    return {
        "question_id": question_id,
        "question_title": question_id,
        "question_content": content,
        "platform": platform,
        "contest_id": "test_contest",
        "contest_date": "2025-01-01T00:00:00",
        "difficulty": difficulty,
        "starter_code": starter_code,
        "public_tests": public_tests or [
            {"input": "2", "output": "4", "testtype": "stdin"},
        ],
        "private_tests": private_tests or [
            {"input": "3", "output": "9", "testtype": "stdin"},
            {"input": "5", "output": "25", "testtype": "stdin"},
        ],
        "metadata": "{}",
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def _wrap(code: str) -> str:
    """Wrap source in a fenced Python block, the format the prompt asks for."""
    return f"```python\n{code}\n```"


_SQUARE_OK = "n = int(input())\nprint(n * n)\n"
_SQUARE_WRONG_ANSWER = "n = int(input())\nprint(n + n)\n"
_SQUARE_RUNTIME_ERROR = "n = int(input())\nraise RuntimeError('boom')\n"
_SQUARE_TIMEOUT = "import time\nn = int(input())\nwhile True:\n    time.sleep(1)\n"


# ============================================================================
# Output normalisation
# ============================================================================


def test_normalize_strips_trailing_whitespace() -> None:
    assert _normalize_output("hello\n") == "hello"
    assert _normalize_output("hello  \n") == "hello"
    assert _normalize_output("hello\n\n\n") == "hello"


def test_normalize_preserves_internal_blank_lines() -> None:
    assert _normalize_output("a\n\nb\n") == "a\n\nb"


def test_normalize_handles_crlf() -> None:
    assert _normalize_output("hello\r\nworld\r\n") == "hello\nworld"


def test_outputs_match_tolerates_trailing_newlines() -> None:
    assert _outputs_match("42\n", "42")
    assert _outputs_match("42", "42\n")
    assert _outputs_match("42\n\n", "42\n")


def test_outputs_match_rejects_structural_diff() -> None:
    assert not _outputs_match("42 ", "4 2")
    assert not _outputs_match("42", "43")
    assert not _outputs_match("1\n2", "2\n1")


# ============================================================================
# Code extraction
# ============================================================================


def test_extract_code_fenced_python() -> None:
    r = "Here's my solution:\n```python\nprint(1)\n```\nDone."
    assert _extract_code(r) == "print(1)"


def test_extract_code_fenced_lowercase_py() -> None:
    r = "```py\nprint(1)\n```"
    assert _extract_code(r) == "print(1)"


def test_extract_code_no_fence_falls_back() -> None:
    r = "print(1)\n"
    assert _extract_code(r) == "print(1)"


def test_extract_code_prefers_first_fence() -> None:
    r = "```python\nprint(1)\n```\nversus\n```python\nprint(2)\n```"
    assert _extract_code(r) == "print(1)"


# ============================================================================
# End-to-end scoring
# ============================================================================


def test_score_all_private_tests_pass(tmp_path: Path) -> None:
    path = tmp_path / "lcb.jsonl"
    _write_jsonl(path, [_record("q1")])
    bench = LiveCodeBenchBench(path, execution_timeout=5.0)

    result = bench.score("q1", _wrap(_SQUARE_OK))
    assert isinstance(result, ScoreResult)
    assert result.passed is True
    assert result.fraction == 1.0
    assert "all private tests passed" in result.detail


def test_score_all_private_tests_fail(tmp_path: Path) -> None:
    path = tmp_path / "lcb.jsonl"
    _write_jsonl(path, [_record("q1")])
    bench = LiveCodeBenchBench(path, execution_timeout=5.0)

    result = bench.score("q1", _wrap(_SQUARE_WRONG_ANSWER))
    assert result.passed is False
    assert result.fraction == 0.0
    assert "wrong_output" in result.detail


def test_score_fractional_partial_pass(tmp_path: Path) -> None:
    # Two private tests: first passes for n=2 (4 is square and 2+2), second fails.
    path = tmp_path / "lcb.jsonl"
    rec = _record(
        "q1",
        private_tests=[
            {"input": "2", "output": "4", "testtype": "stdin"},   # n+n==n*n ok
            {"input": "3", "output": "9", "testtype": "stdin"},   # differs
        ],
    )
    _write_jsonl(path, [rec])
    bench = LiveCodeBenchBench(path, execution_timeout=5.0)

    result = bench.score("q1", _wrap(_SQUARE_WRONG_ANSWER))
    assert result.passed is False
    assert result.fraction == pytest.approx(0.5)
    assert "1/2 passed" in result.detail


def test_score_handles_runtime_error(tmp_path: Path) -> None:
    path = tmp_path / "lcb.jsonl"
    _write_jsonl(path, [_record("q1")])
    bench = LiveCodeBenchBench(path, execution_timeout=5.0)

    result = bench.score("q1", _wrap(_SQUARE_RUNTIME_ERROR))
    assert result.passed is False
    assert result.fraction == 0.0
    assert "runtime_error" in result.detail


def test_score_handles_timeout(tmp_path: Path) -> None:
    path = tmp_path / "lcb.jsonl"
    _write_jsonl(path, [_record("q1")])
    bench = LiveCodeBenchBench(path, execution_timeout=0.5)

    result = bench.score("q1", _wrap(_SQUARE_TIMEOUT))
    assert result.passed is False
    assert result.fraction == 0.0
    assert "timeout" in result.detail


def test_score_no_code_extracted(tmp_path: Path) -> None:
    path = tmp_path / "lcb.jsonl"
    _write_jsonl(path, [_record("q1")])
    bench = LiveCodeBenchBench(path, execution_timeout=5.0)

    result = bench.score("q1", "")
    assert result.passed is False
    assert result.fraction == 0.0
    assert "no code extracted" in result.detail


# ============================================================================
# Task iteration + filtering
# ============================================================================


def test_tasks_yields_all_ids(tmp_path: Path) -> None:
    path = tmp_path / "lcb.jsonl"
    _write_jsonl(path, [
        _record("q1"), _record("q2"), _record("q3"),
    ])
    bench = LiveCodeBenchBench(path)
    ids = sorted(t.id for t in bench.tasks())
    assert ids == ["q1", "q2", "q3"]


def test_task_query_contains_problem_and_examples(tmp_path: Path) -> None:
    path = tmp_path / "lcb.jsonl"
    rec = _record(
        "q1",
        content="Compute n squared.",
        public_tests=[{"input": "7", "output": "49", "testtype": "stdin"}],
    )
    _write_jsonl(path, [rec])
    bench = LiveCodeBenchBench(path)
    task = next(iter(bench.tasks()))
    assert "Compute n squared." in task.query_text
    assert "Input:\n7" in task.query_text
    assert "Expected output:\n49" in task.query_text


def test_task_query_does_not_leak_private_tests(tmp_path: Path) -> None:
    """The solver must never see private test inputs/outputs."""
    path = tmp_path / "lcb.jsonl"
    rec = _record(
        "q1",
        public_tests=[{"input": "PUBLIC_IN", "output": "PUBLIC_OUT", "testtype": "stdin"}],
        private_tests=[{"input": "SECRET_IN", "output": "SECRET_OUT", "testtype": "stdin"}],
    )
    _write_jsonl(path, [rec])
    bench = LiveCodeBenchBench(path)
    task = next(iter(bench.tasks()))
    assert "PUBLIC_IN" in task.query_text
    assert "PUBLIC_OUT" in task.query_text
    assert "SECRET_IN" not in task.query_text
    assert "SECRET_OUT" not in task.query_text


def test_task_ids_filter(tmp_path: Path) -> None:
    path = tmp_path / "lcb.jsonl"
    _write_jsonl(path, [_record("q1"), _record("q2"), _record("q3")])
    bench = LiveCodeBenchBench(path, task_ids=["q1", "q3"])
    ids = sorted(t.id for t in bench.tasks())
    assert ids == ["q1", "q3"]


def test_task_ids_filter_missing_raises(tmp_path: Path) -> None:
    path = tmp_path / "lcb.jsonl"
    _write_jsonl(path, [_record("q1")])
    with pytest.raises(KeyError, match="missing or not stdin-type"):
        LiveCodeBenchBench(path, task_ids=["q1", "nope"])


def test_difficulty_filter(tmp_path: Path) -> None:
    path = tmp_path / "lcb.jsonl"
    _write_jsonl(path, [
        _record("q1", difficulty="easy"),
        _record("q2", difficulty="medium"),
        _record("q3", difficulty="hard"),
    ])
    bench = LiveCodeBenchBench(path, difficulties=["easy", "hard"])
    ids = sorted(t.id for t in bench.tasks())
    assert ids == ["q1", "q3"]


def test_functional_records_are_skipped(tmp_path: Path) -> None:
    """Functional-type tests are filtered out in v1 of the adapter."""
    path = tmp_path / "lcb.jsonl"
    _write_jsonl(path, [
        _record("stdin_q"),
        _record(
            "functional_q",
            platform="leetcode",
            public_tests=[{"input": "2", "output": "4", "testtype": "functional"}],
            private_tests=[{"input": "3", "output": "9", "testtype": "functional"}],
        ),
        _record(
            "mixed_q",
            public_tests=[{"input": "2", "output": "4", "testtype": "stdin"}],
            private_tests=[{"input": "3", "output": "9", "testtype": "functional"}],
        ),
    ])
    bench = LiveCodeBenchBench(path)
    ids = sorted(t.id for t in bench.tasks())
    assert ids == ["stdin_q"]


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="download_livecodebench.py"):
        LiveCodeBenchBench(tmp_path / "nonexistent.jsonl")


def test_score_unknown_task_id_raises(tmp_path: Path) -> None:
    path = tmp_path / "lcb.jsonl"
    _write_jsonl(path, [_record("q1")])
    bench = LiveCodeBenchBench(path)
    with pytest.raises(KeyError, match="not in this LiveCodeBenchBench"):
        bench.score("q_nope", _wrap("print(1)"))
