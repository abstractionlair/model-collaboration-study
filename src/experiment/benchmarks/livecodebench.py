"""LiveCodeBench adapter.

Phase 1 commits to LiveCodeBench for the "competitive /
isolated coding" bucket — coding tasks with executable tests
that are designed to resist training-data contamination via
rolling monthly releases.

This adapter supports the **stdin testtype only** — i.e.
competitive-programming problems sourced from AtCoder and
CodeForces where the solver reads from stdin and writes to
stdout. The `functional` testtype used by LeetCode-sourced
problems (which carries a `starter_code` scaffold and wraps
each test as `assert f(input) == output`) is intentionally
filtered out in v1 of this adapter. Recent LCB releases
(release_v5 onwards) are dominated by stdin-type problems;
extending to functional is tracked as follow-on work.

**Data source.** Run `scripts/download_livecodebench.py` once to
fetch a release file from the official HuggingFace dataset at
`livecodebench/code_generation_lite` and rewrite it as a clean
JSON-only form into `data/livecodebench/` (gitignored). The
upstream LCB files encode `private_test_cases` as
`base64(zlib(pickle(json_str)))`; the fetcher does that decode
once at download time (a single trusted moment) and stores the
decoded tests as plain JSON arrays. The runtime adapter never
touches pickle — it only reads JSON produced by the fetcher.

**Schema of the rewritten record** (JSONL, one per task):

- `question_id`, `question_title`, `question_content`: problem
  statement fields.
- `platform`: one of `atcoder`, `codeforces`, `leetcode`.
- `contest_id`, `contest_date`: source identifiers.
- `difficulty`: `easy` | `medium` | `hard` (LCB's labels).
- `starter_code`: non-empty only for functional (LeetCode)
  problems; empty for stdin problems.
- `public_tests`: list of `{input, output, testtype}` dicts;
  visible to the solver.
- `private_tests`: list of `{input, output, testtype}` dicts;
  hidden from the solver. Used for scoring only.

**Scoring.** For each task, run the hidden private tests
serially against the extracted code in a subprocess with a
per-test wallclock timeout. Output comparison is whitespace-
tolerant (rstrip on each line + strip trailing blank lines) to
match the conventions of competitive-programming judges without
being lenient enough to pass wrong answers. Returns a fractional
score in `[0, 1]` equal to `n_passed / n_total_private`. `passed`
is True iff every private test passes.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal

from .base import ScoreResult, Task


# ============================================================================
# Query formatting
# ============================================================================


_QUERY_TEMPLATE_STDIN = (
    "Solve the following competitive-programming problem. Your solution must "
    "read the input from standard input and write the answer to standard "
    "output. Return the complete Python program inside a single "
    "```python code block. Do not include any prose outside the block.\n\n"
    "Problem:\n{problem}\n\n"
    "Examples:\n{examples}"
)


def _format_examples(public_tests: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for i, t in enumerate(public_tests, 1):
        parts.append(
            f"Example {i}:\nInput:\n{t['input']}\nExpected output:\n{t['output']}"
        )
    return "\n\n".join(parts)


# ============================================================================
# Response parsing
# ============================================================================


_CODE_BLOCK_RE = re.compile(
    r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE,
)


def _extract_code(response: str) -> str:
    """Extract Python code from a model response.

    Prefer the first fenced code block. If no fence is found, fall
    back to the stripped response — some models skip the fence but
    the code is still executable.
    """
    match = _CODE_BLOCK_RE.search(response)
    if match is not None:
        return match.group(1).strip()
    return response.strip()


# ============================================================================
# Stdout comparison
# ============================================================================


def _normalize_output(s: str) -> str:
    """Strip trailing whitespace per line and trailing blank lines.

    Matches competitive-programming judge conventions: tolerate
    trailing newlines or platform-specific line endings, but do not
    accept structurally different outputs.
    """
    lines = [line.rstrip() for line in s.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _outputs_match(actual: str, expected: str) -> bool:
    return _normalize_output(actual) == _normalize_output(expected)


# ============================================================================
# Execution
# ============================================================================


ExecStatus = Literal["pass", "wrong_output", "timeout", "runtime_error"]


@dataclass(frozen=True)
class _TestOutcome:
    status: ExecStatus
    detail: str


def _run_one_stdin_test(
    code: str,
    stdin_input: str,
    expected_output: str,
    timeout: float,
) -> _TestOutcome:
    """Run `code` once with stdin_input piped in; compare stdout."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        program_path = f.name
    try:
        proc = subprocess.run(
            ["python3", program_path],
            input=stdin_input,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _TestOutcome("timeout", f"timeout after {timeout}s")
    finally:
        Path(program_path).unlink(missing_ok=True)

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        if len(stderr) > 500:
            stderr = stderr[:500] + "...(truncated)"
        return _TestOutcome("runtime_error", f"exit={proc.returncode}: {stderr}")

    if _outputs_match(proc.stdout, expected_output):
        return _TestOutcome("pass", "")

    exp = _normalize_output(expected_output)
    got = _normalize_output(proc.stdout)
    if len(exp) > 200:
        exp = exp[:200] + "...(truncated)"
    if len(got) > 200:
        got = got[:200] + "...(truncated)"
    return _TestOutcome("wrong_output", f"expected {exp!r}, got {got!r}")


# ============================================================================
# Adapter
# ============================================================================


@dataclass(frozen=True)
class _LcbProblem:
    """The subset of a LiveCodeBench record this adapter uses."""

    question_id: str
    question_content: str
    difficulty: str
    public_tests: list[dict[str, Any]]
    private_tests: list[dict[str, Any]]


def _load_problems(
    jsonl_path: Path,
    task_ids: Iterable[str] | None,
    difficulties: Iterable[str] | None,
) -> dict[str, _LcbProblem]:
    wanted_ids = set(task_ids) if task_ids is not None else None
    wanted_diffs = set(difficulties) if difficulties is not None else None

    out: dict[str, _LcbProblem] = {}

    with jsonl_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            qid: str = rec["question_id"]
            if wanted_ids is not None and qid not in wanted_ids:
                continue
            difficulty: str = rec["difficulty"]
            if wanted_diffs is not None and difficulty not in wanted_diffs:
                continue

            public_tests: list[dict[str, Any]] = rec["public_tests"]
            private_tests: list[dict[str, Any]] = rec["private_tests"]

            # Keep only problems whose tests are all stdin-type.
            all_tests = public_tests + private_tests
            if all_tests and {t["testtype"] for t in all_tests} == {"stdin"}:
                out[qid] = _LcbProblem(
                    question_id=qid,
                    question_content=rec["question_content"],
                    difficulty=difficulty,
                    public_tests=public_tests,
                    private_tests=private_tests,
                )

    if wanted_ids is not None:
        missing = wanted_ids - set(out.keys())
        if missing:
            raise KeyError(
                f"LiveCodeBench record(s) missing or not stdin-type: "
                f"{sorted(missing)!r}"
            )
    return out


class LiveCodeBenchBench:
    """LiveCodeBench as a `Benchmark`.

    `jsonl_path` should point at a rewritten release file produced
    by `scripts/download_livecodebench.py` (e.g. `test6.json`).
    Pass `task_ids` to restrict to a subset (typical: 5-20 problems
    for framework validation), or `difficulties` to slice by LCB's
    easy/medium/hard labels. `execution_timeout` bounds per-test
    wallclock in seconds; LCB's upstream harness does not pin a
    specific default, so we adopt 10 s as a conservative anchor for
    competitive-programming I/O with small inputs.
    """

    name: str = "livecodebench"

    def __init__(
        self,
        jsonl_path: str | Path,
        task_ids: Iterable[str] | None = None,
        difficulties: Iterable[str] | None = None,
        execution_timeout: float = 10.0,
    ) -> None:
        path = Path(jsonl_path)
        if not path.exists():
            raise FileNotFoundError(
                f"LiveCodeBench data file not found at {path}; "
                f"run `scripts/download_livecodebench.py` first."
            )
        self._problems: dict[str, _LcbProblem] = _load_problems(
            path, task_ids, difficulties,
        )
        self._timeout = execution_timeout

    def tasks(self) -> Iterable[Task]:
        for qid, prob in self._problems.items():
            examples = _format_examples(prob.public_tests)
            yield Task(
                id=qid,
                query_text=_QUERY_TEMPLATE_STDIN.format(
                    problem=prob.question_content,
                    examples=examples,
                ),
            )

    def score(self, task_id: str, response: str) -> ScoreResult:
        if task_id not in self._problems:
            raise KeyError(f"task_id {task_id!r} not in this LiveCodeBenchBench")
        prob = self._problems[task_id]
        code = _extract_code(response)
        if not code.strip():
            return ScoreResult(
                passed=False,
                fraction=0.0,
                detail="no code extracted from response",
            )

        n_total = len(prob.private_tests)
        if n_total == 0:
            return ScoreResult(
                passed=False, fraction=0.0, detail="no private tests",
            )

        n_passed = 0
        first_failure: str = ""
        for i, t in enumerate(prob.private_tests):
            outcome = _run_one_stdin_test(
                code, t["input"], t["output"], self._timeout,
            )
            if outcome.status == "pass":
                n_passed += 1
            elif not first_failure:
                first_failure = f"test {i}: {outcome.status}: {outcome.detail}"

        fraction = n_passed / n_total
        detail = (
            "all private tests passed"
            if n_passed == n_total
            else f"{n_passed}/{n_total} passed; first failure: {first_failure}"
        )
        return ScoreResult(
            passed=(n_passed == n_total),
            fraction=fraction,
            detail=detail,
        )
