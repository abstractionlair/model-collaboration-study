"""BFCL (Berkeley Function Call Leaderboard) adapter.

Phase 1 commits to BFCL for the "tool use / function calling"
bucket. This adapter supports five BFCL categories:

- `simple_python` — one tool, one invocation (v1 scope).
- `multiple` — N candidate tools, one invocation; model picks
  the right tool.
- `parallel` — one tool, N invocations in one response.
- `parallel_multiple` — N tools, M invocations combining them.
- `live_simple` — real-user one-tool one-invocation queries
  (same shape as `simple_python`, different data distribution).

Scoring is ported from Gorilla's
`bfcl_eval.eval_checker.ast_eval.ast_checker`, covering
`simple_function_checker` (reused across single-call categories),
`parallel_function_checker_no_order` (used for `parallel` and
`parallel_multiple`), and `multiple_function_checker` (which is
just `simple_function_checker` against the tool chosen from the
candidate list by GT function name).

**Data source.** Run `scripts/download_bfcl.py` once to fetch
the data files into `data/bfcl/`. The official `bfcl-eval` PyPI
package pins `numpy==1.26.4`, which has no Python 3.13 wheel —
vendoring the small data files avoids that dependency.

**Scoring invariants (from `simple_function_checker`).**

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

**Parallel-category semantics.** Per-call matching is
order-independent: for each ground-truth call, the scorer
finds any unmatched model call that passes
`simple_function_checker` and marks it consumed. Equivalent to
upstream's `parallel_function_checker_no_order`. Exact-count
required (`len(model_calls) == len(gt_items)`).

**Deliberate deviations from upstream.** Two edge cases where
this port is narrower than `bfcl_eval`:

1. **Exact function-name match, no dot/underscore normalisation.**
   Upstream's `convert_func_name` replaces `.` with `_` for
   model families whose native tool-calling API forbids dots
   in tool names (OpenAI, Mistral, Google). We don't use
   native tool-calling — the model sees the tool schema in
   prompted JSON and is asked to emit the exact declared
   name. If a model emits `math_gcd` for a declared
   `math.gcd`, we reject where upstream would accept via
   `underscore_to_dot`.

2. **`is_variable` branch skipped.** Upstream accepts values
   whose Python type doesn't match the declared schema type
   but does match the type of a non-empty entry in the
   accepted list. We enforce the schema strictly. Rare; not a
   live failure mode for prompted-JSON output.
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


_QUERY_TEMPLATE_SIMPLE = (
    "You have access to exactly one tool. To invoke it, respond with a "
    "single JSON object of the form "
    '`{{"name": "<tool_name>", "arguments": {{"<arg>": <value>, ...}}}}` '
    "inside one ```json fenced code block. Do not include any prose "
    "outside the block.\n\n"
    "Tool specification:\n"
    "```json\n{tool_json}\n```\n\n"
    "User request:\n{user_prompt}"
)

_QUERY_TEMPLATE_MULTIPLE = (
    "You have access to the tools listed below. Choose exactly ONE tool "
    "that best satisfies the user request, and invoke it by responding "
    "with a single JSON object of the form "
    '`{{"name": "<tool_name>", "arguments": {{"<arg>": <value>, ...}}}}` '
    "inside one ```json fenced code block. Do not include any prose "
    "outside the block.\n\n"
    "Available tools:\n"
    "```json\n{tool_json}\n```\n\n"
    "User request:\n{user_prompt}"
)

_QUERY_TEMPLATE_PARALLEL = (
    "You have access to exactly one tool. The user request may require "
    "calling it more than once. Respond with a JSON array of one or more "
    'objects, each of the form `{{"name": "<tool_name>", "arguments": '
    '{{"<arg>": <value>, ...}}}}`, one per invocation, inside one ```json '
    "fenced code block. Do not include any prose outside the block.\n\n"
    "Tool specification:\n"
    "```json\n{tool_json}\n```\n\n"
    "User request:\n{user_prompt}"
)

_QUERY_TEMPLATE_PARALLEL_MULTIPLE = (
    "You have access to the tools listed below. The user request may "
    "require calling one or more of them, possibly multiple times. "
    "Respond with a JSON array of one or more objects, each of the form "
    '`{{"name": "<tool_name>", "arguments": {{"<arg>": <value>, ...}}}}`, '
    "one per invocation, inside one ```json fenced code block. Do not "
    "include any prose outside the block.\n\n"
    "Available tools:\n"
    "```json\n{tool_json}\n```\n\n"
    "User request:\n{user_prompt}"
)

_SUPPORTED_CATEGORIES: frozenset[str] = frozenset({
    "simple_python",
    "multiple",
    "parallel",
    "parallel_multiple",
    "live_simple",
})

_SINGLE_CALL_CATEGORIES: frozenset[str] = frozenset({
    "simple_python", "multiple", "live_simple",
})


def _query_template(category: str) -> str:
    if category in ("simple_python", "live_simple"):
        return _QUERY_TEMPLATE_SIMPLE
    if category == "multiple":
        return _QUERY_TEMPLATE_MULTIPLE
    if category == "parallel":
        return _QUERY_TEMPLATE_PARALLEL
    if category == "parallel_multiple":
        return _QUERY_TEMPLATE_PARALLEL_MULTIPLE
    raise ValueError(f"unknown BFCL category {category!r}")


# ============================================================================
# Response parsing
# ============================================================================


_FENCED_JSON_RE = re.compile(
    r"```(?:json|javascript|python)?\s*\n?(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


def _coerce_call(obj: Any) -> dict[str, Any] | None:
    """Validate and normalise a single `{name, arguments}` dict.
    Returns the canonicalised call on success, None on shape
    failure. Handles OpenAI-style `arguments` as a JSON-encoded
    string."""
    if not isinstance(obj, dict):
        return None
    name = obj.get("name")
    args = obj.get("arguments")
    if not isinstance(name, str):
        return None
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (json.JSONDecodeError, ValueError):
            return None
    if not isinstance(args, dict):
        return None
    return {"name": name, "arguments": args}


def _extract_function_call(response: str) -> dict[str, Any] | None:
    """Extract a single `{"name": str, "arguments": dict}` call
    from a response. Returns None on any parse / shape failure —
    the caller records this as a capability failure.

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
        call = _coerce_call(obj)
        if call is not None:
            return call
    return None


def _extract_function_calls(response: str) -> list[dict[str, Any]] | None:
    """Extract a LIST of `{name, arguments}` calls for
    parallel / parallel_multiple categories. The response is
    expected to contain a JSON array of call objects; a single
    object is also accepted and wrapped in a one-element list
    so 1-call cases in parallel data don't trip on shape.
    Returns None on any parse / shape failure."""
    candidates: list[str] = []
    for match in _FENCED_JSON_RE.finditer(response):
        candidates.append(match.group(1).strip())
    candidates.append(response.strip())

    for cand in candidates:
        try:
            obj = json.loads(cand)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(obj, list):
            calls: list[dict[str, Any]] = []
            bad = False
            for item in obj:
                coerced = _coerce_call(item)
                if coerced is None:
                    bad = True
                    break
                calls.append(coerced)
            if not bad and calls:
                return calls
        else:
            single = _coerce_call(obj)
            if single is not None:
                return [single]
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


def _value_matches_list_of_dicts(
    value: list[Any], accepted: list[Any],
) -> bool:
    """Handle `array[dict]` arguments. Mirrors upstream's
    `list_dict_checker`: `accepted` is a list of alternative
    answers; each alternative is a position-indexed list of
    per-slot dict acceptance specs. The model's list must match
    every position of at least one alternative, matching each
    position via the same rules as `_value_matches_dict` on a
    single-alternative wrapper."""
    for alternative in accepted:
        if not isinstance(alternative, list):
            continue
        if len(alternative) != len(value):
            continue
        ok = True
        for model_dict, position_spec in zip(value, alternative):
            if not isinstance(model_dict, dict) or not isinstance(position_spec, dict):
                ok = False
                break
            if not _value_matches_dict(model_dict, [position_spec]):
                ok = False
                break
        if ok:
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
            nested_type = None
            if declared_type in _NESTED_TYPES:
                nested_type = schema.get("items", {}).get("type")
            if nested_type == "dict":
                ok = _value_matches_list_of_dicts(value, accepted)
            else:
                ok = _value_matches_list(
                    value, accepted, nested_is_string=(nested_type == "string"),
                )
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


def _find_tool_schema(
    tools: list[dict[str, Any]], name: str,
) -> dict[str, Any] | None:
    for t in tools:
        if t.get("name") == name:
            return t
    return None


def _check_parallel_no_order(
    tool_schemas: list[dict[str, Any]],
    model_calls: list[dict[str, Any]],
    gt_items: list[dict[str, Any]],
) -> ScoreResult:
    """Ports upstream's `parallel_function_checker_no_order`. For
    each ground-truth call, find any unmatched model call that
    passes `_check_simple_call` and consume it. Exact count
    required."""
    if len(model_calls) != len(gt_items):
        return ScoreResult(
            passed=False, fraction=0.0,
            detail=(
                f"expected {len(gt_items)} call(s), "
                f"got {len(model_calls)}"
            ),
        )

    matched: set[int] = set()
    for i, gt_item in enumerate(gt_items):
        gt_fn_name = next(iter(gt_item.keys()))
        schema = _find_tool_schema(tool_schemas, gt_fn_name)
        if schema is None:
            return ScoreResult(
                passed=False, fraction=0.0,
                detail=(
                    f"ground-truth call {i} references tool "
                    f"{gt_fn_name!r}, not declared in task's schema list"
                ),
            )
        found = False
        last_detail = ""
        for j, call in enumerate(model_calls):
            if j in matched:
                continue
            r = _check_simple_call(schema, call, gt_item)
            if r.passed:
                matched.add(j)
                found = True
                break
            last_detail = r.detail
        if not found:
            return ScoreResult(
                passed=False, fraction=0.0,
                detail=(
                    f"no model call matched GT call {i} for "
                    f"{gt_fn_name!r}; last attempt: {last_detail}"
                ),
            )
    return ScoreResult(passed=True, fraction=1.0, detail="ok")


# ============================================================================
# Benchmark
# ============================================================================


class BFCLBench:
    """BFCL benchmark for one of five categories:
    `simple_python`, `multiple`, `parallel`, `parallel_multiple`,
    `live_simple`.

    Construct with `category` and paths to the two JSONL files
    (questions and `possible_answer`). Fetch them via
    `scripts/download_bfcl.py` into `data/bfcl/`.

    `task_ids` filters to a subset; KeyError if any named id is
    absent from the loaded file.
    """

    def __init__(
        self,
        category: str,
        questions_path: Path,
        answers_path: Path,
        task_ids: Iterable[str] | None = None,
    ) -> None:
        if category not in _SUPPORTED_CATEGORIES:
            raise ValueError(
                f"BFCL category {category!r} not supported; "
                f"supported: {sorted(_SUPPORTED_CATEGORIES)}"
            )
        self.category = category
        self.name = f"bfcl_{category}"

        questions = self._load_jsonl(questions_path)
        answers = self._load_jsonl(answers_path)

        self._questions: dict[str, dict[str, Any]] = {
            q["id"]: q for q in questions
        }
        self._answers: dict[str, dict[str, Any]] = {
            a["id"]: a for a in answers
        }

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
        template = _query_template(self.category)
        for task_id, q in self._questions.items():
            tools = q["function"]
            user_msg = _first_user_message(q["question"])
            if self.category in ("simple_python", "live_simple", "parallel"):
                # single tool — render the bare schema dict rather
                # than a 1-element list for consistency with the
                # "exactly one tool" phrasing in the template.
                tool_payload: Any = tools[0]
            else:
                tool_payload = tools
            query_text = template.format(
                tool_json=json.dumps(tool_payload, indent=2),
                user_prompt=user_msg,
            )
            yield Task(id=task_id, query_text=query_text)

    def score(self, task_id: str, response: str) -> ScoreResult:
        if task_id not in self._questions:
            raise KeyError(f"task_id {task_id!r} not in this BFCLBench")

        q = self._questions[task_id]
        a = self._answers[task_id]
        tools: list[dict[str, Any]] = q["function"]
        gt_items: list[dict[str, Any]] = a["ground_truth"]

        if self.category in _SINGLE_CALL_CATEGORIES:
            call = _extract_function_call(response)
            if call is None:
                return ScoreResult(
                    passed=False, fraction=0.0,
                    detail="failed to extract JSON function call from response",
                )
            gt_item = gt_items[0]
            gt_fn_name = next(iter(gt_item.keys()))
            # For `multiple`, pick the schema whose name matches
            # GT. For `simple_python` / `live_simple`, there's
            # exactly one candidate, so take it directly; the
            # mismatch-name case is reported by `_check_simple_call`.
            schema = (
                _find_tool_schema(tools, gt_fn_name)
                if self.category == "multiple"
                else tools[0]
            )
            if schema is None:
                return ScoreResult(
                    passed=False, fraction=0.0,
                    detail=(
                        f"ground-truth function {gt_fn_name!r} not "
                        f"among candidate tools {[t['name'] for t in tools]!r}"
                    ),
                )
            return _check_simple_call(schema, call, gt_item)

        # parallel / parallel_multiple
        calls = _extract_function_calls(response)
        if calls is None:
            return ScoreResult(
                passed=False, fraction=0.0,
                detail="failed to extract JSON function-call list from response",
            )
        return _check_parallel_no_order(tools, calls, gt_items)


def _first_user_message(question_field: list[list[dict[str, str]]]) -> str:
    """BFCL's `question` field is a nested list: outer list for
    conversation turns (single-turn = 1 element), inner list for
    messages within a turn. The categories supported here are
    all single-turn; we extract defensively."""
    for turn in question_field:
        for msg in turn:
            if msg.get("role") == "user":
                return str(msg.get("content", ""))
    return ""
