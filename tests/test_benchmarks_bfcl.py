"""Unit tests for the BFCL adapter.

Uses hand-authored in-test datasets (not the real BFCL files)
so the tests don't depend on `scripts/download_bfcl.py` having
been run. Real data goes through the same code paths; these
tests pin the behavioural invariants.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.experiment.benchmarks import BFCLBench, ScoreResult
from src.experiment.benchmarks.bfcl import (
    _check_simple_call,
    _extract_function_call,
    _normalize_string,
)


# ============================================================================
# Helpers
# ============================================================================


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def _triangle_schema() -> dict[str, Any]:
    """Mirrors simple_python_0 from BFCL."""
    return {
        "name": "calculate_triangle_area",
        "description": "Calculate the area of a triangle given its base and height.",
        "parameters": {
            "type": "dict",
            "properties": {
                "base": {"type": "integer", "description": "The base."},
                "height": {"type": "integer", "description": "The height."},
                "unit": {"type": "string", "description": "The unit."},
            },
            "required": ["base", "height"],
        },
    }


def _triangle_ground_truth() -> dict[str, Any]:
    return {
        "calculate_triangle_area": {
            "base": [10],
            "height": [5],
            "unit": ["units", ""],
        },
    }


# ============================================================================
# _normalize_string
# ============================================================================


def test_normalize_strips_punctuation_and_lowercases() -> None:
    assert _normalize_string("April 1, 2024") == "april12024"
    assert _normalize_string("Foo-Bar_Baz") == "foobarbaz"
    # Exclamation / bang is NOT stripped by BFCL — only [ ,./-_*^].
    assert _normalize_string("Hello, World!") == "helloworld!"


def test_normalize_single_to_double_quotes() -> None:
    assert _normalize_string("it's fine") == 'it"sfine'


# ============================================================================
# _extract_function_call
# ============================================================================


def test_extract_fenced_json() -> None:
    r = 'Here:\n```json\n{"name": "foo", "arguments": {"x": 1}}\n```'
    assert _extract_function_call(r) == {"name": "foo", "arguments": {"x": 1}}


def test_extract_bare_fence() -> None:
    r = '```\n{"name": "foo", "arguments": {"x": 1}}\n```'
    assert _extract_function_call(r) == {"name": "foo", "arguments": {"x": 1}}


def test_extract_bare_json_no_fence() -> None:
    r = '{"name": "foo", "arguments": {"x": 1}}'
    assert _extract_function_call(r) == {"name": "foo", "arguments": {"x": 1}}


def test_extract_prose_surrounding_fence() -> None:
    r = 'Thinking...\n```json\n{"name": "f", "arguments": {}}\n```\nDone.'
    assert _extract_function_call(r) == {"name": "f", "arguments": {}}


def test_extract_openai_style_arguments_as_json_string() -> None:
    """OpenAI's tool-use schema serialises `arguments` as a
    JSON-encoded string. Our extractor unwraps it."""
    r = '```json\n{"name": "foo", "arguments": "{\\"x\\": 1}"}\n```'
    assert _extract_function_call(r) == {"name": "foo", "arguments": {"x": 1}}


def test_extract_invalid_json_returns_none() -> None:
    assert _extract_function_call("not json at all") is None


def test_extract_missing_arguments_returns_none() -> None:
    r = '```json\n{"name": "foo"}\n```'
    assert _extract_function_call(r) is None


def test_extract_missing_name_returns_none() -> None:
    r = '```json\n{"arguments": {"x": 1}}\n```'
    assert _extract_function_call(r) is None


def test_extract_prefers_valid_fenced_over_invalid_bare() -> None:
    """If the fenced block parses but the bare response doesn't,
    we should return the fenced result — not fall through."""
    r = (
        "Some free prose that\ndoesn't parse as JSON on its own\n"
        '```json\n{"name": "foo", "arguments": {}}\n```\n'
        "More prose."
    )
    assert _extract_function_call(r) == {"name": "foo", "arguments": {}}


def test_extract_extra_keys_ignored() -> None:
    """Models sometimes add `reasoning` or `description` keys
    alongside name/arguments. Those should be ignored."""
    r = (
        '```json\n{"name": "f", "arguments": {"x": 1}, '
        '"reasoning": "because"}\n```'
    )
    assert _extract_function_call(r) == {"name": "f", "arguments": {"x": 1}}


# ============================================================================
# _check_simple_call — happy path
# ============================================================================


def test_check_perfect_match() -> None:
    call = {
        "name": "calculate_triangle_area",
        "arguments": {"base": 10, "height": 5, "unit": "units"},
    }
    result = _check_simple_call(
        _triangle_schema(), call, _triangle_ground_truth(),
    )
    assert result.passed
    assert result.fraction == 1.0


def test_check_optional_param_omitted_when_empty_in_accepted() -> None:
    """`unit` has "" in accepted values, so it's optional. Omitting it
    should still pass."""
    call = {
        "name": "calculate_triangle_area",
        "arguments": {"base": 10, "height": 5},
    }
    result = _check_simple_call(
        _triangle_schema(), call, _triangle_ground_truth(),
    )
    assert result.passed


def test_check_string_match_case_insensitive() -> None:
    call = {
        "name": "calculate_triangle_area",
        "arguments": {"base": 10, "height": 5, "unit": "UNITS"},
    }
    result = _check_simple_call(
        _triangle_schema(), call, _triangle_ground_truth(),
    )
    assert result.passed


def test_check_string_match_punctuation_normalised() -> None:
    """BFCL standardises strings by stripping punctuation."""
    schema: dict[str, Any] = {
        "name": "set_date",
        "parameters": {
            "type": "dict",
            "properties": {
                "date": {"type": "string", "description": "date"},
            },
            "required": ["date"],
        },
    }
    gt = {"set_date": {"date": ["April 1, 2024"]}}
    # Model emits differently-punctuated version; normalisation
    # should still match.
    call = {"name": "set_date", "arguments": {"date": "April 1 2024"}}
    result = _check_simple_call(schema, call, gt)
    assert result.passed


# ============================================================================
# _check_simple_call — failure modes
# ============================================================================


def test_check_wrong_function_name() -> None:
    call = {
        "name": "calculate_rectangle_area",
        "arguments": {"base": 10, "height": 5},
    }
    result = _check_simple_call(
        _triangle_schema(), call, _triangle_ground_truth(),
    )
    assert not result.passed
    assert "wrong function name" in result.detail


def test_check_missing_required_param() -> None:
    call = {"name": "calculate_triangle_area", "arguments": {"base": 10}}
    result = _check_simple_call(
        _triangle_schema(), call, _triangle_ground_truth(),
    )
    assert not result.passed
    assert "missing required" in result.detail


def test_check_unexpected_param() -> None:
    """Model supplies a parameter not declared in the schema."""
    call = {
        "name": "calculate_triangle_area",
        "arguments": {"base": 10, "height": 5, "area_in_m2": True},
    }
    result = _check_simple_call(
        _triangle_schema(), call, _triangle_ground_truth(),
    )
    assert not result.passed
    assert "unexpected parameter" in result.detail


def test_check_wrong_value_for_required() -> None:
    call = {
        "name": "calculate_triangle_area",
        "arguments": {"base": 999, "height": 5},
    }
    result = _check_simple_call(
        _triangle_schema(), call, _triangle_ground_truth(),
    )
    assert not result.passed
    assert "not in accepted" in result.detail


def test_check_wrong_type_for_param() -> None:
    """`base` is declared integer; supplying a string fails."""
    call = {
        "name": "calculate_triangle_area",
        "arguments": {"base": "10", "height": 5},
    }
    result = _check_simple_call(
        _triangle_schema(), call, _triangle_ground_truth(),
    )
    assert not result.passed
    assert "expected integer" in result.detail


def test_check_bool_rejected_for_int_param() -> None:
    """bool is a subclass of int in Python; BFCL treats them
    strictly, so True must not be accepted where int is
    declared even though `True == 1`."""
    call = {
        "name": "calculate_triangle_area",
        "arguments": {"base": True, "height": 5},
    }
    result = _check_simple_call(
        _triangle_schema(), call, _triangle_ground_truth(),
    )
    assert not result.passed
    assert "expected integer" in result.detail


# ============================================================================
# _check_simple_call — int → float coercion
# ============================================================================


def test_check_int_coerced_to_float_for_float_param() -> None:
    schema: dict[str, Any] = {
        "name": "sqrt",
        "parameters": {
            "type": "dict",
            "properties": {"x": {"type": "float", "description": "val"}},
            "required": ["x"],
        },
    }
    gt = {"sqrt": {"x": [4.0]}}
    # Model sends int 4; should be promoted to 4.0 and match.
    call = {"name": "sqrt", "arguments": {"x": 4}}
    result = _check_simple_call(schema, call, gt)
    assert result.passed


# ============================================================================
# _check_simple_call — list and dict
# ============================================================================


def test_check_list_of_strings_with_normalisation() -> None:
    schema: dict[str, Any] = {
        "name": "route.estimate",
        "parameters": {
            "type": "dict",
            "properties": {
                "stops": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Cities",
                },
            },
            "required": ["stops"],
        },
    }
    gt = {"route.estimate": {"stops": [["Santa Barbara", "Monterey"]]}}
    call = {
        "name": "route.estimate",
        "arguments": {"stops": ["santa barbara", "monterey"]},
    }
    result = _check_simple_call(schema, call, gt)
    assert result.passed


def test_check_list_length_mismatch_fails() -> None:
    schema: dict[str, Any] = {
        "name": "route.estimate",
        "parameters": {
            "type": "dict",
            "properties": {
                "stops": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Cities",
                },
            },
            "required": ["stops"],
        },
    }
    gt = {"route.estimate": {"stops": [["Santa Barbara", "Monterey"]]}}
    call = {
        "name": "route.estimate",
        "arguments": {"stops": ["Santa Barbara"]},
    }
    result = _check_simple_call(schema, call, gt)
    assert not result.passed


# ============================================================================
# BFCLBench loading / subsetting
# ============================================================================


def test_bench_loads_and_yields_tasks(tmp_path: Path) -> None:
    qf = tmp_path / "q.json"
    af = tmp_path / "a.json"
    _write_jsonl(qf, [{
        "id": "t0",
        "question": [[{"role": "user", "content": "What is 2+2?"}]],
        "function": [_triangle_schema()],
    }])
    _write_jsonl(af, [{"id": "t0", "ground_truth": [_triangle_ground_truth()]}])

    bench = BFCLBench(qf, af)
    tasks = list(bench.tasks())
    assert len(tasks) == 1
    assert tasks[0].id == "t0"
    # Query text includes the tool schema + user question
    assert "calculate_triangle_area" in tasks[0].query_text
    assert "What is 2+2?" in tasks[0].query_text
    assert "```json" in tasks[0].query_text


def test_bench_subset_filter(tmp_path: Path) -> None:
    qf = tmp_path / "q.json"
    af = tmp_path / "a.json"
    rows_q = [
        {
            "id": f"t{i}",
            "question": [[{"role": "user", "content": f"q{i}"}]],
            "function": [_triangle_schema()],
        }
        for i in range(3)
    ]
    rows_a = [
        {"id": f"t{i}", "ground_truth": [_triangle_ground_truth()]}
        for i in range(3)
    ]
    _write_jsonl(qf, rows_q)
    _write_jsonl(af, rows_a)

    bench = BFCLBench(qf, af, task_ids=["t0", "t2"])
    assert [t.id for t in bench.tasks()] == ["t0", "t2"]


def test_bench_unknown_task_id_raises(tmp_path: Path) -> None:
    qf = tmp_path / "q.json"
    af = tmp_path / "a.json"
    _write_jsonl(qf, [{
        "id": "t0",
        "question": [[{"role": "user", "content": "q"}]],
        "function": [_triangle_schema()],
    }])
    _write_jsonl(af, [{"id": "t0", "ground_truth": [_triangle_ground_truth()]}])

    with pytest.raises(KeyError, match="no questions for task_ids"):
        BFCLBench(qf, af, task_ids=["t0", "missing"])


def test_bench_missing_answer_raises(tmp_path: Path) -> None:
    """If some questions lack a possible_answer entry, surface
    loudly rather than scoring them silently."""
    qf = tmp_path / "q.json"
    af = tmp_path / "a.json"
    _write_jsonl(qf, [{
        "id": "t0",
        "question": [[{"role": "user", "content": "q"}]],
        "function": [_triangle_schema()],
    }])
    _write_jsonl(af, [])  # no answers at all

    with pytest.raises(ValueError, match="no possible_answer"):
        BFCLBench(qf, af)


# ============================================================================
# BFCLBench.score end-to-end
# ============================================================================


def test_bench_score_correct_response(tmp_path: Path) -> None:
    qf = tmp_path / "q.json"
    af = tmp_path / "a.json"
    _write_jsonl(qf, [{
        "id": "t0",
        "question": [[{"role": "user", "content": "triangle area"}]],
        "function": [_triangle_schema()],
    }])
    _write_jsonl(af, [{"id": "t0", "ground_truth": [_triangle_ground_truth()]}])

    bench = BFCLBench(qf, af)
    response = (
        "I'll compute the area.\n"
        "```json\n"
        '{"name": "calculate_triangle_area", '
        '"arguments": {"base": 10, "height": 5}}\n'
        "```\n"
    )
    result = bench.score("t0", response)
    assert result.passed
    assert result.fraction == 1.0


def test_bench_score_malformed_response(tmp_path: Path) -> None:
    qf = tmp_path / "q.json"
    af = tmp_path / "a.json"
    _write_jsonl(qf, [{
        "id": "t0",
        "question": [[{"role": "user", "content": "q"}]],
        "function": [_triangle_schema()],
    }])
    _write_jsonl(af, [{"id": "t0", "ground_truth": [_triangle_ground_truth()]}])

    bench = BFCLBench(qf, af)
    result = bench.score("t0", "I don't feel like using the tool.")
    assert not result.passed
    assert "failed to extract" in result.detail


def test_bench_score_unknown_task_raises(tmp_path: Path) -> None:
    qf = tmp_path / "q.json"
    af = tmp_path / "a.json"
    _write_jsonl(qf, [{
        "id": "t0",
        "question": [[{"role": "user", "content": "q"}]],
        "function": [_triangle_schema()],
    }])
    _write_jsonl(af, [{"id": "t0", "ground_truth": [_triangle_ground_truth()]}])

    bench = BFCLBench(qf, af)
    with pytest.raises(KeyError, match="not in this BFCLBench"):
        bench.score("unknown", "{}")


def test_bench_query_does_not_leak_ground_truth(tmp_path: Path) -> None:
    """Selector-as-oracle discipline: query_text must not contain
    the ground-truth function call."""
    qf = tmp_path / "q.json"
    af = tmp_path / "a.json"
    _write_jsonl(qf, [{
        "id": "t0",
        "question": [[{"role": "user", "content": "triangle with base 10 height 5"}]],
        "function": [_triangle_schema()],
    }])
    _write_jsonl(af, [{"id": "t0", "ground_truth": [_triangle_ground_truth()]}])

    bench = BFCLBench(qf, af)
    task = next(iter(bench.tasks()))
    # Ground-truth literally lists `"base": [10]` — the numeric
    # values from the user prompt are fine (they're the task),
    # but the `ground_truth` structure itself must not appear.
    assert "ground_truth" not in task.query_text
    assert '"base": [10]' not in task.query_text
