# Phase 1 Pilot — Findings (2026-07-24)

Full condition matrix (A×3, B, C, D, D′, E) on the LiveCodeBench
test6 medium+hard pool, N=86 tasks, single seed, executable
scoring (mean_fraction primary). 688 (condition × task) pairs,
$62.00 total spend, ~30 h wall clock across two segments
(paused mid-run 2026-07-23 for the round-7 review patch set —
see Harness history below).

**What this pilot is:** a descriptive, machinery-validation run
of the full Phase 1 matrix on a calibrated-then-invalidated
pool. **What it is not:** the pre-registered middle-band test
(N far below the ~400/arm power requirement; pool no longer
middle-band for the true best subject; single seed; one
benchmark). Claim limits per the round-7 reviews apply
throughout.

## Headline results

| Condition | strict | mean_frac | $/task | vs A(gemini), paired |
|---|---|---|---|---|
| A (gpt-5.4-mini) | 22/85 (.26) | 0.529 | $0.0035 | −0.268 |
| A (claude-haiku-4-5) | 19/86 (.22) | 0.545 | $0.0077 | −0.252 |
| **A (gemini-3-flash-preview)** | **60/86 (.70)** | **0.797** | **$0.077** | — |
| B (gpt, n=8 + pick) | 34/86 (.40) | 0.617 | $0.036 | −0.180 |
| C (pool drafts + pick) | 33/86 (.38) | 0.605 | $0.091 | −0.193 * |
| D (hetero ReConcile) | 59/86 (.69) | 0.816 | $0.301 | +0.019 (n.s.) |
| D′ (gpt ×3 ReConcile) | 30/86 (.35) | 0.588 | $0.039 | −0.209 |
| E (hierarchical synth) | 37/86 (.43) | 0.638 | $0.166 | −0.160 * |

Paired-bootstrap 95% CIs (10k resamples, per-task differences):
D−A(gemini) +0.019 [−0.068, +0.109]; E−A(gemini) −0.160
[−0.243, −0.078]; C−A(gemini) −0.193 [−0.287, −0.099];
B−A(gpt) **+0.094 [+0.014, +0.175]**; B−D′ +0.028 [−0.031,
+0.088].

1. **No collaboration condition beats the best single model at
   matched compute.** D achieves statistical parity with
   A(gemini) at 3.9× the dollar cost; on the design's headline
   efficiency metric (dollars per solved task: gemini $0.110 vs
   D $0.438) the single model wins decisively. E and C are
   significantly *below* the best single model despite costing
   2–1.2× more than it.
2. **The one significant positive: repeat-sampling.** B's
   +0.094 over its own base model (8 samples + task-visible
   same-model pick, at ~10× A(gpt)'s cost) is the pilot's only
   CI-excluding-zero gain — the variance-harvest mechanism
   works. B > D′ (same cost, same model, sampling vs ReConcile
   structure) is directionally positive (+0.028) but not
   significant at N=86.
3. **D vs D′ (+0.228) is dominated by pool composition, not
   structure.** With one member far stronger than the others,
   the "heterogeneity" comparison mostly measures Gemini's
   presence. The informative reading is D vs A(gemini): the
   ReConcile machinery neither destroyed the dominant member's
   contribution (C did: 0.605 from the same three drafts) nor
   added measurable value beyond it.
4. **Consistent with (not confirmation of) the strata
   hypothesis.** The pool sits in the easy band for the true
   best subject (0.797), where the pre-registered utility curve
   predicts collaboration ≈ neutral-to-harmful. That is what
   was observed. Underpowered as a test; the direction matches.

## The ceiling analysis (why a big win was arithmetically out of reach)

Per-task best-of-pool over the A drafts ("oracle") scores 0.854
vs the best single model's 0.797: **+0.056 recoverable headroom
for one-draw-per-member selection**, far below the
pre-registered +10pp effect. C realized −0.193 against a +0.056
ceiling — its judge recovered none of the available headroom.
The ceiling binds C only (B's ceiling is over its own 8 draws;
D/E operate on revised/fresh artifacts) but it frames the
matrix: on this pool, *picking well* was worth ≤5.6 points, so
only generation lift (revision/synthesis beating every original
draft) could have produced a large win, and none appeared.
Part of the measured ceiling is itself a truncation artifact
(see below), so true selection headroom is lower still.

**Objective-flip corollary (routing).** An oracle per-task
router achieves 0.832 mean_frac at **49% of all-gemini cost**
(48/86 tasks routed to 10–20× cheaper models). The same pool
that offers nothing to capability-seeking collaboration offers
2× savings to cost-seeking routing — the imbalance that breaks
one objective feeds the other. See backlog: cost-side
objective flip.

## Harness history and instrument caveats (load-bearing)

1. **Gemini truncation bug (fixed 2026-07-23).** Thinking
   tokens count against `max_output_tokens`; at the original
   shared 4096 cap Gemini's answers truncated mid-fence and
   thinking tokens went unbilled. This invalidated the April
   calibration ("gemini unusable on LCB" was substantially
   artifact), flipped the best-subject ranking when fixed, and
   moved the pool from middle-band to easy-band for the true
   best subject.
2. **Gemini remains budget-bounded at 32,768 in this run**, and
   the bound binds: ~26/86 A(gemini) tasks sit within 2.5% of
   the cap (≥10 pinned at cap with score 0.00 — truncation
   signature, silent because those rows predate the truncation
   flag); 76 truncated calls were counted live across
   B/C/D/D′/E. Every condition faces the same bounded Gemini,
   so within-run comparisons are internally consistent; the
   correct description of the subject is "gemini-3-flash at a
   32k thinking+answer budget." Unbounded, Gemini's rate — and
   its dominance — would be higher. All open instrument issues
   bias *against* the best single model or *toward* fake
   collaboration wins (cap suppresses Gemini; unsandboxed
   execution could only inflate scores), so the negative
   headline is robust in direction.
3. **Round-7 patch set applied mid-run** (task-visible
   PickOne/ParScore/E-review prompts, seeded candidate shuffle,
   AST-level score parse policy, truncation telemetry,
   provider-refusal class, one denominator rule). A-columns ran
   pre-patch but contain no aggregation/critique steps and are
   unaffected; B's 32 pre-patch (task-blind) rows were deleted
   and fully rerun; C/D/D′/E ran entirely post-patch.
4. **Known remaining holes (queued for confirmatory):**
   unsandboxed candidate execution with private tests readable
   (structurally confirmed; spontaneous exploitation implausible
   for these prompts, unauditable post-hoc since candidate
   texts are not retained); no generation seeds (single
   uncontrolled provider replicate); tier caps unenforced
   (B is realized-cost-matched to D′ only); pool contamination
   window for gemini-3 on test6 unchecked.

## Failure accounting

One abort in 688 pairs: `abc396_f` under A(gpt) — OpenAI
moderation refusal (provider_refusal class; excluded from
denominators). The same task did not trigger the filter in
gpt-bearing collaboration conditions (moderation is
stochastic). 76 truncated calls, all Gemini thinking-exhaustion
on hard tasks: 38 in D, 23 in E, 15 in C, 0 in A/B/D′ (A's
predate the flag; see caveat 2). Zero infra-failure aborts;
zero parse-failure or tie events surfaced in condition
telemetry.

## Cost anatomy

Total $62.00: google $47.03 (76%), openai $9.83, anthropic
$5.15. Gemini thinking tokens dominate: D at $0.301/task runs
~7.7× D′ ($0.039) with identical structure — the realized cost
of "heterogeneity" on this pool is mostly one vendor's
inference-time reasoning, billed as output. Per-condition
$/task: A $0.0035–0.077, B $0.036, C $0.091, D $0.301,
D′ $0.039, E $0.166.

## What follows

Pre-conditions for the confirmatory phase (tracked in
status/backlog/decisions): recalibration wave on the fixed
harness including gemini-2.5-flash (near-peer pool candidate)
with cap policy settled first and truncation ≈ 0 verified per
provider; complementarity-ceiling gate on pool selection;
pool expansion toward N≈400; fractional-outcome power analysis
+ multiplicity pre-registration; candidate-text retention and
per-test vectors; execution sandboxing; A⁺ allocation-sweep,
router, and frontier-judge arms as rival baselines.
