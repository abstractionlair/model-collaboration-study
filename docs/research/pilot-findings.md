# Phase 1 Pilot — Findings (2026-07-24, rev. 2 after round-8 review)

Full condition matrix (A×3, B, C, D, D′, E) on the LiveCodeBench
test6 medium+hard pool, N=86 tasks, single seed, executable
scoring (mean_fraction primary). 688 (condition × task) pairs,
$62.00 total spend, ~30 h wall clock across two segments
(paused mid-run 2026-07-23 for the round-7 review patch set —
see Harness history below).

**Revision note.** Rev. 1 was audited by four independent
reviewers against the raw data (round 8:
`docs/reviews/conclusions-review-*-2026-07-24.md`, synthesis in
`docs/reviews/synthesis-round8-2026-07-24.md`). Every table
entry and CI reproduced; several *interpretive sentences* did
not survive and are corrected here. The most important
reviewer-contributed analyses (cap decomposition, random-pick
null for C, multiplicity corrections) are incorporated with
attribution.

**What this pilot is:** a descriptive, machinery-validation run
of the full Phase 1 matrix on a calibrated-then-invalidated
pool. **What it is not:** the pre-registered middle-band test
(N far below ~400/arm; pool no longer in any pre-registered
band for the true best subject; single seed; one benchmark; no
enforced budget tiers). All CIs below are marginal
(uncorrected) paired task-level bootstraps unless stated;
the pilot is descriptive, and no comparison family was
pre-registered.

## Headline results

| Condition | strict | mean_frac | $/task | $/solved* |
|---|---|---|---|---|
| A (gpt-5.4-mini) | 22/85 (.26) | 0.529 | $0.0035 | $0.014 |
| A (claude-haiku-4-5) | 19/86 (.22) | 0.545 | $0.0077 | $0.035 |
| **A (gemini-3-flash-preview)** | **60/86 (.70)** | **0.797** | $0.077 | $0.110 |
| B (gpt, n=8 + pick) | 34/86 (.40) | 0.617 | $0.036 | **$0.091** |
| C (pool drafts + pick) | 33/86 (.38) | 0.605 | $0.091 | $0.238 |
| D (hetero ReConcile) | 59/86 (.69) | 0.816 | $0.301 | $0.438 |
| D′ (gpt ×3 ReConcile) | 30/86 (.35) | 0.588 | $0.039 | $0.112 |
| E (hierarchical synth) | 37/86 (.43) | 0.638 | $0.166 | $0.385 |

\* dollars per strict-solved task (the design's headline
efficiency metric, strict-defined; fractional-equivalent
versions preserve the ordering).

Key paired comparisons (mean_frac; 95% marginal bootstrap CIs):
D−A(gemini) +0.019 [−0.068, +0.109]; on strict −0.012 [−0.116,
+0.093] (sign flips across metrics; both n.s.; win/loss/tie
14/15/57). E−A(gemini) −0.160 [−0.243, −0.078]. C−A(gemini)
−0.193 [−0.287, −0.099] (−0.314 on strict). B−A(gpt) +0.094
[+0.014, +0.175] (see conclusion 3 for multiplicity). D−D′
+0.228 [+0.136, +0.320].

### Conclusions

1. **No collaboration condition *demonstrated* a win over the
   best single model — and none was compute-matched against
   it.** C and E are significantly below A(gemini) while
   costing 1.2×/2.2× more, so their negatives are conclusive on
   this pool. D reached statistical indistinguishability while
   spending 3.9× — but the design's own Best-of-N discipline
   comparator (a matched-budget B or an inference-scaled A⁺ at
   D's cost) was not run, so D's matched-compute question is
   **unresolved, not negative**. The only ~cost-matched pair in
   the run (B vs D′, both ≈$0.038, both pure-gpt) is a
   structure contrast, not a collaboration-vs-single test.

2. **D's apparent parity with A(gemini) is concentrated
   entirely in the cap-strained subset — and is best read as
   "the ensemble rescues the bounded member's truncation
   failures."** (Reviewer analyses: Fable-r8, Sol-r8,
   Kimi-r8; verified.) On the 26 tasks where A(gemini)'s
   output sits ≥32k of its 32,768 budget, D−gemini = +0.228;
   on the other 60 tasks D−gemini = **−0.072**, and excluding
   just gemini's 11 truncated-to-zero tasks flips the aggregate
   to −0.060 [−0.141, +0.015]. A cap counterfactual (scoring
   gemini's pinned-zero rows at its uncapped hard-band mean)
   gives D−gemini ≈ −0.090. Under a deployment that actually
   imposes a 32k budget, D's rescue behavior is real value;
   as evidence that collaboration adds capability over an
   unbounded best model, it is a harness artifact.

3. **Repeat-sampling (B) shows the pilot's most promising
   positive — nominal only.** B−A(gpt) = +0.094 [+0.014,
   +0.175], unadjusted p≈.023–.027; under Holm/Bonferroni
   across the five reported comparisons it does **not** retain
   significance on the primary metric (Bonferroni-5 99% CI
   [−0.011, +0.201]), though it survives on strict (+0.141)
   and by sign test (32W/14L, p≈.011). It is also a single
   uncontrolled provider replicate (smoke-run A-columns moved
   by up to 0.5 mean_frac between repeats). Treat as promising
   and replication-worthy, not established. Note the Pareto
   point: B *undercuts the best single model on dollars per
   solved task* ($0.091 vs $0.110) — the one place any
   condition beats A(gemini) on the design's headline
   efficiency metric.

4. **C's judge performed at or below random selection.**
   (Kimi-r8; verified.) C's 0.605 sits at the **27th
   percentile of a random-pick null** over the three drafts
   (null mean 0.622 [0.566, 0.678]). The task-visible judge
   not only failed to find the +0.056 oracle headroom — it
   failed to match a coin. Selection quality is the measured
   bottleneck of the pick-based conditions and the single most
   actionable finding for protocol design. (Caveat: C picks
   among *fresh* drafts, not the A-column drafts, and unchosen
   candidates were not retained, so judge quality deeper than
   this null is unmeasurable from this run.)

5. **D vs D′ (+0.228) tracks pool composition; the pilot
   cannot decompose it further.** D ≈ A(gemini) and D′ ≈
   A(gpt)+0.06; the same-cost structure contrast (B vs D′) is
   +0.028 n.s. But swapping the pool also changed realized
   cost 7.7×, truncation exposure, and lineage — capability,
   diversity, and native reasoning spend are not separable
   here. Tie telemetry matters for D′: 20 weighted-vote ties
   (23% of its tasks) resolved by one seeded coin — an
   unmeasured single-seed sensitivity. (Rev. 1's "zero tie
   events" was wrong; 24 ties total, 4 in D.)

6. **The pool sits *above* the pre-registered easy band for
   the true best subject, so the strata hypothesis was not
   tested.** At 0.797 mean_frac (0.70 strict), the best
   subject is outside the declared 60–70% band. The observed
   pattern (C/E harmful, D ≈ 0) is qualitatively compatible
   with an extrapolation of the easy-band prediction, and is
   also overdetermined by the ceiling: with ≤5.6 points of
   selection headroom available, *any* mechanism would look
   neutral-to-harmful. Weak directional consistency, no more.

7. **The ceiling analysis, sharpened: the pool's true
   complementarity is ~zero.** Oracle best-of-pool over the A
   drafts = 0.854 vs gemini 0.797 (+0.056 [+0.022, +0.099]).
   Decomposed (Sol-r8/Kimi-r8; verified): headroom is +0.186
   on gemini's 26 cap-strained tasks and **+0.0004 on the
   other 60**. On tasks where the best model isn't
   artificially bounded, the pool contains essentially nothing
   the best model lacks. Scope: the ceiling binds
   one-draw-per-member selection (C); B's ceiling is over its
   own 8 draws; D/E operate on revised/fresh artifacts.

8. **Robustness direction, corrected.** Rev. 1 claimed all
   open instrument issues bias against the single model; the
   run's own data contradicts this for the dominant issue
   (Kimi-r8): the 32k cap suppresses *both* sides of the D
   comparison (D−gemini = −0.119 on D's 18 truncation-bearing
   tasks vs +0.055 on clean ones), and unsandboxed execution
   is roughly symmetric across conditions. What remains
   robust: the C and E negatives (deficits of 16–19 points
   dwarf any cap effect) and the B positive's direction.
   D-vs-best-single is unresolved in *both* directions.

### Objective-flip corollary (routing)

An **ex-post oracle router** — per task, the cheapest model
whose realized fraction ≥ gemini's — achieves 0.832 mean_frac
at **49% of all-gemini cost** (48/86 tasks routed to 10–20×
cheaper models). The argmax variant (cheapest among per-task
best) achieves 0.854 at 50%. Both are ground-truth-dependent
upper bounds; whether a deployable pre-hoc router approaches
them is untested. The same pool that offers nothing to
capability-seeking collaboration offers ~2× savings to
cost-seeking routing. See backlog: cost-side objective flip.

## Harness history and instrument caveats (load-bearing)

1. **Gemini truncation bug (fixed 2026-07-23).** Thinking
   tokens count against `max_output_tokens`; at the original
   shared 4096 cap Gemini's answers truncated mid-fence and
   thinking went unbilled. This invalidated the April
   calibration and contributed to the best-subject flip —
   though the flip **conflates the bug fix with the 2.5→3
   model swap** (April's gemini-2.5-flash scored 0.023 under
   the bug; no post-fix 2.5-flash measurement exists yet), so
   the bug's isolated role is not quantified. April's best
   subject on the adopted metric was haiku (0.606), not gpt.
2. **Gemini remained budget-bounded at 32,768 in this run and
   the bound binds** (~26/86 A(gemini) tasks within 2.5% of
   cap; ≥10 pinned at cap with score 0.00; 76 flagged
   truncated calls across C/D/E). Conditions share the same
   *per-call* cap but differ in number and role of Gemini
   calls, so truncation exposure is **not** equal across arms.
   The correct subject description is "gemini-3-flash at a 32k
   thinking+answer budget"; unbounded, its dominance would be
   larger (cap counterfactual ≈ 0.906).
3. **Round-7 patch set applied mid-run** (task-visible
   aggregation prompts, seeded candidate shuffle, AST score
   parse policy, truncation telemetry, provider-refusal class,
   one denominator rule). A-columns ran pre-patch but contain
   no aggregation/critique steps; B's 32 pre-patch rows were
   deleted and rerun; C/D/D′/E ran entirely post-patch.
4. **Known remaining holes (queued):** unsandboxed candidate
   execution with private tests readable (exploitation
   implausible here, unauditable post-hoc); no generation
   seeds (single provider replicate; contest-cluster
   bootstrap widens D−gemini to ≈[−0.093, +0.149] but leaves
   B positive and C/E negative); tier caps unenforced;
   contamination window for gemini-3 on test6 unchecked;
   candidate texts and per-test vectors not retained (blocks
   judge-quality and B-selection analyses deeper than the
   random-pick null).

## Failure accounting

One abort in 688 pairs: `abc396_f` under A(gpt) — OpenAI
moderation refusal (recorded pre-patch as `unexpected_error`;
semantically a provider refusal; excluded from denominators,
N=85 for A(gpt)). 76 truncated calls: 38 D, 23 E, 15 C
(A-columns predate the flag; see caveat 2). Zero infra-failure
aborts; zero score/pick parse failures; **24 weighted-vote
ties** (20 in D′, 4 in D), all resolved by the seeded RNG.

## Cost anatomy

Total $62.00: google $47.03 (76%), openai $9.83, anthropic
$5.15. Gemini thinking tokens dominate: D at $0.301/task runs
7.7× D′ ($0.039) with identical structure. Per-condition
$/task in the headline table.

## What follows

Pre-conditions for the confirmatory phase (tracked in
status/backlog/decisions): cap policy settled, then a
recalibration wave on the fixed harness **including
gemini-2.5-flash** (near-peer pool candidate; also isolates
the bug-vs-model-swap conflation in caveat 1) with truncation
≈ 0 verified per provider; complementarity-ceiling gate on
pool selection; pool expansion toward N≈400;
fractional-outcome power analysis + multiplicity
pre-registration; candidate-text and per-test-vector
retention; execution sandboxing; A⁺ allocation-sweep, router,
and frontier-judge arms; judge-quality work motivated by
conclusion 4 (C's at-or-below-chance selection).
