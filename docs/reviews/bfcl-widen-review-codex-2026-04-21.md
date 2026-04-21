# BFCL widen-categories review — Codex (GPT-5.4)

**Reviewer:** Codex (GPT-5.4), MCP session `mcs-bfcl-widen-review`,
thread `019db24b-993c-70c2-9ce8-32ee5262c8b8`. Continuation of
the earlier BFCL round-5 review at
`docs/reviews/bfcl-review-codex-2026-04-21.md`.

**Subject:** Commits `0c28cea` (widen BFCL to five categories)
and `8ccfe69` (wording-fix follow-up). Primary files:
`src/experiment/benchmarks/bfcl.py`, `tests/test_benchmarks_bfcl.py`,
`scripts/run_bfcl.py`, `scripts/download_bfcl.py`,
`data/mini_bench_runs/README.md`.

**Verdict:** Proceed.


## Full review text

> I don't see a blocker in the widen-to-five BFCL adapter
> change itself. The adapter logic in
> `src/experiment/benchmarks/bfcl.py` is semantically aligned
> with Gorilla's `parallel_function_checker_no_order`, the
> four-way prompt split is a clean factoring, and the added
> category coverage is a reasonable stopping point for this
> session. The one place I'd sharpen the write-up is the
> interpretation of `parallel_2`: "peer critique pushed correct
> drafts wrong" is plausible, but the cleaner causal story is
> that D's revise step drops the original task/schema context,
> so an authoritative but schema-violating critique has an easy
> path to corrupt a previously correct draft. That is a real
> collaborative failure mode, but not quite the same claim as
> "peer review alone inverted correctness."

### Per-finding notes

1. **Q1 / no-order port.** Semantically faithful. Upstream does
   exact-count check, then greedily walks GT calls, finds any
   unmatched model call that passes `simple_function_checker`,
   and consumes it; local `_check_parallel_no_order` does the
   same. The main difference is only diagnostics: upstream
   accumulates richer per-candidate errors, while local code
   returns the last failure detail.
2. **Q2 / multi-call extractor.** Array handling is
   directionally right. Rejecting the whole array on one bad
   element is the safer choice; otherwise you risk partial-
   credit behavior BFCL does not define. Auto-wrapping a bare
   object to a 1-list is slightly permissive, but not harmful
   for current data: both `parallel` and `parallel_multiple`
   have minimum ground-truth call count 2, so a bare object
   cannot false-pass because the later count check still fails.
   Unnecessary for today's data, but not a reason to revise.
3. **Q3 / query-template factoring.** Four templates are the
   right call. The branches in `_query_template` correspond to
   real instruction changes, not cosmetic variation. A single
   template with conditionals would be terser but less legible.
4. **Q4 / `parallel_2` interpretation.** Would not attribute
   this primarily to a formatting directive. The stronger
   explanation is **protocol context loss**: D's revise step in
   `src/executor/interpreter.py` (lines 276–282) calls the
   revise prompt with only `{critique, draft}`, and the default
   revise template in `src/experiment/prompts.py` (line 131)
   likewise omits the original task/schema. So the likely story
   is "peer critique introduced the wrong physical-constant
   idea, and the revise stage had no task/schema anchor to
   resist it." E passing the same task is consistent with this,
   because E's fuse prompt re-includes the task.
5. **Q5 / missing categories.** Five is enough for this
   change. The obvious cheap next additions are `live_multiple`,
   `live_parallel`, and `live_parallel_multiple` (same scorer/
   query families). `multi_turn_*` is a different benchmark
   shape and was correctly left out.
6. **Minor documentation nit.** `scripts/download_bfcl.py`
   docstring still said "simple_python category" despite the
   script fetching five categories. **Addressed in the
   follow-up commit.**
7. **Verification note.** Could not run `pytest` in the review
   sandbox (no writable temp directory), so this review is from
   static inspection plus local BFCL data / run-log inspection.


## How findings were handled

1. **No-order port faithful** — no changes.
2. **Multi-call extractor auto-wrap** — acknowledged
   non-harmful-today; no change. Track if future categories
   violate the min-count-2 assumption.
3. **Template factoring** — no change.
4. **`parallel_2` / protocol context loss** — **primary finding
   of this review.** Verified directly: `_REVISE_USER` in
   `prompts.py:131` takes only `{critique, draft}`; the revise
   call site in `interpreter.py:276–282` passes only those two.
   `_FUSE_USER` at line 138 starts with `Task:\n{query}`, so E
   has the original task in-context during synthesis; D does
   not. This is a system-level finding beyond the widen scope.
   Status.md and decisions routing updated to flag this as
   work for a future session; no code changes to prompt
   templates in this commit. The earlier "peer critique
   authority pushed drafts wrong" framing in status.md and the
   validation README is being revised to name the missing-task-
   context mechanism instead.
5. **Missing categories (scope OK)** — no change; tracked as
   future work in the residual-BFCL section of status.md.
6. **Stale docstring** — fixed in the commit that accompanies
   this review transcription.
