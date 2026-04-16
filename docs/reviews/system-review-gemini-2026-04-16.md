# Review: Phase 1 system implementation

**Reviewer:** Gemini (Independent Cross-Lineage Reviewer)
**Date:** 2026-04-16
**Artifact reviewed:** The system as of commit `16e1f78`, specifically `src/executor/interpreter.py`, `src/protocols/conditions.py`, and the accompanying reviews by Opus 4.7 and Codex. Checked against `docs/research/experimental-design.md`.

## Summary assessment
The architectural layering (IR -> Executor -> Experiment Spec) is sound and the selector-as-oracle discipline is cleanly maintained in the code. However, severe design-implementation divergences in conditions B, D, and E mean the code currently implements a different experimental matrix than the promoted design. Furthermore, an overlooked interaction with `temperature=0` will cause the homogeneous conditions (B and D') to mechanically collapse into single-pass baselines, invalidating the compute-matched controls.

## Specific findings

**1. Homogeneous conditions (B, D') will collapse at `temperature=0` (Missed by both Opus and Codex).**
Opus 4.7 correctly identified that `temperature=0` with `seeds=5` yields zero variance across runs. However, the much more catastrophic measurement issue is *internal* to the macro-models: at `temperature=0`, `ParGen` running against a homogeneous pool (Conditions B and D') will produce *N exactly identical drafts*. 
- For Condition B (Best-of-N), the aggregator will just be picking among N identical copies, meaning B mathematically reduces to Condition A. 
- For Condition D', 3 identical writers will review 3 identical drafts. 
To test the compute-scaling hypothesis and homogeneous collaboration, you **must** use `temperature > 0` during generation to create the intra-pool variance that aggregation and peer-review rely on.

**2. D-family is Self-Review, not Peer Review (Codex is 100% correct).**
In `interpreter.py`'s `_one_round`, the model `m` that generated the draft is the exact same model prompted to review and revise it (`self._review_and_revise_one(m, drafts[i]...)`). This is self-review with peer visibility, whereas the design strictly dictates peer review ("each draft reviewed by 1-2 peers"). This completely destroys the heterogeneity axis for Condition D, because the critique comes from the model's own lineage rather than a diverse peer.

**3. B/C Pointwise Scoring vs Comparative Selection (Opus & Codex are correct).**
The design explicitly specifies a peer-judge that "chooses among the N candidates." The implementation uses `ParScore` (scoring each draft in total isolation) followed by `WeightedVote` (argmax). Pointwise scoring lacks a comparative anchor and is highly susceptible to score clustering or default-fallback, mechanically collapsing the choice to positional bias. Either the IR needs a true comparative node (e.g., `PickOne(judge, drafts) -> Answer`), or the design must formally adopt pointwise scoring.

**4. Condition E Composition Divergence (Opus is correct).**
The implemented Condition E (`ParGen -> ReviseRound -> Fuse`) forces writers to revise their own drafts before the meta-reviewer synthesizes them. The promoted design explicitly rejected this, committing to a macro-model where drafts are critiqued, and then the meta-reviewer synthesizes those raw critiques and writes the final response directly. The code implements the rejected alternative.

**5. Tie-breaking bias and Parse Failures compound silently (Opus #4, #5).**
Because `_parse_score` silently defaults to `0.5` on non-numeric text, and `WeightedVote` breaks ties by taking the first maximum index (`max(..., key=...)`), any parse failure or score tie systematically privileges the first model in the array. If the pool is `[gpt-5.4-mini, claude-haiku-4-5, gemini-2.5-flash]`, GPT will mechanically win every tie.

**6. Selector-as-Oracle design doc inconsistency.**
The code implementation is completely clean; the `Interpreter` evaluates nodes and calls `client.complete` without ever seeing the benchmark oracle. However, as Codex spotted, the promoted `experimental-design.md` still contains stale text under the "Independent Variables" section ("With executable scoring, the selection rule is fixed to 'pick the candidate that passes the executable check'"). This text directly contradicts your Round 3 macro-model reframing and must be purged to prevent reviewer confusion.

## Recommendation
**Revise and re-review.**

The system's foundation is excellent, but you cannot proceed to calibration until you:
1. Reconcile the macro-model implementations (B, C, D, E) with the design text.
2. Set `temperature > 0` to ensure Conditions B and D' actually generate N unique samples.
3. Fix the score parser's silent fallback and implement explicit, randomized tie-breaking for `WeightedVote`.
4. Scrub the stale oracle-selector language from the design doc.