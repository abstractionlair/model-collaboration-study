# Project Status

**Last updated:** 2026-07-05

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

1. **README + dependency manifest for the featured profile page.** In progress on branch `career-9/readme`: add root `README.md` and `requirements.txt`, verify 155 tests pass, and file the delegation report.
2. ~~Build the experiment-spec layer.~~ Done — `src/experiment/`.
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

**Done 2026-04-24: per-bucket calibration + harder-subset
selection.** Both parts ran. Combined: 1,086 calls, $1.61,
~2h36m wall, no aborts. Full write-up at
`docs/research/calibration-findings.md`; raw log at
`data/mini_bench_runs/calibration-all-2026-04-24T23-37-45.json`;
resumable checkpoint at `data/calibration_checkpoint.json`.

**Headline:**

| Bench | Slice | N | gpt-5.4-mini | claude-haiku-4-5 | gemini-2.5-flash |
|-------|-------|---|--------------|------------------|------------------|
| lcb | easy | 26 | 1.00 | 0.96 | 0.85 |
| lcb | medium | 26 | **0.54** (0.67) | **0.46** (0.70) | 0.08 |
| lcb | hard | 60 | 0.25 (**0.48**) | 0.20 (**0.56**) | 0.00 |
| bfcl | simple_python | 50 | 1.00 | 1.00 | 0.98 |
| bfcl | multiple | 50 | 0.96 | 0.98 | 0.96 |
| bfcl | parallel | 50 | 0.88 | 0.90 | 0.94 |
| bfcl | parallel_multiple | 50 | 0.92 | 0.92 | 0.94 |
| bfcl | live_simple | 50 | 0.82 | 0.92 | 0.82 |

(Strict pass rate; mean_frac in parens where it differs. Bold
= in-band 0.45-0.55.)

**LCB is usable, BFCL is not.** LCB/medium hits the middle
band on strict for gpt and haiku; LCB/hard hits it on
mean_frac for both. The combined LCB medium+hard pool (N=86)
gives gpt 0.34 strict / 0.54 mean_frac — the cleanest natural
middle-band slice we have. Gemini-2.5-flash is essentially
unusable on LCB beyond easy.

BFCL is structurally saturated across all 5 currently-downloaded
categories at first-50: every cell is 0.82-1.00. Union-of-failures
subsets are 1-12 tasks per category; even at full 199-399 task
size, harder-subset selection cannot supply N≈400 middle-band
tasks per cell. **BFCL as currently constituted cannot run the
interaction test at 80% power**, and the saturation is a
property of the data not just N-too-small.

**Best-subject is bucket-specific.** Gpt dominates LCB; gemini
leads BFCL/parallel; haiku leads BFCL/multiple and live_simple.
Implication: build_phase1_conditions's single best_model arg
needs to be invoked once per bucket, not once globally.

**Decisions raised but not made (for Scott at kickoff):**
1. LCB pool expansion — pull additional `test5`/`test4` releases
   to reach N≈400 medium+hard pool. ~5 releases needed. Cheap.
2. BFCL: trigger middle-band fallback (pre-registered, supported
   by saturation evidence) vs. expand to `live_multiple`/`live_parallel`
   /`live_parallel_multiple` (uncertain payoff) vs. replace.
3. LCB scoring: strict pass vs. mean_fraction. Fractional gives
   more middle-band-shaped slices; load-bearing for power story.
4. Gemini on LCB: keep (critique-signal value), exclude, or
   replace.

**Tooling changes:** new `scripts/run_calibration.py` driver
with `--checkpoint` per-cell-resumable JSON sidecar. Mid-run
terminal kills no longer lose progress. No changes to adapters,
condition factories, or runner.

---

**Next session.** Three open items before Phase 1 kickoff
(LCB+BFCL data choices need Scott's call before any of these
become well-defined):

1. **SWE-bench Verified adapter** (multi-session, 2-3 sittings).
   Heaviest. Not blocked by calibration outcomes.
2. **Run-manifest schema** (~½ session). Foldable into any
   adapter session.
3. **LCB functional-testtype support** (~½ session). Only matters
   if LCB pool needs to expand significantly past medium+hard.

**Kickoff itself** is now blocked on Scott's calls in the four
decision items above, not on more work from me.

---

**2026-07-04: the four decisions are MADE** (see decisions.md same date):
LCB pool expands (~5 releases toward N≈400); BFCL dropped from Phase 1 with
the uniform middle-band fallback adopted phase-wide; LCB scores by
mean_fraction (test moves to test-case-level binomial or beta regression —
implementation note, not design change); gemini-2.5-flash replaced by
gemini-3-flash (recalibrate its cells).

Kickoff is decision-unblocked. Remaining pre-kickoff work, in rough order:
1. **SWE-bench Verified adapter** (multi-session, 2-3 sittings) — unchanged.
2. **Run-manifest schema** (~½ session) — unchanged.
3. **LCB pool pull** (~5 test5/test4 releases) + **gemini-3-flash
   recalibration run** (new; cheap).
4. LCB functional-testtype support is likely MOOT under the chosen path
   (pool grows within medium+hard; no expansion past those test types).

Work-graph: mcs-1 tracks this; the blocking decision-packet node mcs-2 is
resolved.

---

---

**Investigated 2026-04-22: subject-pool swap to weaker variants
(not adopted).** Both BFCL-widen and LCB-validation sessions
surfaced the same "no headroom" pattern: the best Condition A
run was at or near 100%. Initial proposal was to drop one
capability tier on each subject -- `gpt-5.4-nano-2026-03-17`,
`gemini-3.1-flash-lite-preview`, `claude-3-5-haiku-20241022` --
to break the ceiling.

**Probed each ID against the live API.** Two passed
(`gpt-5.4-nano-2026-03-17`, `gemini-3.1-flash-lite-preview`).
The Anthropic side returned 404 on every Haiku 3.x variant
tried (`claude-3-5-haiku-20241022`,
`claude-3-5-haiku-latest`, `claude-haiku-3-5*`,
`claude-3-haiku-20240307`, `claude-haiku-3*`). Anthropic's
account-level model listing and current pricing page both
confirm: Haiku 4.5 is the smallest current Claude. The
"Haiku 3.x still listed on the pricing page" recollection
was out of date.

**Three options surfaced:** (1) asymmetric pool -- keep
Haiku 4.5, downgrade only the other two; (2) drop Anthropic
from the small pool, replace with a different vendor's small
model; (3) stop trying to weaken the subjects and instead
**select harder within-bucket task subsets** -- the
calibration step the design's "Task difficulty strata"
section already calls for.

**Decision: option 3.** Saturation is a task-selection
problem, not a subject-capability problem; the design
already names the mechanism for fixing it. Options 1 and 2
were easier code edits but would have changed what "best
subject" means partway through the project, with cascading
effects on the heterogeneity / pool-pricing arguments. No
code changes from this investigation; the current pool
(`gpt-5.4-mini`, `claude-haiku-4-5`, `gemini-2.5-flash`)
stays. The Gemini 2.5 → 3 stale-anchor question is parked
for the same reason -- jumping to Gemini 3 Flash would
*worsen* saturation (more capable than 2.5), and we have
no need to touch the model IDs while we're addressing the
ceiling via task selection instead.

Per-bucket calibration (already routed for the next
session) is now scoped to also include **harder-subset
selection**: for each bucket, find the within-bucket subset
where the best subject lands near the target middle band
(45-55% one-shot success). Concretely: BFCL needs
high-difficulty `parallel_multiple` subsets and the harder
`live_*` categories yet to be added; LCB needs the
`difficulty="hard"` filter exercised at meaningful N.

---

**Done 2026-04-22: LiveCodeBench adapter.** Second Phase-1
benchmark adapter. LCB is the first Phase-1 bucket to use
**fractional scoring** (n_private_tests_passed / n_total); BFCL
and HumanEval are both binary. 155 tests total (up from 131;
+24 new LCB tests). mypy `--strict` clean on the new files.

**Scope of v1:** supports **stdin testtype only** (AtCoder and
CodeForces-sourced problems). Functional testtype (LeetCode
starter-code + `assert f(x) == y`) is filtered out at load time
and tracked as follow-on work. Recent LCB releases
(release_v5 onwards) are stdin-dominated; test6 is 112 stdin-only
out of 175 total.

**Security call on binary-serialised payloads:** LCB wraps
`private_test_cases` in a base64 + zlib + Python-native-binary
+ JSON chain. Decoding the native-binary layer executes
arbitrary code at load time. The decode call is confined to
`scripts/download_livecodebench.py`, which runs once at the
trust boundary (user-invoked, against HuggingFace's signed CDN)
and rewrites records as clean JSON. The runtime adapter
(`src/experiment/benchmarks/livecodebench.py`) never touches
that decode path -- it only reads JSON produced by the fetcher.
This moves the exploit surface from every benchmark run to a
single one-shot trust boundary. The alternative (install the
`datasets` library) was rejected because it hides the same
decode call behind a library boundary rather than eliminating
it.

**Files:**
- `src/experiment/benchmarks/livecodebench.py` -- `LiveCodeBenchBench`
  implementing the `Benchmark` protocol. Subprocess execution
  per private test with configurable wallclock timeout (default
  10 s); whitespace-tolerant stdout comparison (rstrip per line
  + strip trailing blanks) matching competitive-programming
  judge conventions.
- `scripts/download_livecodebench.py` -- one-time fetcher.
  Selectable release (default: `test6`, the smallest and most
  contamination-resistant), caches raw upstream JSONL under
  `data/livecodebench/.raw/`, emits clean JSONL under
  `data/livecodebench/` (gitignored). Both idempotent.
- `scripts/run_livecodebench.py` -- validation driver, same
  shape as `run_bfcl.py` / `run_humaneval.py`. Reports `Full
  pass` (strict) and `Mean frac` (fractional-aware) summary
  columns.
- `tests/test_benchmarks_livecodebench.py` -- 24 tests: output
  normalisation, code extraction, end-to-end scoring (all-pass
  / all-fail / partial / runtime-error / timeout / no-code),
  task iteration, task_id / difficulty filters, no-leak-of-
  private-tests, functional-record skipping, error paths.
  Real `python3` subprocess execution against hand-authored
  programs -- no mocking of execution.

**End-to-end validation (test6, 3 tasks x 5 conditions, ~8 min, $0.18):**

| Condition | Full pass | Mean frac | Dollars |
|-----------|-----------|-----------|---------|
| A (gpt-5.4-mini) | 3/3 | 1.000 | $0.010 |
| A (claude-haiku-4-5) | 2/3 | 0.775 | $0.017 |
| A (gemini-2.5-flash) | 2/3 | 0.667 | $0.002 |
| D (hetero, 1 round) | 2/3 | 0.667 | $0.084 |
| E (hetero, meta-synth) | 2/3 | 0.775 | $0.063 |

No aborts, no infra failures, all three providers working.
Fractional scoring surfaces correctly -- the failing tasks
report non-trivial pass fractions. Cost-per-condition matches
per-node call-count predictions. Log at
`data/mini_bench_runs/livecodebench-test6-2026-04-22T00-18-02.json`.

**Early finding (tiny N, do not overinterpret):** on these 3
tasks, D and E did not outperform the best Condition A
(gpt-5.4-mini at 100%). Same "no headroom when a subject model
is at ceiling" pattern as BFCL's widen session. A meaningful
comparison needs both larger N and a within-difficulty subset
that lands near 50% for the best subject -- i.e. the calibration
step the power-analysis write-up flagged as a kickoff
prerequisite.

---

**Done 2026-04-21: pre-kickoff power analysis.**
`analysis/power_analysis.py` simulates the pre-registered
Protocol × Stratum interaction LRT (binomial GLM, 2-df
interaction term) against the pre-declared utility curve across
a grid of N per cell. Calibration verified under null curves
(type-1 ≈ α at 2,000 sims). Write-up in
`docs/research/power-analysis.md`; raw grid in
`analysis/power_results.json`; mypy `--strict` clean; 131 tests
still passing.

**Headline numbers:**
- **Interaction test reaches 80% power at N ≈ 425 task
  instances per stratum per protocol** (2,000-sim grid;
  refined to 4,000 sims around the threshold).
- **Middle-band fallback test reaches 80% power at N ≈ 388
  per arm** (analytical) / 400 per arm (simulated). Simulation
  and Fleiss-style analytical agreed to within MC noise.
- Per-stratum diagnostics: easy-band 5 pp effect is
  under-powered at realistic Phase 1 N (needs ~1,500+ per arm
  for 80%); hard-band 0 pp stays at α as a calibration check.

**Operational recommendation (non-binding, for kickoff):**
trigger the middle-band fallback for Phase 1 as a whole. The
binding argument is structural, not budgetary: SWE-bench
Verified has 500 instances total (~167 per stratum if
stratified into thirds), which is well below the 425 needed
for 80% interaction power, so the fallback triggers for
SWE-bench on instance availability alone. Running
interaction-test on BFCL/LCB while SWE-bench runs the
fallback fragments the primary pre-registration; uniform
fallback is cleaner. Write-up names this as a kickoff
decision, not an in-repo commitment.

**Not decided by this analysis (deferred to kickoff):**
- Per-bucket calibration of absolute rates onto the subject
  models (one-shot pass rates to confirm the middle band
  actually lands near 0.50 for BFCL / LiveCodeBench /
  SWE-bench on the three subjects).
- Multiplicity correction across the ~10
  protocol-comparison × tier cells per bucket (Bonferroni
  raises N per arm to ~620 analytically; FDR lands
  somewhere between 400 and 620).

**Not added:** a `decisions.md` entry for the fallback. The
fallback outcome is an operational call Scott should make at
kickoff once the dollar ceiling and per-bucket calibration
are in hand; committing now would pre-empt the calibration
evidence.

---

**Next session — pick one of four remaining before Phase 1 kickoff.**
LCB adapter done this session. Four open items:

1. **Per-bucket calibration + harder-subset selection**
   (~1 session, expanded scope). Two parts:
   (a) Run each of BFCL / LCB at meaningful N (30-50 tasks
   per difficulty label) on each of the three subject
   models, see where one-shot pass rates actually land.
   (b) For each bucket, identify the within-bucket subset
   where the best subject lands near the middle band
   (45-55% one-shot success). This is the design's "Task
   difficulty strata" mechanism, escalated this session
   from a queued item to the active fix for the saturation
   problem. Direct evidence both buckets need it: BFCL
   100% on most categories at small N (widen session); LCB
   gpt-5.4-mini 100% on 3 tasks (LCB validation). Without
   the middle band actually existing in our data, the
   interaction / fallback decision can't be made. Reuses
   the existing adapters; the work is a bigger run, a
   subset-selection pass, and a write-up.
2. **SWE-bench Verified adapter** (multi-session, 2–3
   sittings). Heaviest: x86_64 + Docker + 120 GB + 16 GB RAM
   + 8 CPUs. Plan explicit session-1 scope ("one instance
   end-to-end, defer the rest"). Verify host has Docker +
   disk before starting.
3. **Run-manifest schema** (~½ session). Persists per-run:
   protocol AST (serialised), model assignments, prompt
   templates, seed, full trace, costs, verdict. Foldable
   into any adapter or calibration session.
4. **LCB functional-testtype support** (~½ session). Extend
   the adapter to handle LeetCode-sourced problems with
   starter_code + `assert f(x) == y`-style tests. Not a
   blocker for Phase 1; only matters if the stdin-only
   subset proves too small or stratum-thin.

Opus 4.7's recommendation for the next session (not binding):
**(1) per-bucket calibration**. Scott's 2026-04-21 guidance
was explicit that speculative sensitivity on hand-picked
anchors should wait until real subjects-on-each-bucket data
exists. The adapters and the power analysis have now made
that data a one-session run away. Doing it next gives the
Phase 1 kickoff decision (middle-band fallback yes/no,
per-stratum N) something real to push against, instead of
just more adapters stacked on top of untested utility-curve
assumptions. SWE-bench is still the biggest ask; the
run-manifest schema folds cleanly into a calibration session.

---

**Done 2026-04-21: widen BFCL categories.** `BFCLBench` now
covers five categories via a `category=` parameter:
`simple_python` (original), `multiple`, `parallel`,
`parallel_multiple`, `live_simple`. Single-call categories
(`simple_python` / `multiple` / `live_simple`) go through the
existing `_check_simple_call`; multi-call categories (`parallel` /
`parallel_multiple`) go through a new `_check_parallel_no_order`
ported from upstream's `parallel_function_checker_no_order`. A
second extractor `_extract_function_calls` handles JSON arrays of
`{name, arguments}` objects for the multi-call path.

**Empirical finding from this session's validation:** 100%
ceiling confirmed across all new categories at small N.
`multiple` 9/9, `parallel` 9/9, `parallel_multiple` 30/30,
`live_simple` 30/30 on Condition A. Gemini's round-5 warning is
directly validated — frontier models one-shot BFCL across the
board. Phase 1 tool-use stratum needs either a harder within-BFCL
subset (high-index `parallel_multiple`, or `live_parallel_*` once
added) OR much larger N OR both.

**One unexpected finding from D+E validation on `parallel`:**
Condition A passed 9/9, but Condition D (3-model, 1-round peer
revision) passed only 2/3. The failure was on
`parallel_2::calculate_resistance`: the schema declares
`resistivity` as a string enum (`'copper'` / `'aluminum'`), and
each A-run correctly emitted the string label, but D's final
revision emitted `resistivity: 2.82e-08` — aluminum's real-world
physics constant in ohm-meters. The scorer rejected it as
wrong-type per upstream semantics.

**Codex's widen-review (below) traced the mechanism concretely:**
D's revise template `_REVISE_USER` at `src/experiment/prompts.py:131`
takes only `{critique, draft}`; the revise call site at
`src/executor/interpreter.py:276–282` passes only those two.
The original task/schema is **not in the prompt** when the
writer revises. So a schema-violating but authoritative-sounding
critique has no anchor to resist. E's fuse prompt
(`_FUSE_USER`, line 138) starts with `Task:\n{query}\n\n` — E
has the task in-context during synthesis; D does not. This
explains why all three A runs (which have the task) passed,
while D (which doesn't, during revise) failed.

Gemini's complementary framing: this is exactly the
"authoritative deception / over-correction" failure mode the
study should measure. Both readings compatible. The actionable
piece is Codex's: prompt-template context discipline is an
open design choice that this study should make deliberately,
not inherit accidentally. Tracked as routed work below.

**Round-6 cross-lineage reviews landed 2026-04-21:**
- `docs/reviews/bfcl-widen-review-codex-2026-04-21.md` — Proceed,
  with the `parallel_2` context-loss finding above.
- `docs/reviews/bfcl-widen-review-gemini-2026-04-21.md` — Proceed,
  with "power analysis is now the immediate unblocker."

**Prompt-context fix landed 2026-04-21** in response to the
Codex finding. `_REVISE_USER` now starts with "The original
task was:\n{query}" (was `{critique, draft}` only); the three
`revise_user.format(...)` call sites in
`src/executor/interpreter.py` now pass
`target.production_query`. `reconcile()` now uses
`ALL_VISIBLE` (was `PEERS_GROUPED`), so the peer reviewer in D
sees the task alongside the target draft and peer drafts.
Re-validation on `parallel_2::calculate_resistance`: D now
1/1 (was 0/1 before the fix); A and E unchanged. `PEERS_GROUPED`
variant remains available in the IR for future ablation work.
`decisions.md` 2026-04-21 entry records the rationale. 131
tests pass; mypy `--strict` clean.

131 tests total (18 new BFCL tests: 4 on `multiple`, 8 on
`parallel`, 1 on `parallel_multiple`, 1 on `live_simple`, 4 on
`_extract_function_calls`, plus direct `_check_parallel_no_order`
coverage). mypy `--strict` clean on the updated adapter.

---

**Next session — pick one of four remaining.**

Four items remain before Phase 1 kickoff:

1. **Pre-kickoff power analysis** (~half session). Operational
   gate from `experimental-design.md`. Simulate Protocol ×
   Stratum interaction test against the pre-declared utility
   curve (easy −5pp, middle +10pp, hard 0pp) at actual Phase 1
   N per stratum × condition × tier. If <80% power,
   middle-band fallback triggers automatically per locked
   design. Self-contained — pure `scipy`/`statsmodels`, no
   external deps. **Escalated from #2 to #1 by this session's
   finding:** 100% ceiling confirmed empirically across all
   widened BFCL categories; both widen reviewers agree this is
   now the clearest next unblocker.
2. **LiveCodeBench adapter** (~1 session). Coding tasks with
   executable tests, no Docker. Middle-weight; sits between
   BFCL and SWE-bench in effort. Reuses the `Benchmark`
   protocol shape.
3. **SWE-bench Verified adapter** (multi-session, 2–3 sittings).
   Heaviest: requires x86_64 + Docker + 120 GB storage + 16 GB
   RAM + 8 CPU cores. Plan an explicit session-1 scope
   ("one instance end-to-end, defer the rest"). Verify host
   has Docker + disk before starting.
4. **Run-manifest schema** (~half session). Persists per-run:
   protocol AST (serialised), model assignments, prompt
   templates, seed, full trace, costs, verdict. Can fold into
   any of the above.

**Residual BFCL work** (not routed as a session, likely folds
into #1 or a future calibration pass):
- Add `live_multiple`, `live_parallel`, `live_parallel_multiple`.
  All three reuse existing scorers; only data fetch + dispatch
  wiring needed.
- Investigate high-index `parallel_multiple` tasks to see if
  the 100% ceiling breaks at higher difficulty within the
  category (cheap experiment: run N=30 on `parallel_multiple`
  tasks 100+).

Opus 4.7's recommendation for the next session (not binding):
**(1) power analysis** is now the clearest unblock for Phase 1
kickoff — the widening session confirmed Gemini's ceiling
empirically, so we need to know the operational N story before
committing further bench work. LiveCodeBench is the natural
technical follow-on from the two adapters that just landed, but
doesn't answer a current strategic question.

---

**Done 2026-04-21: BFCL adapter (simple_python category).**
First Phase-1-matrix benchmark adapter. Proves the
`Benchmark` abstraction holds for a non-coding task shape.

**Round-5 review (BFCL adapter) landed 2026-04-21.** Codex
recommended Revise-and-re-review on one concrete scorer bug
(verified: `array[dict]` params routed to the list scorer
instead of a recursive per-dict checker — broke real tasks
like `simple_python_96::database.query`). Gemini recommended
Proceed but flagged that 100% ceiling on simple_python means
D/E have no headroom; must widen BFCL categories before
Phase 1 kickoff.

**Fix landed in follow-up commit (`3f9ddb7`):**
`_value_matches_list_of_dicts` helper ports upstream's
`list_dict_checker` (position-aligned per-dict match against
per-alternative accepted lists). `_check_simple_call`
dispatches `array[dict]` to the new helper; other list-of-X
paths unchanged. Five new tests cover simple_python_96's
shape + wrong-position, wrong-length, missing-required-subfield,
multi-alternative. Real-data check: both array[dict] tasks in
the corpus (`simple_python_96`, `simple_python_335`) score
correctly now. Two deliberate deviations from upstream (exact
dotted-name match, `is_variable` branch skipped) documented
inline in the module docstring.

**Round-5 re-review 2026-04-21: Codex → Proceed.** "The
`array[dict]` fix addresses the concrete faithfulness bug …
The five new tests are the right ones for this fix … From my
previous list, the remaining concrete concerns are now
correctly downgraded to explicit deviations rather than hidden
mismatches." One non-blocking test gap noted: no unit test for
optional-array[dict] omission (the `[""]` sentinel case on
`simple_python_335::deck`). Added in the subsequent commit —
test mirrors the 335 shape and confirms model omission passes.

113 tests total (up from 107 at start of session); mypy
`--strict` clean.

- `src/experiment/benchmarks/bfcl.py` — `BFCLBench`
  implementing the protocol. AST scorer ported from Gorilla's
  `simple_function_checker`: function-name match, required-
  params present, strict type check (bool/int distinguished),
  value match against accepted-values list with BFCL's
  string-normalisation rules (strip `[ ,./-_*^]`, lowercase,
  single→double quotes), list/dict variants with the same
  normalisation, `""` sentinel for optional-omission. Skipped
  the `is_variable` case (rare when models are told to emit
  concrete-value JSON).
- `scripts/download_bfcl.py` — idempotent fetcher for the
  JSONL files from the Gorilla repo. Data lands in
  `data/bfcl/` (gitignored). Installing the official
  `bfcl-eval` PyPI package was the first path tried, but it
  pins `numpy==1.26.4` which has no Python 3.13 wheel;
  vendoring just the data avoids the full evaluator dep.
- `scripts/run_bfcl.py` — driver mirroring
  `run_humaneval.py`: Condition A × each subject model + D +
  E, writes a JSON log to `data/mini_bench_runs/`.
- `tests/test_benchmarks_bfcl.py` — 33 tests covering
  normalisation, extraction (fenced / bare / OpenAI-style /
  prose-surround / invalid), scorer (happy path, wrong name,
  missing required, unexpected param, wrong value, wrong
  type, bool/int confusion, int→float coercion, list, dict,
  optional-omission). Hand-authored in-test data — real BFCL
  files don't need to be downloaded to run the suite.

**Validation:** 3 tasks × 5 conditions (A × 3 models + D + E),
15/15 pass, $0.05, ~3 min. Full telemetry clean (no parse
fails, no ties, no infra/capability failures). 66 total calls;
cost-per-condition matches the per-node call-count predictions
(A=1/task, D=12/task with three-model cycle, E=7/task with
meta synthesis). Log at
`data/mini_bench_runs/bfcl-2026-04-21T12-20-49.json`.

Total test count: **107** (33 new BFCL tests, up from 74
before this session); mypy `--strict` clean on the new files.

---

**Next session — pick one of two remaining.** BFCL (option 1)
landed; power analysis and SWE-bench still open. Same
trade-offs as before:

- **Pre-kickoff power analysis** (~half session) — pure stats,
  self-contained, unblocks calibration-time decisions about
  task-instance counts. Uses pre-declared utility curve (easy
  −5pp, middle +10pp, hard 0pp) at Phase 1 N per stratum ×
  condition × tier. If <80% power, middle-band fallback
  triggers automatically per locked design.
- **SWE-bench Verified adapter** (multi-session) — heaviest;
  needs x86_64 + Docker + 120 GB + 16 GB RAM + 8 CPUs. Plan
  for 2–3 sittings with an explicit session-1 scope ("one
  instance end-to-end").

`LiveCodeBench` is a natural follow-on to BFCL (coding tasks
with executable tests, no Docker) — smaller than SWE-bench,
larger than BFCL. Pick it up after either of the above.

**Run-manifest schema** is a half-session follow-on that can
be folded into any adapter session. Needs to persist per-run:
protocol AST (serialized), model assignments, prompt
templates, seed, full trace, costs, verdict.

---

**Pick-one routing (preserved for reference).** Framework
foundation is green (all four review rounds Proceed; end-to-end
HumanEval + BFCL validation passed; all three providers
working).

1. **BFCL adapter** (~1 session) **— done 2026-04-21.** Berkeley Function Call
   Leaderboard: tool-use benchmark, executability-based
   scoring (valid JSON matching declared tool surface). No
   Docker, no code execution in subprocess — lightest of the
   three Phase 1 benchmarks. Shape: implement `Benchmark`
   protocol, format tool surface in query, parse
   function-call JSON from response, compare against
   reference. Good first adapter — proves the abstraction
   holds for a non-coding task shape.

2. **Pre-kickoff power analysis** (~half a session). The
   operational gate from `experimental-design.md`: simulate
   Protocol × Stratum interaction test against the
   pre-declared utility curve (easy −5pp, middle +10pp, hard
   0pp) at the actual Phase 1 N per stratum × condition ×
   tier. If <80% power, the middle-band fallback triggers
   automatically per the locked design. Self-contained —
   pure statistics work with `scipy`/`statsmodels`, no
   external deps. Unblocks calibration-time decisions about
   task-instance counts.

3. **SWE-bench Verified adapter** (multi-session,
   2–3 sittings). Heaviest of the three: requires x86_64 +
   Docker + 120 GB storage + 16 GB RAM + 8 CPU cores (per
   design). Shape: official `swebench` harness drives
   container-per-instance test execution. Tricky bits:
   query formatting (how much repo context to pass),
   patch extraction from model responses (diff vs. full
   file), scoring (propagating test results through the
   Docker boundary). Verify host has Docker + disk before
   starting. Probably best tackled with an explicit
   budget-for-session-1 plan ("get one instance to run
   end-to-end, defer the rest").

`LiveCodeBench` is also in the Phase 1 matrix but isn't
listed here — it sits between BFCL and SWE-bench in effort
(coding tasks with executable tests, no Docker). Pick it up
after BFCL if the adapter shape is holding up.

**Run-manifest schema** is a small follow-on that can be
folded into whichever adapter session or done separately —
it's ~half a session on its own. Needs to persist per-run:
protocol AST (serialized), model assignments, prompt
templates, seed, full trace, costs, verdict.

---

**Done 2026-04-21 (follow-up)**: Google key fallback wired.
Vault stores the generative key under
`GOOGLE_EMBEDDING_API_KEY` / `GEMINI_EMBEDDING_API_KEY`
deliberately (prevents the `gemini` CLI from auto-switching);
verified end-to-end that it's a generic key. Framework now
reads the canonical names first, then falls back to the
`_EMBEDDING_` names (`ApiClient._get_google`,
`run_humaneval.py::available_providers`,
`smoke_test.py::available_models`). Documented in CLAUDE.md §
"API credentials" and in my project memory
(`reference_vault.md`). Three new tests in `test_api_client.py`
pin the fallback priority. Validation re-run with all three
providers live: 3 HumanEval tasks × 5 conditions (A × 3
models + D + E), 15/15 pass, $0.09, ~4 min.

**Done 2026-04-21**: framework-validation run against a
HumanEval subset. Built a minimal `Benchmark` abstraction
(Task / ScoreResult / Benchmark) that SWE-bench /
LiveCodeBench / BFCL adapters will share, a HumanEval
adapter using the official `human-eval` package, a minimal
runner at `src/experiment/runner.py`, a driver at
`scripts/run_humaneval.py`, and 11 new unit tests.

**Results (10 tasks, 4 conditions, ~5 min, $0.20 total):**

| Condition | Pass | $ | Calls | Avg |
|-----------|------|----|-------|-----|
| A (gpt-5.4-mini) | 10/10 | $0.008 | 10 | 1.2s |
| A (claude-haiku-4-5) | 10/10 | $0.011 | 10 | 1.7s |
| D (hetero, 1 round) | 10/10 | $0.098 | 80 | 15.1s |
| E (hetero, meta-synth) | 10/10 | $0.080 | 50 | 13.7s |

One tie-break event in D (seeded-random resolved as
designed). No infra / capability / parse failures. Call
counts match architecture-doc predictions exactly.

**One real bug surfaced and fixed during the run:** OpenAI's
GPT-5 family rejects `max_tokens` as unsupported; switched
`_call_openai` to `max_completion_tokens`. Smoke test's job.

Full write-up in `data/mini_bench_runs/README.md`.

Not a research benchmark — HumanEval stays out of the Phase
1 matrix (SWE-bench / LiveCodeBench / BFCL). Framework
validation only.

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
