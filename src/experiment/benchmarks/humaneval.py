"""HumanEval adapter.

Framework-validation benchmark. **Not part of the Phase 1
matrix** (SWE-bench Verified / LiveCodeBench / BFCL are the
Phase 1 commitments); HumanEval is heavily contaminated in
training data, which makes it useless for capability
measurement but *useful* for framework validation because
near-ceiling pass rates on single-model runs mean the pipeline
works, and a pass-rate collapse signals a real pipeline bug.

Source: https://github.com/openai/human-eval (via `pip install
human-eval`). Each problem is a function prompt + hidden test
cases; scoring executes the tests in a sandboxed subprocess
via `human_eval.execution.check_correctness`.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

import human_eval.data as he_data  # type: ignore[import-untyped]
import human_eval.execution as he_exec  # type: ignore[import-untyped]

from .base import Benchmark, ScoreResult, Task


# Prompt template wrapping the HumanEval function stub. We ask
# for a fenced Python block so extraction is deterministic.
_QUERY_TEMPLATE = (
    "Complete the following Python function. Return the full "
    "function (signature + body) inside a single ```python code "
    "block. Do not include any other prose.\n\n"
    "{prompt}"
)


_CODE_BLOCK_RE = re.compile(
    r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE,
)


def _extract_code(response: str) -> str:
    """Extract Python code from a model response.

    Prefer the first fenced code block (``` or ```python). If
    no fence is present, return the response stripped of
    surrounding whitespace — some models skip the fence but the
    code is still executable.
    """
    match = _CODE_BLOCK_RE.search(response)
    if match is not None:
        return match.group(1).strip()
    return response.strip()


class HumanEvalBench:
    """HumanEval as a `Benchmark`.

    Construct with an optional `task_ids` filter to use a subset
    (typical: 10-20 problems for a framework-validation run).
    Omit to use all 164.

    `execution_timeout` bounds per-test wallclock. Default 5
    seconds matches the official harness.
    """

    name: str = "humaneval"

    def __init__(
        self,
        task_ids: Iterable[str] | None = None,
        execution_timeout: float = 5.0,
    ) -> None:
        all_problems: dict[str, dict[str, Any]] = he_data.read_problems()
        if task_ids is not None:
            wanted = list(task_ids)
            missing = [t for t in wanted if t not in all_problems]
            if missing:
                raise KeyError(
                    f"HumanEval has no problems for task_ids={missing!r}"
                )
            self._problems: dict[str, dict[str, Any]] = {
                t: all_problems[t] for t in wanted
            }
        else:
            self._problems = all_problems
        self._timeout = execution_timeout

    def tasks(self) -> Iterable[Task]:
        for task_id, problem in self._problems.items():
            yield Task(
                id=task_id,
                query_text=_QUERY_TEMPLATE.format(prompt=problem["prompt"]),
            )

    def score(self, task_id: str, response: str) -> ScoreResult:
        if task_id not in self._problems:
            raise KeyError(f"task_id {task_id!r} not in this HumanEvalBench")
        problem = self._problems[task_id]
        completion = _extract_code(response)
        # `check_correctness` runs `problem["prompt"] + completion`
        # in a sandboxed subprocess, then runs the hidden tests.
        # If the model's completion also contains the function
        # signature (which models usually do when returning a
        # full function block), the second definition overrides
        # the first — still correct.
        result = he_exec.check_correctness(
            problem, completion, timeout=self._timeout,
        )
        passed = bool(result.get("passed"))
        detail = str(result.get("result", ""))
        return ScoreResult(
            passed=passed,
            fraction=1.0 if passed else 0.0,
            detail=detail,
        )
