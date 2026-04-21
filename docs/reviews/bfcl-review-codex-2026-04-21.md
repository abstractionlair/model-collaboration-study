# BFCL adapter review — Codex (GPT-5.4)

**Reviewer:** Codex (GPT-5.4), MCP session `mcs-bfcl-review`,
thread `019db002-0c50-7933-aa58-279f53e0bdbb`.

**Subject:** `src/experiment/benchmarks/bfcl.py` and surrounding
files; first Phase-1-matrix benchmark adapter (BFCL,
`simple_python` category only).

**Two-pass review:** first pass against commit `2860c2d` (initial
BFCL adapter commit); second pass against commit `3f9ddb7`
(follow-up fix for `array[dict]` scorer).


## Round 1 verdict: Revise and re-review

Commit reviewed: `2860c2d`.

### Findings

1. **`array[dict]` scorer — broken.** The port routes every
   list-valued argument through `_value_matches_list`, but
   upstream BFCL has a separate `list_dict_checker` path that
   recursively applies `dict_checker`. In the current
   `simple_python` snapshot this affects real tasks, not just
   hypotheticals: `simple_python_96::database.query` has
   `conditions: array[dict]`, and the local scorer rejects
   even the exact intended structure because it compares
   against the raw accepted-value schema instead of per-dict
   accepted values. The tests miss this entirely.

2. **Dotted-name compatibility omitted.** Upstream's
   `convert_func_name` replaces `.` with `_` for model
   families whose native tool-calling API forbids dots. 167/400
   `simple_python` tasks use dotted names; the port hard-fails
   a model that emits the underscore form. This is a
   deliberate narrowing (we don't use native tool-calling) but
   wasn't documented as such.

3. **`is_variable` branch skipped** — mostly fine for
   concrete-value JSON output, but not literally harmless:
   `simple_python_307::venue: ["", true]` against a declared
   `string` type can be accepted by upstream via the
   `is_variable` path, and this port cannot. Rare, but
   should be named.

### Non-findings (acknowledged as acceptable)

- The `Benchmark` protocol interface looks fine for SWE-bench
  and LiveCodeBench, because the benchmark can keep hidden
  harness state behind `task_id`. Wouldn't change it yet.
- `simple_python`-only is defensible as a narrow Phase 1
  "single-tool structured invocation" slice, but not as a
  proxy for BFCL broadly. The risk is exactly that it excludes
  multiple/parallel/live/multi-turn settings, which are more
  coordination-heavy and more likely to show collaboration
  gains.
- The 15/15 validation does not read as "scorer too
  permissive" — if anything, the concrete scorer bug is too
  strict, not too loose.


## Round 2 verdict: Proceed

Commit reviewed: `3f9ddb7`.

### Summary

> The `array[dict]` fix addresses the concrete faithfulness
> bug from the last review. `_check_simple_call` now
> dispatches `items.type == "dict"` through
> `_value_matches_list_of_dicts`, and that helper has the
> right upstream shape: alternatives at the outer level,
> position-aligned matching within an alternative, each slot
> checked with dict semantics via `_value_matches_dict`. On
> the real BFCL row that was previously wrong,
> `simple_python_96::database.query`, the canonical answer
> now passes and swapped-position / wrong-length variants fail.
>
> The five new tests […] are the right ones for this fix.
> They cover the actual regression surface: canonical success,
> position sensitivity, length mismatch, missing required
> inner key, and multi-alternative acceptance. That closes
> the main gap.
>
> From my previous list, the remaining concrete concerns are
> now correctly downgraded to explicit deviations rather than
> hidden mismatches. The docstring now names both dotted-name
> strictness and the skipped `is_variable` branch, which was
> the important part. I do not see another live
> scorer-faithfulness issue in the changed area.

### Non-blocking residual

- No unit test for the optional `array[dict]` omission
  sentinel case (`[""]`), e.g. `simple_python_335::deck`.
  Path was verified against real data out-of-band. Test
  hardening, not a re-review blocker. **Addressed in commit
  `721c98b`.**
