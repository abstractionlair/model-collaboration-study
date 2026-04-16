# Project Status

**Last updated:** 2026-04-16

The volatile top of the stack. Read at session start to know what's
happening and what to do next. Write at *task start*, not task end:
before starting any substantive unit of work, update the "Next up"
list to reflect what you're about to do.

For durable state, see `docs/design/system-architecture.md` and
`docs/decisions.md`. For ideas not currently being worked on, see
`docs/backlog.md`.


## Phase

Design phase **complete** (promoted 2026-04-14). Phase 1
implementation substantially built as of 2026-04-16: typed IR,
executor with real `ApiClient` (Anthropic/OpenAI/Google/xAI),
experiment-spec layer, Phase 1 condition factories A–E, and
end-to-end smoke tests passing across all four providers. The
major gaps to a real Phase 1 run are a benchmark runner (nothing
yet adapts SWE-bench / LiveCodeBench / BFCL to the executor), a
run manifest schema, budget-cap enforcement, and the pre-kickoff
power analysis.

Before investing in any of those, a **fresh-context independent
review** is the next active task — see "Currently routed to."


## Next up

1. ~~Build the experiment-spec layer.~~ Done — `src/experiment/`.
2. ~~Express macro-models A–E.~~ Done. All 12 condition-tier pairs
   build, type-check, and run through the executor. `Fuse` node
   added to the IR for Condition E.
3. ~~Wire a real `ModelClient`.~~ Done — `src/executor/api_client.py`.
   Anthropic, OpenAI, and Google adapters with retry/backoff and
   token-usage tracking.
4. ~~Integrate `PromptTemplates` into the executor.~~ Done.
   Interpreter accepts `PromptTemplates`; defaults to
   structured-critique format from `src/experiment/prompts.py`.
5. ~~End-to-end smoke tests with real APIs.~~ Done 2026-04-16.
   All conditions A–E pass across 4 providers (Anthropic, OpenAI,
   Google, xAI). 49 API calls, 0 retries. Intermediate steps
   (review, revise, fuse) verified to attempt what was asked.
   TracingClient captures full request/response traces.
6. **Fresh-context independent review of the full system** (see
   "Currently routed to"). Gates everything below.
7. Address review findings. Then, in some order: benchmark
   adapters, experiment runner with budget-cap enforcement, run
   manifest schema, pre-kickoff power analysis.


## Currently routed to

**Independent system review.** The incoming fresh-context agent
should treat the entire system (as of commit `16e1f78`) as an
artifact under review. Almost all of `src/experiment/`,
`src/executor/api_client.py`, `src/executor/tracing.py`,
`src/protocols/conditions.py`, and the `Fuse` node in the IR were
written in one extended session by the prior Opus. That instance
can no longer review its own work independently; fresh eyes are
the point.

### How to run the review

Follow `WORKFLOW.md` → "Review Procedure" and use the review
template there. Deliverable: a file in `docs/reviews/` named
`system-review-<reviewer>-2026-04-16.md`. Recommendation field
should be actionable ("Proceed / Revise / Rethink") scoped to the
review's findings.

### What to review, against what

Check the code against the committed design artifacts — the
design is locked, the code is on trial, not the reverse.

Primary design references the code should be consistent with:

- `docs/research/experimental-design.md` — the committed Phase 1
  design. Condition definitions, compute-matching semantics,
  statistical plan, scoping, failure-handling policy.
- `docs/decisions.md` — locked decisions. Particularly the
  macro-model framing (2026-04-14) and the `Fuse` naming decision
  (2026-04-16).
- `docs/design/system-architecture.md` — the layer structure and
  IR invariants.

Surfaces worth scrutinizing (non-exhaustive — fresh eyes may find
things this list misses):

- **Conditions A–E** (`src/protocols/conditions.py`) — do they
  faithfully express the macro-models in the experimental design,
  or did the implementation quietly reinterpret them?
  - Conditions B and C aggregate via `ParScore + WeightedVote`
    (each candidate scored independently by a model, highest
    wins). The design calls this a "peer-judge aggregation block"
    that "chooses among the N candidates." Is independent
    pointwise scoring a faithful implementation of that intent,
    or does it silently change what is being tested?
  - Condition E is `ParGen → ReviseRound → Fuse(meta)`. The
    design text says the meta-reviewer "synthesizes the critiques
    and writes the final response directly." The implementation
    has the meta-reviewer see the *revised drafts*, not the raw
    critiques. Faithful?
- **The selector-as-oracle discipline.** The design is emphatic
  that the final executable evaluator must never be the internal
  aggregator. Do the conditions respect this in code? Anything
  that could leak oracle information into selection?
- **`PromptTemplates` + executor integration.** Every prompt
  site replaced, no stragglers? Does the `Fuse` prompt actually
  elicit synthesis, or does it read as selection?
- **`ApiClient`.** Retry classification (infra vs capability) —
  correct per provider? Token accounting sensible? Any provider
  where errors escape the `InfrastructureError` wrapper? Any
  `Any` that should be tighter?
- **Phase 1 builder** (`src/experiment/phase1.py`). Two specific
  placeholders worth calling out:
  - `_best_model()` returns Haiku as a "conservative default"
    for the A/B/D' baselines. Real value comes from calibration,
    not yet run. Is having this placeholder live in code a
    footgun?
  - `_n_samples_for_b()` picks N=1/3/6 at $X/$2X/$4X by hand.
    No cost calibration behind it. Is this reasonable placeholder
    or dangerous?
  - `PHASE1_PRICING` is hardcoded from pre-kickoff notes; design
    says "verify before kickoff."
- **Smoke tests** (`scripts/smoke_test.py`). The "PASS" verdict
  is based on keyword checks (does the review contain evaluative
  language? does a score parse as a float in [0,1]?). This
  verifies the machinery runs and steps attempt what was asked;
  it does not verify that outputs are correct. Is the claim
  scoped honestly in the commit message and status update, or is
  it overclaiming?
- **Typed IR**. `mypy --strict` passes on all 19 source files —
  but passing strict mode is not the same as being well-typed.
  Are there `Any` escape hatches, loose generics, or places
  where the type system fails to catch a meaningful class of
  errors?

### Explicitly NOT built (don't flag as missing)

- Experiment runner executing the spec against a benchmark.
- Benchmark adapters (SWE-bench, LiveCodeBench, BFCL).
- Run manifest schema (tracked in `docs/backlog.md`).
- Power analysis.
- `ContextMode.ACCUMULATED` real-client support.
- `ReviseFromMany` or advisory-synthesis IR nodes (names
  reserved in `docs/decisions.md`; no concrete use case yet).

### After this review

Parallel reviews from Codex (`mcs-coord`) and Gemini
(`mcs-coord-gemini`) would give stronger triangulation —
different training lineages, not just different context. Worth
running after the Opus review so the second-lineage reviewers
can be pointed at the review findings, not just the artifacts.


## Blockers

None.
