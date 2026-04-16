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

**Three independent system reviews complete on 2026-04-16:**
- `docs/reviews/system-review-opus47-2026-04-16.md` (Opus 4.7,
  fresh-context)
- `docs/reviews/system-review-codex-2026-04-16.md` (Codex /
  GPT-5.4, `mcs-coord`)
- `docs/reviews/system-review-gemini-2026-04-16.md` (Gemini 3.1
  Pro, `mcs-coord-gemini`)

**All three converge on *Revise and re-review*.** Cross-lineage
triangulation surfaced two findings the same-family Opus review
missed:

- **Codex's D-family catch.** `ReviseRound` in the executor is
  self-review-informed-by-peers, not peer review of each draft by
  1–2 peers as the design specifies. Larger faithfulness gap than
  Opus 4.7's B/C and E findings; reframes those alongside it.
- **Gemini's temperature-collapse catch.** At `temperature=0`,
  `ParGen` on a homogeneous pool produces N identical drafts.
  Conditions B and D' mechanically collapse to single-pass
  baselines. Invalidates the matched-budget controls those
  conditions are supposed to provide.

Plus Codex's design-doc internal-inconsistency catch: the
Independent Variables section of the locked
`experimental-design.md` still has stale "executable scoring is
the selection rule" language contradicting the macro-model
framing. Needs a scrub before further faithfulness review can
work cleanly.

Architectural foundation (IR / executor / spec layer split,
selector-as-oracle discipline in code) is sound across all three
reviewers. Next round is targeted reconciliation, not rethink.


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

**Reconciliation work based on the three review files.** Suggested
order (per all three reviewers' converged recommendations):

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
   - **E composition** (Opus #2, Codex #3, Gemini #4): **Next.**
     Add `ParPeerReview` (peer review producing critiques only,
     no revision; cyclic 1-peer assignment) and
     `FuseWithCritiques` (meta reads drafts + aligned critiques,
     writes fresh). Rename existing `condition_e` to
     `condition_e_writers_revise_then_fuse`; new `condition_e`
     uses the new nodes per the design.
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
