# Project Status

**Last updated:** 2026-04-19

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

**Three independent system reviews completed on 2026-04-16:**
- `docs/reviews/system-review-opus47-2026-04-16.md` (Opus 4.7,
  fresh-context)
- `docs/reviews/system-review-codex-2026-04-16.md` (Codex /
  GPT-5.4, `mcs-coord`)
- `docs/reviews/system-review-gemini-2026-04-16.md` (Gemini 3.1
  Pro, `mcs-coord-gemini`)

All three converged on *Revise and re-review*. The architectural
foundation (IR / executor / spec layer split, selector-as-oracle
discipline in code) was sound across all three reviewers; the
needed work was targeted reconciliation, not rethink.

**Reconciliations done as of 2026-04-16:**
- Design-doc scrub (commit `f295e59`): removed stale
  "executable scoring is the selection rule" language; deleted
  duplicated subsection.
- D-family review semantics (commits `82627d3` + follow-up):
  renamed self-review nodes; added `PeerReviseRound`/
  `PeerRounds` with cyclic 1-peer assignment; D/D'/E migrated.
- B/C aggregation (commit `4609c33`): added `PickOne`
  comparative-selection node; B/C migrated. ParScore +
  WeightedVote retained for D/D' confidence-weighted
  aggregation.
- E composition (this commit): added `ParPeerReview` and
  `FuseWithCritiques`; new `condition_e` is design-faithful;
  previous variant kept as `condition_e_writers_revise_then_fuse`.

**Round 2 cross-lineage reviews landed 2026-04-16:**
- `docs/reviews/system-review-codex-2026-04-16-round2.md`
- `docs/reviews/system-review-gemini-2026-04-16-round2.md`

Both reviewers confirmed the three faithfulness gaps are
resolved. Both listed an operational-readiness blocker set;
**all seven items addressed 2026-04-16** across two commits
(`10a2f5b` measurement/observability/tests, and the follow-up
API-reliability/calibration-gates commit). Summary of what
landed:

1. ~~Parser silent fallbacks (Codex #5, Gemini #4).~~
   `_parse_score` and `_parse_pick` now return None on failure;
   caller logs + seeded random fallback. WeightedVote ties
   broken by seeded random with telemetry.
2. ~~Generation stochasticity (Gemini #2, Codex #9).~~
   `ApiClient.temperature` is now `Optional[float]` defaulting
   to None; omitted from provider calls so vendor defaults
   apply. `decisions.md` 2026-04-16 entry on the temperature
   policy.
3. ~~Google retry classification (Codex #6).~~ Narrowed via
   `_is_google_infra()` predicate to 408/429/5xx + httpx
   network/timeout errors. Other 4xx propagate as regular
   exceptions.
4. ~~Empty-response handling and failed-call telemetry
   (Codex #7).~~ `CapabilityFailure` exception; empty responses
   raise it (with CallRecord appended so tokens are billed).
   Exhausted infra retries also now record CallRecord entries.
   New `CallRecord.status` field and count properties on
   ApiClient.
5. ~~Pre-calibration gates (Codex #8).~~ `build_phase1_conditions`
   and `build_phase1_spec` now require `best_model`,
   `n_samples_for_b`, and `pricing` as explicit keyword args.
   `PHASE1_PRICING` renamed to `PHASE1_PRICING_DRAFT`.
6. ~~TracingClient step_type staleness (Codex #4, round-2).~~
   Recognizes `pick_one` and `fuse_with_critiques`.
   More-specific matchers ordered first.
7. ~~FakeClient unit tests (Codex #10, round-1).~~ 44 tests in
   `tests/` covering identity memoization, ParGen/ParScore
   alignment, cyclic peer assignment, WeightedVote/PickOne
   non-positional fallback, drafts/critiques alignment,
   Phase 1 call counts, parser behavior, ApiClient status
   tracking, and calibration-gate errors.

**Round 3 cross-lineage reviews landed 2026-04-17:**
- `docs/reviews/system-review-codex-2026-04-17.md`
- `docs/reviews/system-review-gemini-2026-04-17.md`

Both reviewers confirmed the operational-readiness fixes
mostly hold; both at *Revise and re-review* for two specific,
fixable items:

1. **Parser priorities are inverted.** Both reviewers
   independently caught this. `_parse_score` checks last-float
   in [0,1] before the "N out of 10" pattern, so scale-echo
   responses ("On a scale of 0.0-1.0, I'd rate this 7 out of
   10") parse to 1.0 instead of 0.7. `_parse_pick` grabs the
   last in-range integer, hijacking "I pick 2 because
   candidate 3 is incomplete" → 3. Fix: check specific
   semantic patterns first; prefer None over confidently
   wrong.
2. **Telemetry black hole** (Gemini, new). The
   `InterpreterTelemetry` added in commit `10a2f5b` is
   inaccessible to callers because `run()` instantiates the
   `Interpreter`, calls `evaluate()`, returns only the result,
   and discards the Interpreter (and its telemetry). Fix:
   `run()` returns `(value, telemetry)` tuple OR runner uses
   Interpreter directly.

Other reviewer notes (not blocking, archived for the analysis
phase): vendor-default temperature variance is a real
interpretive confound (similar shape to price arbitrage) and
should be named explicitly when discussing why heterogeneity
works (Gemini); calibration should empirically verify that
homogeneous pools show meaningful variance under vendor
default rather than assume (Codex).

**Done 2026-04-19** in commit `c5211a2`:
- `_parse_score` priorities reordered: bare-number → "N out of
  10" → labeled (Score:/Confidence:/Rating:) → last-float-in-
  range → None.
- `_parse_pick` rewritten: bare response (`fullmatch` on
  optional "Candidate" + integer) → pick-verb pattern
  (`pick|choose|select|prefer|winner|answer is|...` near a
  number) → None.
- `run()` now returns `(result, telemetry)`. smoke_test.py and
  the test suite updated to unpack and surface non-zero
  counters as issues.
- 49 unit tests passing; mypy --strict clean on 24 files.

**Round 4 cross-lineage reviews landed 2026-04-19:**
- `docs/reviews/system-review-codex-2026-04-19.md`
- `docs/reviews/system-review-gemini-2026-04-19.md`

**Both reviewers recommend Proceed.** No structural,
faithfulness, or operational blockers remain. Minor
non-blocking notes for future hardening:
- Looser pick-verb phrasings ("my pick is 2", "I vote for 2",
  "choice: 2") return None rather than wrong; degrade to
  seeded-random fallback with telemetry. Worth widening when
  real traces show them (Codex).
- Score format "0.7/1.0" still falls through to last-float and
  parses as 1.0. Edge case on an edge case; not blocking
  (both reviewers).
- `smoke_test.py` pins `temperature=0.0` for deterministic
  plumbing — appropriate for smoke tests, must stay scoped to
  smoke-test behavior and not leak into Phase 1 defaults.
- Vendor-default temperature variance remains a real
  interpretive confound that should be named explicitly when
  discussing why heterogeneity works (Gemini, restated).
- A `RunResult` dataclass may become cleaner than the tuple
  if more per-run metadata accumulates; tuple is the right
  pragmatic choice for now (Codex).

**System is structurally sound, hermetically sealed from
ground truth, and ready for benchmark integration.** The
operational-readiness phase that opened on 2026-04-16 is
complete.


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
   All conditions A–E ran across 4 providers (Anthropic, OpenAI,
   Google, xAI) without exceptions. 49 API calls, 0 retries.
   Review responses contain evaluative language; score responses
   contain a parseable float in [0,1]. TracingClient captures
   full request/response traces. **Scope correction (Opus 4.7
   review #12):** the smoke test does NOT verify that revise
   actually changed the draft, that Fuse actually synthesized
   versus picked one verbatim, or that the score parser
   extracted the intended number. The earlier "verified to
   attempt what was asked" claim was too strong.
6. ~~Fresh-context independent review of the full system.~~ Done
   2026-04-16 by Opus 4.7. Recommendation: *Revise and re-review*.
   See `docs/reviews/system-review-opus47-2026-04-16.md`.
7. **Cross-lineage review of the system AND of the Opus 4.7
   review document** by Codex (`mcs-coord`) and Gemini
   (`mcs-coord-gemini`). Different training lineages will surface
   what same-family review missed; they are also well-positioned
   to weigh in on the design-vs-implementation faithfulness
   findings (#1, #2 in the review) since they signed off on the
   design wording in the fourth round.
8. Address review findings. Suggested order:
   - Decide and document the faithfulness gaps (#1, #2) with
     `decisions.md` entries.
   - Fix the implementation bugs (#3 Google error classification,
     #4 score parser, #5 WeightedVote tie-breaking, #6 empty-
     response handling).
   - Gate the placeholders (#7 `_best_model`, #8
     `_n_samples_for_b`, #9 `PHASE1_PRICING`) against
     pre-calibration use.
   - Address the variance issue (#11 temperature/seeds).
9. Then, in some order: benchmark adapters, experiment runner
   with budget-cap enforcement, run manifest schema, pre-kickoff
   power analysis, FakeClient unit tests (review #13), real
   within-step parallelism (review #10).


## Currently routed to

**Done 2026-04-19**: tie-break and parse-failure policy
pulled from the interpreter up to the AST as enum fields on
`WeightedVote` and `PickOne`. `TieBreakPolicy`
(RANDOM/FIRST/LAST) and `ParseFailurePolicy` (RANDOM/RAISE)
enums live alongside `ContextMode` and `Visibility` in
`src/ir/types.py`. Interpreter dispatches via
`_resolve_tie()` and `_recover_parse_failure()`. Seeded RNG
stays on the interpreter as a run-level resource. Defaults
preserve current behavior (RANDOM for both). New
`ParseFailure` exception for the RAISE case. 54 unit tests
passing (up from 49); mypy --strict clean on 24 files.
`docs/decisions.md` 2026-04-19 entry records the rationale.

Neither Codex nor Gemini caught this across four review
rounds; both treated tie-breaking as an implementation
detail. Scott's diagnosis was sharper: it's a design choice
that belongs at the AST level.

**Next phase: benchmark integration and runner work.** Both
round-4 reviewers signed off on the system as ready to
proceed. The next major items, in roughly the order the design
implies:

1. **Benchmark adapters.** Adapt SWE-bench Verified,
   LiveCodeBench, and BFCL to the executor. Each needs a way
   to (a) load task instances, (b) format the task as a
   `query_text` for `run()`, (c) score the macro-model's
   final answer (executable per-bucket: patch acceptance,
   test execution, BFCL executability), and (d) NOT leak
   ground truth into the query text (selector-as-oracle
   discipline applies at the adapter boundary).
2. **Experiment runner.** Drives `ExperimentSpec` end-to-end:
   instantiates clients, iterates conditions × tiers ×
   buckets × seeds, snapshots `client.calls` per run for
   per-task cost attribution, accumulates
   `InterpreterTelemetry` per task instance, enforces
   `BudgetTier` caps (truncating or excluding macro-models
   that would exceed), separates infra failures from
   capability failures, retries infra failures off-budget.
3. **Run manifest schema.** Per-run record of inputs and
   outputs: protocol AST, model assignments, prompt
   templates, seed, raw response trace, parse-failure /
   tie counts, dollar cost, success/failure verdict.
   Tracked in `docs/backlog.md`.
4. **Pre-kickoff power analysis** (operational gate from the
   experimental design). Estimate power for the Protocol ×
   Stratum interaction test against the pre-declared utility
   curve. If below 80%, the pre-declared middle-band fallback
   triggers automatically.

The real within-step parallelism gap (`ParGen`/`ParScore`/etc.
are sequential for-loops) is also still tracked as a future
fix; will matter at Phase 1 wallclock but doesn't block
benchmark-adapter or runner work.

### Historical: completed work routes (preserved for reference)

Below is the trail of what landed during the
operational-readiness phase. Kept for future reviewers.

**Operational-readiness work** from the round-2 reviews —
**Done 2026-04-16** across two commits:

- Commit `10a2f5b` (measurement quality + observability +
  tests): parser fixes with parse-failure telemetry,
  WeightedVote tie-breaking via seeded random, temperature
  made optional (omit to use vendor defaults), TracingClient
  step_type updated for PickOne and FuseWithCritiques,
  FakeClient-backed unit tests in `tests/` (28 tests).
- This commit (API reliability + Phase 1 gates): Google retry
  narrowed to 408/429/5xx + httpx network errors (other 4xx
  propagate as regular exceptions), empty-response →
  CapabilityFailure, CallRecord.status field with infra- and
  capability-failure logging, pre-calibration placeholders
  removed (best_model / n_samples_for_b / pricing required as
  explicit kwargs; `PHASE1_PRICING` renamed to
  `PHASE1_PRICING_DRAFT`). Additional tests in
  `tests/test_api_client.py` and `tests/test_phase1.py` (16
  tests).

44 unit tests total; mypy --strict passes on 24 files (21
source + 3 test). All round-2 blockers addressed. Ready for
round-3 cross-lineage review — both round-2 reviewers
forecasted `Proceed` as achievable once these operational
fixes landed.

### Historical: the faithfulness reconciliations (completed)

Below is the plan that drove the 2026-04-16 reconciliation work.
Kept here as the trail for future reviewers; all three items are
now done.

1. **Faithfulness reconciliations** — decide and record in
   `decisions.md`. Each is a code-or-design choice. The chosen
   pattern is **keep the existing component as a renamed building
   block, then add a new sibling that matches the design**, on
   the principle that the IR is the substrate for the broader
   protocol-inventory space and self-review / pointwise / fused-
   over-revised-drafts are all real macro-model shapes worth
   keeping pluggable.
   - ~~**D-family review semantics** (Codex #1, Gemini #2):~~
     **Done 2026-04-16.** Two commits: `82627d3` renamed the
     existing self-review nodes to `SelfReviseRound` /
     `SelfRounds`; the follow-up added `PeerReviseRound` /
     `PeerRounds` (cyclic 1-peer assignment, N >= 2), four
     `peer_review_*` prompt templates, and migrated D/D'/E.
     `decisions.md` updated. The E composition gap (meta fuses
     revised drafts, design specifies raw critiques) remains —
     see the E item below.
   - ~~**B/C aggregation** (Opus #1, Codex #2, Gemini #3):~~
     **Done 2026-04-16.** Added `PickOne(judge, drafts)`
     comparative-selection node; B and C migrated. ParScore +
     WeightedVote unchanged (still used by D/D' for
     confidence-weighted aggregation). Call counts: B(N=3) and
     C now N+1 calls instead of 2N. `decisions.md` 2026-04-16
     entry recorded.
   - ~~**E composition** (Opus #2, Codex #3, Gemini #4):~~
     **Done 2026-04-16.** Added `ParPeerReview` (peer review
     producing critiques only) and `FuseWithCritiques` (meta
     reads drafts + aligned critiques, writes fresh). New
     `condition_e` is design-faithful: ParGen → ParPeerReview
     → FuseWithCritiques. Previous variant kept as
     `condition_e_writers_revise_then_fuse`. Call count: 2N+1
     (was 3N+1). `decisions.md` 2026-04-16 entry recorded.
2. ~~**Design-doc scrub** (Codex #4, Gemini #6): remove the
   stale "selection rule is fixed to pick the candidate that
   passes the executable check" language from the IV section of
   `experimental-design.md`; remove the duplicated "What the
   matrix tests" section.~~ Done 2026-04-16. The IV paragraph on
   F (selection rule) was rewritten to align with the macro-model
   framing (selectors are per-condition aggregation steps, not a
   global rule; executable evaluator is never the aggregator);
   judge-information-regime sentence preserved as its own
   paragraph. The duplicate matrix-tests section (older "protocol
   families" wording) was deleted; the macro-model-vocabulary
   version remains. Done before the faithfulness reconciliations
   so next-round reviewers compare against single-source-of-truth
   design text.
3. **Implementation bugs** (small, local fixes):
   - Google retry classification — narrow to status-based
     (408/429/5xx), not exception-class-wide.
   - Score parser — extract last float in `[0,1]`, raise/log on
     parse failure rather than silently defaulting to 0.5.
   - `WeightedVote` tie-breaking — random with recorded seed, or
     pre-declared model preference order; emit telemetry on ties.
   - Empty-response handling — distinguish capability failure at
     the executor boundary; explicit telemetry.
   - `ApiClient.calls` (Codex #11) — record exhausted retries
     and per-provider failure rates, not only successful calls.
4. **Pre-calibration gates** for `_best_model()`,
   `_n_samples_for_b()`, `PHASE1_PRICING` — fail loudly until
   calibrated.
5. **Generation stochasticity** (Gemini #1, Opus #11): set
   `temperature > 0` for generation calls so homogeneous-pool
   conditions actually produce N distinct samples. This is
   pre-Phase-1-blocking, not just a "variance metric" issue.

Then re-review (a single round, against the updated artifacts),
then proceed to the originally-planned next-up items: benchmark
adapters, run manifest, budget-cap enforcement, power analysis,
FakeClient unit tests, real within-step parallelism.

### Source-of-truth pointers for the reconciliation work

- The three reviews:
  - `docs/reviews/system-review-opus47-2026-04-16.md`
  - `docs/reviews/system-review-codex-2026-04-16.md`
  - `docs/reviews/system-review-gemini-2026-04-16.md`
- The system being reviewed: as of commit `16e1f78`. Subsequent
  fixes will be obvious from `git log`.
- Design references:
  - `docs/research/experimental-design.md` (locked Phase 1
    design — needs scrub per item 2 above)
  - `docs/decisions.md` (macro-model framing, `Fuse` naming)
  - `docs/design/system-architecture.md` (layer structure, IR
    invariants)

### Explicitly NOT built (don't flag as missing)

- Experiment runner executing the spec against a benchmark.
- Benchmark adapters (SWE-bench, LiveCodeBench, BFCL).
- Run manifest schema (tracked in `docs/backlog.md`).
- Power analysis.
- `ContextMode.ACCUMULATED` real-client support.
- `ReviseFromMany` or advisory-synthesis IR nodes (names
  reserved in `docs/decisions.md`; no concrete use case yet).


## Blockers

None.
