"""BFCL (Berkeley Function Call Leaderboard) adapter.

Phase 1 commits to BFCL for the "tool use / function calling"
bucket. This adapter supports the `simple_python` category only
— one tool, one invocation, AST-matched against BFCL's
`possible_answer` set. Other categories (multiple / parallel /
live_*) are future work; the adapter structure is set up so
they can land as additional scorer functions without
disturbing the protocol.

**Data source.** The BFCL data is not vendored into the repo;
run `scripts/download_bfcl.py` once to fetch the category
files into `data/bfcl/`. The official `bfcl-eval` PyPI package
pins `numpy==1.26.4`, which has no Python 3.13 wheel — vendoring
the small data files avoids that dependency without pulling in
the full evaluator toolchain.

**Scorer.** Ported from `bfcl_eval.eval_checker.ast_eval.ast_checker`
in the Gorilla repo, specifically `simple_function_checker` and
its string / list / dict sub-checkers. Behavioural invariants:

- Function name must match exactly.
- Required parameters must all be supplied.
- Every model-supplied parameter must be declared by the tool
  schema AND appear in the ground-truth answer for that task.
- Values are matched against the accepted list with
  type-specific semantics: strings are compared after
  normalisation (strip ` ,./-_*^`, lowercase, single→double
  quotes), lists element-wise with the same normalisation,
  dicts key-wise with `""` in the accepted list signalling
  "absent is OK". Numeric values use plain equality; int is
  auto-promoted to float when the declared type is float.
- Missing parameters that the ground truth lists must have
  `""` in their accepted-values list — the BFCL convention
  for "omitting this argument is acceptable."

This matches the upstream checker for simple_python; it does
not attempt to replicate the `is_variable` edge case (where a
model returns a symbolic reference like `"x"` rather than a
value), which is rare for models explicitly instructed to
emit concrete-value JSON.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from .base import ScoreResult, Task


# ============================================================================
# Query formatting
# ============================================================================


_QUERY_TEMPLATE = (
    "You have access to exactly one tool. To invoke it, respond with a "
    "single JSON object of the form "
    '`{{"name": "<tool_name>", "arguments": {{"<arg>": <value>, ...}}}}` '
    "inside one ```json fenced code block. Do not include any prose "
    "outside the block.\n\n"
    "Tool specification:\n"
    "```json\n{tool_json}\n```\n\n"
    "User request:\n{user_prompt}"
)


# ============================================================================
# Response parsing
# ============================================================================


_FENCED_JSON_RE = re.compile(
    r"```(?:json|javascript|python)?\s*\n?(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


def _extract_function_call(response: str) -> dict[str, Any] | None:
    """Extract a `{"name": str, "arguments": dict}` object from a
    response. Returns None on any parse / shape failure — the
    caller records this as a capability failure.

    Accepts three shapes, in order: fenced JSON block, bare JSON
    object, OpenAI-style with `arguments` as a JSON-encoded
    string.
    """
    candidates: list[str] = []
    for match in _FENCED_JSON_RE.finditer(response):
        candidates.append(match.group(1).strip())
    candidates.append(response.strip())

    for cand in candidates:
        try:
            obj = json.loads(cand)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        name = obj.get("name")
        args = obj.get("arguments")
        if not isinstance(name, str):
            continue
        # OpenAI tool-use shape puts `arguments` as a serialised
        # JSON string. Unwrap if so.
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except (json.JSONDecodeError, ValueError):
                continue
        if not isinstance(args, dict):
            continue
        return {"name": name, "arguments": args}
    return None


# ============================================================================
# AST checker (ported from Gorilla's simple_function_checker)
# ============================================================================


_PYTHON_TYPE_MAPPING: dict[str, type] = {
    "string": str,
    "integer": int,
    "float": float,
    "boolean": bool,
    "array": list,
    "tuple": list,
    "dict": dict,
    "any": str,
}

_NESTED_TYPES = {"array", "tuple"}

_NORMALIZE_RE = re.compile(r"[ ,./\-_*^]")


def _normalize_string(s: str) -> str:
    """Strip `[ ,./-_*^]`, lowercase, single→double quotes. Mirrors
    `bfcl_eval.ast_eval.ast_checker.standardize_string` so the
    string / list / dict comparisons match upstream semantics."""
    return _NORMALIZE_RE.sub("", s).lower().replace("'", '"')


def _strict_type_match(value: Any, expected: type) -> bool:
    """Upstream BFCL uses `type(value) == expected`, not
    `isinstance`. The distinction matters for bool/int: in
    Python `isinstance(True, int)` is True, but BFCL treats a
    bool-valued arg as the wrong type for an int-declared
    parameter (and vice versa). Replicate the strict check."""
    return type(value) is expected


def _value_matches_scalar(value: Any, accepted: list[Any]) -> bool:
    """Plain `in` with bool/int distinguished. `True in [1]` is
    True in Python (bool is an int), but BFCL's evaluator treats
    them as distinct, so we filter by matching type first."""
    for a in accepted:
        if type(a) is type(value) and a == value:
            return True
    return False


def _value_matches_string(value: str, accepted: list[Any]) -> bool:
    norm = _normalize_string(value)
    for a in accepted:
        if isinstance(a, str) and _normalize_string(a) == norm:
            return True
    return False


def _value_matches_list(
    value: list[Any], accepted: list[Any], nested_is_string: bool,
) -> bool:
    normalized = list(value)
    if nested_is_string:
        normalized = [
            _normalize_string(v) if isinstance(v, str) else v
            for v in normalized
        ]
    for candidate in accepted:
        if not isinstance(candidate, list):
            continue
        if len(candidate) != len(normalized):
            continue
        normalized_candidate = [
            _normalize_string(x) if isinstance(x, str) else x
            for x in candidate
        ]
        if normalized == normalized_candidate:
            return True
    return False


def _value_matches_dict(value: dict[str, Any], accepted: list[Any]) -> bool:
    for candidate in accepted:
        if not isinstance(candidate, dict):
            continue  # skips "" sentinel + malformed entries
        ok = True
        for k, v in value.items():
            if k not in candidate:
                ok = False
                break
            accepted_vals = candidate[k]
            if isinstance(v, str):
                norm_v = _normalize_string(v)
                norm_accepted = [
                    _normalize_string(x) if isinstance(x, str) else x
                    for x in accepted_vals
                ]
                if norm_v not in norm_accepted:
                    ok = False
                    break
            else:
                if not _value_matches_scalar(v, accepted_vals):
                    ok = False
                    break
        if not ok:
            continue
        for k, accepted_vals in candidate.items():
            if k not in value and "" not in accepted_vals:
                ok = False
                break
        if ok:
            return True
    return False


def _check_simple_call(
    tool_schema: dict[str, Any],
    model_call: dict[str, Any],
    ground_truth_item: dict[str, Any],
) -> ScoreResult:
    """Score one call (`{"name": ..., "arguments": ...}`) against
    one BFCL ground-truth entry (`{fn_name: {param: [values]}}`)."""
    properties = tool_schema["parameters"]["properties"]
    required_params = tool_schema["parameters"].get("required", [])

    gt_fn_name = next(iter(ground_truth_item.keys()))
    gt_params: dict[str, list[Any]] = ground_truth_item[gt_fn_name]

    if model_call["name"] != gt_fn_name:
        return ScoreResult(
            passed=False, fraction=0.0,
            detail=(
                f"wrong function name: expected {gt_fn_name!r}, "
                f"got {model_call['name']!r}"
            ),
        )

    model_args = model_call["arguments"]
    for p in required_params:
        if p not in model_args:
            return ScoreResult(
                passed=False, fraction=0.0,
                detail=f"missing required parameter {p!r}",
            )

    for p, value in model_args.items():
        if p not in properties or p not in gt_params:
            return ScoreResult(
                passed=False, fraction=0.0,
                detail=f"unexpected parameter {p!r}",
            )
        schema = properties[p]
        declared_type = schema.get("type", "any")
        expected_type = _PYTHON_TYPE_MAPPING.get(declared_type, str)

        if declared_type == "float" and type(value) is int:
            value = float(value)
        if declared_type == "tuple" and isinstance(value, tuple):
            value = list(value)

        if not _strict_type_match(value, expected_type):
            return ScoreResult(
                passed=False, fraction=0.0,
                detail=(
                    f"param {p!r}: expected {declared_type}, got "
                    f"{type(value).__name__} ({value!r})"
                ),
            )

        accepted = gt_params[p]
        ok: bool
        if expected_type is str:
            ok = _value_matches_string(value, accepted)
        elif expected_type is list:
            nested = declared_type in _NESTED_TYPES and schema.get("items", {}).get("type") == "string"
            ok = _value_matches_list(value, accepted, nested_is_string=nested)
        elif expected_type is dict:
            ok = _value_matches_dict(value, accepted)
        else:
            ok = _value_matches_scalar(value, accepted)

        if not ok:
            return ScoreResult(
                passed=False, fraction=0.0,
                detail=f"param {p!r}: value {value!r} not in accepted {accepted!r}",
            )

    for p, accepted in gt_params.items():
        if p not in model_args and "" not in accepted:
            return ScoreResult(
                passed=False, fraction=0.0,
                detail=f"missing parameter {p!r} (ground truth lists no empty-default)",
            )

    return ScoreResult(passed=True, fraction=1.0, detail="ok")


# ============================================================================
# Benchmark
# ============================================================================


class BFCLBench:
    """BFCL `simple_python` category as a `Benchmark`.

    Construct with paths to two JSONL files (questions and
    `possible_answer`). Fetch them once via
    `scripts/download_bfcl.py` into `data/bfcl/`.

    `task_ids` filters to a subset; KeyError if any named id is
    absent from the loaded file.
    """

    name: str = "bfcl_simple_python"

    def __init__(
        self,
        questions_path: Path,
        answers_path: Path,
        task_ids: Iterable[str] | None = None,
    ) -> None:
        questions = self._load_jsonl(questions_path)
        answers = self._load_jsonl(answers_path)

        self._questions: dict[str, dict[str, Any]] = {q["id"]: q for q in questions}
        self._answers: dict[str, dict[str, Any]] = {a["id"]: a for a in answers}

        missing = set(self._questions) - set(self._answers)
        if missing:
            raise ValueError(
                f"{len(missing)} question(s) have no possible_answer entry "
                f"(e.g. {sorted(missing)[:3]})"
            )

        if task_ids is not None:
            wanted = list(task_ids)
            bad = [t for t in wanted if t not in self._questions]
            if bad:
                raise KeyError(
                    f"BFCL has no questions for task_ids={bad!r}"
                )
            self._questions = {t: self._questions[t] for t in wanted}

    @staticmethod
    def _load_jsonl(path: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    def tasks(self) -> Iterable[Task]:
        for task_id, q in self._questions.items():
            tool = q["function"][0]
            user_msg = _first_user_message(q["question"])
            query_text = _QUERY_TEMPLATE.format(
                tool_json=json.dumps(tool, indent=2),
                user_prompt=user_msg,
            )
            yield Task(id=task_id, query_text=query_text)

    def score(self, task_id: str, response: str) -> ScoreResult:
        if task_id not in self._questions:
            raise KeyError(f"task_id {task_id!r} not in this BFCLBench")

        q = self._questions[task_id]
        a = self._answers[task_id]
        tool_schema = q["function"][0]
        ground_truth_items: list[dict[str, Any]] = a["ground_truth"]
        # simple_python always has exactly one ground-truth call.
        ground_truth_item = ground_truth_items[0]

        call = _extract_function_call(response)
        if call is None:
            return ScoreResult(
                passed=False, fraction=0.0,
                detail="failed to extract JSON function call from response",
            )

        return _check_simple_call(tool_schema, call, ground_truth_item)


def _first_user_message(question_field: list[list[dict[str, str]]]) -> str:
    """BFCL's `question` field is a nested list: outer list for
    conversation turns (single-turn = 1 element), inner list for
    messages within a turn. simple_python is always single-turn
    single-user-message; we extract defensively."""
    for turn in question_field:
        for msg in turn:
            if msg.get("role") == "user":
                return str(msg.get("content", ""))
    return ""
