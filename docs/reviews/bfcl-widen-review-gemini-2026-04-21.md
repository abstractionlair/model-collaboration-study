# BFCL widen-categories review — Gemini 3.1 Pro

**Reviewer:** Gemini 3.1 Pro (preview), MCP session
`mcs-bfcl-widen-review-gemini`, session
`47fd31e0-1d88-4d04-b006-656f69478d4b`. Continuation of the
round-5 review at `docs/reviews/bfcl-review-gemini-2026-04-21.md`
(which flagged the 100%-ceiling concern that this widen session
was the direct response to).

**Subject:** Commits `0c28cea` + `8ccfe69`. Primary files:
`src/experiment/benchmarks/bfcl.py`, `tests/test_benchmarks_bfcl.py`,
`data/mini_bench_runs/README.md`.

**Verdict:** Proceed.


## Full review text

> The widening of the BFCL adapter to five categories is
> structurally sound, faithfully implements upstream's
> order-independent matching, and successfully expands the
> framework's coverage to multi-tool and multi-call scenarios.
> The 100% Condition-A ceiling across all new categories
> validates the round-5 concern but is an experimental-design
> parameter issue, not an adapter architecture flaw. There are
> no blocking issues in the codebase; the implementation is
> robust, well-tested, and cleanly isolates the multi-call
> parsing and scoring logic. Proceed directly to the pre-
> kickoff power analysis.

### Per-finding notes

1. **Ceiling concern and Phase 1 design.** The widening did
   *not* resolve the ceiling concern; the 100% Condition-A
   pass rate across all new categories empirically confirms
   it. However, the Phase 1 design does not need a fundamental
   rethink. Instead, the operational parameters must adapt.
   The upcoming power analysis must model this ceiling to
   determine the required N for statistical power. If power is
   unachievable, Phase 1 will need to restrict the tool-use
   stratum to a harder subset (e.g., high-index
   `parallel_multiple` tasks or adding `live_parallel_multiple`).
2. **The `parallel_2` observation risk.** The Condition D
   degradation (coercing a string enum to a physical float
   after peer revision) is a highly valuable finding. Rather
   than threatening the collaboration-lifts-capability thesis,
   it *enriches* the study by surfacing a concrete failure
   mode: "authoritative deception" or over-correction during
   peer review. This is exactly the kind of structural
   interaction the experimental design aims to measure. Phase
   1 at scale will determine if this is an edge case that
   averages out or a systematic penalty for specific task
   shapes.
3. **Faithfulness of `_check_parallel_no_order`.** Port is
   faithful. Correctly enforces an exact call-count match and
   uses a greedy matching strategy (iterating through ground-
   truth items and consuming the first unmatched model call
   that passes the AST check). Accurately mirrors Gorilla's
   `parallel_function_checker_no_order`, cleanly reusing the
   rigorous `_check_simple_call` logic for the underlying
   validation.
4. **Scope of widening.** Leaving out `live_multiple`,
   `live_parallel`, and `live_parallel_multiple` is
   acceptable. Moving from one to five categories leaves the
   Phase 1 tool-use bucket in a significantly better spot by
   proving out multi-call extraction, order-independent
   scoring, and multi-tool query templates. The remaining
   categories reuse these exact same scorers and only require
   data fetching and dispatch wiring.
5. **Blocking issues.** None. The abstractions hold, tests are
   comprehensive, code is clean. Pre-kickoff power analysis is
   the immediate next unblocker to determine the N required
   to overcome the confirmed ceiling.


## How findings were handled

1. **Ceiling unresolved, power analysis now urgent** —
   reinforces Opus 4.7's routing recommendation (escalated in
   this session from #2 to #1). Tracked in status.md
   "Currently routed to."
2. **`parallel_2` framing** — Gemini reads it as a valuable
   study-enriching finding; Codex gave a sharper mechanistic
   explanation (D's revise step drops task context;
   `prompts.py:131` and `interpreter.py:276–282`). Both
   interpretations are compatible. The Codex finding is the
   actionable one (fix prompt template OR keep as a design
   variant to measure); Gemini's framing is how the
   phenomenon relates to the study thesis. Tracked as
   follow-up work for a future session.
3. **Port faithful** — no changes.
4. **Scope OK** — no changes; residual categories tracked.
5. **No blockers** — proceed to power analysis.
