# Review: Pilot conclusions given the data (round 8)

**Reviewer:** GPT-5.6 Sol  
**Date:** 2026-07-24  
**Artifacts reviewed / analyses run:** `docs/status.md`; `docs/research/pilot-findings.md`; `docs/research/experimental-design.md`; `docs/reviews/synthesis-round7-2026-07-23.md`; `docs/research/power-analysis.md`; the complete pilot JSON; the April calibration JSON; all three pilot smoke logs; LiveCodeBench test6 metadata. I reproduced condition means, costs, paired differences, marginal bootstrap intervals, oracle ceilings, and router arithmetic; ran paired t/McNemar sensitivity tests, multiplicity adjustments, task- and contest-cluster bootstraps, difficulty-stratified summaries, cap-proxy analyses, private-test-weighted sensitivity analyses, Pareto comparisons, and April-calibration ceiling calculations.

## Summary assessment

The descriptive scores and costs are reproducible, but several central interpretations are not publication-safe. Most importantly, the pilot supports “no demonstrated compute-matched collaboration win,” not “no collaboration beats the best model at matched compute”; D never received the required matched B or A⁺ comparator.

## Claim-by-claim verdicts

1. **UNSUPPORTED — “No collaboration condition beats the best single model at matched compute.”** Only B and D′ are approximately cost-matched ($0.036 versus $0.039 per task), and B is directionally better by +0.028. C and E are dominated by cheaper A(gemini), but D scores +0.019 at $0.301/task versus Gemini’s $0.077/task and has no $0.301 single-model scaling baseline; therefore the matched-compute result for D is unknown, not negative.

2. **OVERCLAIMED — “D achieves statistical parity with A(gemini) at 3.9× cost.”** A failure to reject zero is not evidence of parity or equivalence: +0.019 [−0.068, +0.109] permits material harm or benefit, and no equivalence margin or TOST was specified. The metric direction also changes: D is +1.9 points on task-equal mean fraction, but −1.2 points on strict success (59/86 versus 60/86; paired discordances 10 versus 11, exact McNemar \(p=1.0\)).

3. **OVERCLAIMED — “B’s +0.094 over its own base model is the pilot’s only significant positive.”** The marginal paired result is reproducible, but the +0.094 point estimate appears to retain the excluded A(gpt) refusal as a zero; complete-case pairing gives +0.093 with essentially the same marginal interval. Among five reported comparisons, a paired-t sensitivity gives unadjusted \(p=.027\), Holm-adjusted \(p=.082\), and Bonferroni-adjusted \(p=.136\), so “significant” requires an explicit marginal/exploratory qualifier; moreover D−D′ is another CI-excluding-zero positive, +0.228 with bootstrap CI approximately [+0.137, +0.319], although it is not compute-matched or cleanly attributable.

4. **OVERCLAIMED — “D vs D′ (+0.228) is dominated by pool composition, not structure.”** The protocol graph is held fixed, so the descriptive difference is associated with changing the pool, but realized cost simultaneously changes by 7.7× and the arms differ in model capability, native reasoning spend, truncation exposure, and lineage. D’s proximity to A(gemini) makes “Gemini’s presence” plausible, but the data cannot separate that explanation from diversity or added inference compute, nor establish that ReConcile added no value.

5. **OVERCLAIMED — ceiling analysis and “C realized none of it.”** The arithmetic is correct: the A-column oracle is 0.8538 versus Gemini’s 0.7974, a +0.0564 gap on 13 tasks; my task bootstrap gives approximately [+0.022, +0.099]. The write-up correctly limits this ceiling to one-draw-per-member selection, but C generated fresh drafts rather than selecting the recorded A drafts, and its unchosen candidates were not retained, so realized selection recovery is unmeasurable; likewise “no generation lift appeared” is too strong without D/E draft-level before/after scores.

6. **OVERCLAIMED — “Consistent with (not confirmation of) the strata hypothesis.”** The caution against confirmation is appropriate, but 0.797 is not the pre-registered 60–70% easy band; it lies outside the calibrated strata entirely. C and E are harmful and D is near zero, which is qualitatively compatible with an extrapolation of the easy-band story, but a single invalidated pool cannot provide evidence about a Protocol × Stratum relationship.

7. **UNSUPPORTED — “All open instrument issues bias against the best single model or toward fake collaboration wins.”** The Gemini cap may suppress A(gemini), but Gemini-bearing protocols have different numbers and roles of capped calls—38 flagged truncations in D, 23 in E, and 15 in C—so exposure is not common or one-sided. Uncontrolled provider randomness is two-sided, possible Gemini contamination could favor the best single model, and weighted-vote tie-breaking can help or hurt either D arm; the missing matched baseline is an identification gap, not a directional bias.

8. **SUPPORTED, AS AN ORACLE BOUND — routing corollary.** I reproduce 0.8323 mean fraction at 49.0% of all-Gemini cost by choosing, for each task, the cheapest realized model whose score is at least Gemini’s realized score; this routes 48/86 tasks to cheaper models (38 GPT, 10 Haiku). The rule should be stated explicitly and described as an ex-post upper bound: it uses counterfactual executable outcomes and realized costs unavailable to a deployable pre-hoc router, and it excludes routing/training overhead.

## Statistical methodology findings

1. **The paired task bootstrap is appropriate for the declared task-equal mean-fraction estimand.** It preserves within-task pairing and treats the private tests inside each task as a cluster, avoiding test-case pseudoreplication. A flat test-case binomial analysis would both understate uncertainty and change the estimand by giving 40-test tasks much more weight than one-test tasks.

2. **The sampling target needs definition.** The bootstrap treats 86 tasks as independent draws from a task superpopulation, but they come from one release and only 21 contests, with 2–6 tasks per contest. An exploratory contest-cluster bootstrap widens D−Gemini to approximately [−0.093, +0.149]; C and E remain negative, while B−A(gpt) remains positive at approximately [+0.022, +0.168].

3. **The five marginal intervals are not simultaneous.** They share tasks and arms, and the family appears selected for this write-up rather than governed by a registered pilot analysis. Either label all intervals marginal and exploratory or predefine a comparison family and use a joint paired bootstrap, Holm procedure, or other registered adjustment; under a simple Holm sensitivity, B’s primary mean-fraction result no longer clears 0.05.

4. **The strict/fractional discrepancy is shown but not integrated into the conclusion.** D beats Gemini only under equal-task mean fraction. It loses slightly on strict success and on the diagnostic private-test-weighted fraction, 0.8217 versus 0.8252; the latter is not a replacement primary metric, but the sign change should accompany any public “parity” sentence.

5. **One provider replicate is a larger limitation than the task CI conveys.** The harness seed controls protocol shuffles and fallbacks, not provider generation, so task bootstrapping conditions on one realized generation draw per arm. On the same three smoke tasks, the two post-Gemini-fix A runs moved GPT from 0.667 to 0.167 and Haiku from 0.633 to 0.383, illustrating why provider-level repeats are needed.

6. **Failure accounting is internally inconsistent in the presented comparison.** The sole A(gpt) abort is serialized as `unexpected_error`, although it was semantically a moderation refusal; the headline correctly reports 22/85, but the +0.094 B−A point matches treating that row as a zero. The paired comparison must use the same exclusion rule as the displayed denominator.

7. **The telemetry statement is factually wrong.** The raw log contains 24 `weighted_vote_ties`: 4/86 in D and 20/86 in D′. Parse failures are zero, but tie events are not; because all runs use one interpreter seed, tie-resolution sensitivity is unmeasured and especially relevant to D′.

8. **“Dollars per solved task” is undefined under the primary fractional outcome unless “solved” means strict pass.** The quoted $0.110 and $0.438 values use strict passes. If fractional mass is interpreted as equivalent solved tasks, the corresponding values are about $0.097 and $0.368; either definition preserves the efficiency conclusion, but the metric must be named accurately.

## Missing analyses (with results if you ran them)

1. **Cap-proxy decomposition.** On the 26 A(gemini) tasks with at least 32,000 output tokens, Gemini averages 0.467 and D beats it by +0.228. On the other 60 tasks, Gemini averages 0.940 and D is −0.072; thus D’s aggregate +0.019 is entirely concentrated in the post-hoc cap-proxy subset. The oracle gap is +0.186 on the proxy subset and only +0.0004 elsewhere, so almost all measured selection headroom is associated with cap-limited Gemini rows.

2. **Difficulty-label breakdown.** On medium tasks, Gemini is 0.939 and D is 0.921 (−0.018); on hard tasks, Gemini is 0.736 and D is 0.770 (+0.035). Both differences are imprecise, and even the “hard” label lies above the design’s 60–70% easy band for the actual best subject, confirming that these benchmark labels are not usable as the registered empirical strata.

3. **Observed cost-quality frontier.** Under mean fraction, C is dominated by A(gemini), E is dominated by A(gemini), and D′ is dominated by B. D is the highest-scoring observed arm by only 1.9 points at 3.9× Gemini’s cost; under strict success, Gemini also dominates D.

4. **Task-level gain/loss decomposition.** D beats Gemini on fraction on 14 tasks, loses on 15, and ties on 57; on strict success the corresponding discordances are 10 wins and 11 losses. This is a clearer description than “parity”: different outputs largely cancel in the aggregate.

5. **April ceiling replication.** On April’s medium+hard A columns, Haiku—not GPT—is the best mean-fraction subject at 0.606; the oracle is 0.717, for the stated +0.111 gap. That arithmetic is correct and confirms that the metric switch and truncation fix changed both the anchor and the apparent complementarity structure.

6. **Tie-rate reporting and sensitivity.** Weighted-vote ties occur in 23% of D′ tasks versus 5% of D tasks. Candidate texts are absent, so the outcomes cannot be re-aggregated under alternate tie seeds; this should be reported as an unresolved single-seed sensitivity rather than “zero tie events.”

## Publishability

I would object to the following sentences if quoted verbatim:

- **“No collaboration condition beats the best single model at matched compute.”**  
  Replace with: “No collaboration condition demonstrated a compute-matched win; D lacked a matched B/A⁺ comparator, while C and E were already dominated by the cheaper Gemini baseline.”

- **“D achieves statistical parity with A(gemini) at 3.9× the dollar cost.”**  
  Replace with: “D was not statistically distinguishable from A(gemini) on task-equal mean fraction, but the interval was wide [−0.068, +0.109], strict success slightly favored Gemini, and no equivalence test was specified.”

- **“The one significant positive: repeat-sampling.”**  
  Replace with: “B−A(gpt) was the only positive among the five reported marginal comparisons; its unadjusted interval excluded zero, but it did not survive a simple familywise multiplicity sensitivity and requires provider-level replication.”

- **“D vs D′ (+0.228) is dominated by pool composition, not structure.”**  
  Replace with: “D outscored D′ by 0.228, but changing the pool also changed realized cost by 7.7×, so the pilot cannot separate Gemini capability, lineage diversity, and native reasoning spend.”

- **“C realized none of the available headroom.”**  
  Replace with: “C’s final score fell below A(gemini), but candidate-level recovery cannot be measured because C used fresh drafts and unchosen candidates were not retained.”

- **“The pool sits in the easy band for the true best subject (0.797).”**  
  Replace with: “The pool is easier than the pre-registered easy band for the apparent best subject, so the strata hypothesis was not tested; the observed harm/neutrality is only qualitatively compatible with its easy-side prediction.”

- **“Every condition faces the same bounded Gemini, so within-run comparisons are internally consistent.”**  
  Replace with: “Gemini-bearing conditions used the same per-call cap but had different numbers and roles of Gemini calls, so truncation exposure was not equal across arms.”

- **“All open instrument issues bias against the best single model or toward fake collaboration wins.”**  
  Delete. Several issues are two-sided, and possible Gemini contamination points in the opposite direction.

- **“Zero infra-failure aborts; zero parse-failure or tie events surfaced.”**  
  Replace with: “Zero infrastructure failures and parse failures surfaced; 24 weighted-vote ties occurred, including 20 in D′.”

- **“The same pool … offers 2× savings to cost-seeking routing.”**  
  Replace with: “An ex-post oracle indicates up to roughly 2× savings may be available; whether a pre-hoc router can realize that bound is untested.”

## Recommendation

**Revise and re-review.**
