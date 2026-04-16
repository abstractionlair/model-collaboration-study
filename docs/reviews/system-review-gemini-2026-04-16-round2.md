# Review: Phase 1 system implementation (round 2)

**Reviewer:** Gemini (Independent Cross-Lineage Reviewer)
**Date:** 2026-04-16
**Artifact reviewed:** The reconciliation work on top of commit `16e1f78`, specifically commits `f295e59`, `82627d3`, `a704cf0`, `4609c33`, and `87909d6`. Checked against updated design docs, the code in `src/`, and Codex's round-2 review.

## Summary assessment

The structural and design-faithfulness issues are now cleanly and elegantly resolved. The strategy of preserving previous behaviors as distinct typed building blocks while introducing faithful implementations (`PeerRounds`, `PickOne`, `FuseWithCritiques`) is a textbook use of the AST pattern, establishing a robust foundation for future macro-model exploration. The macro-models finally match the promoted experimental design. However, the system is not yet ready for Phase 1 kickoff due to critical operational blockers—most notably the `temperature=0` default that continues to cause homogeneous conditions to mechanically collapse into single-pass baselines. My recommendation remains **Revise and re-review**, but the focus now shifts entirely to implementation readiness and measurement quality.

## Specific findings

### 1. Faithfulness Gaps Resolved

- **D-family Peer Review:** The cyclic 1-peer assignment via `PeerReviseRound` is a faithful and cleanly constrained operationalization of the design's "1-2 peers" requirement. The fact that fixed model ordering hard-codes the reviewer→writer edges is completely acceptable for Phase 1 screening, provided it is treated as a specific D-family instantiation rather than a universal property of peer review.
- **B/C Comparative Selection:** `PickOne` perfectly resolves the pointwise-vs-comparative gap. It places all candidates in front of the judge side-by-side, adhering to the "chooses among the N candidates" phrasing. However, the fallback implementation in `_parse_pick` (returning candidate 1 on parse failure) means that the measurement vulnerability (positional bias) is still present and now affects the comparative baseline directly.
- **Condition E Composition:** `ParPeerReview` -> `FuseWithCritiques` is structurally perfect. It fulfills the exact design intent ("meta-reviewer synthesizes the critiques and writes the final response directly") without implicit aggregation or nested revision steps.

### 2. Measurement Quality and the Temperature=0 Collapse

The `temperature=0` and `seeds=5` default cannot be deferred. This is not just a "variance metric" bug; it is a fatal flaw for homogeneous conditions.
- **Why it must be fixed now:** Leaving `temperature=0` means that any hand-run smoke tests or dry runs of Conditions B and D' are currently evaluating degenerate effects.
- **The impact on `PickOne`:** For Condition B at temp=0, `ParGen` generates N identical drafts. `PickOne` then presents a prompt to the judge containing N identical blocks of text. The judge model is forced to choose between indistinguishable options, which will likely confuse it or result in arbitrary output. If it fails to parse, the fallback selects index 0. Mathematically, it collapses to Condition A with extra wasted API calls and tokens. This fundamentally destroys the compute-scaling baseline. You must implement generation stochasticity (e.g., `temperature > 0`) before any meaningful calibration can begin.

### 3. Selector-as-Oracle Re-audit

The discipline remains completely clean. The introduction of `PickOne`, `ParPeerReview`, and `FuseWithCritiques` does not introduce any oracle leakage. `PickOne` shows the judge multiple candidates, but none of the context injected into the prompt includes the executable test cases or oracle ground truth. The boundary between the executor's internal aggregation and the external benchmark runner is fully respected.

### 4. Remaining Open Items (Operational Blockers)

The remaining items identified by Codex are no longer "optional cleanup"—they are **blocking for Phase 1 calibration and real runs**:
- **Parsers and Fallbacks:** `_parse_score` and `_parse_pick` silent fallbacks to 0.5 and index 0 respectively, along with `WeightedVote`'s positional tie-breaking, will systematically skew the results of your tightest comparisons. They must be replaced with randomized tie-breaking and explicit parse-failure telemetry.
- **Google Retry Classification:** Blanket-treating 4xx as infra-retryable will burn retry budgets on malformed prompts and mask genuine capability failures.
- **Pre-calibration Gates:** `_best_model()`, `_n_samples_for_b()`, and `PHASE1_PRICING` must fail loudly if invoked before real calibration parameters are set.
- **Telemetry & Tracing:** Empty-response capability failures and exhausted retries must be recorded. Additionally, as Codex pointed out, `TracingClient` is now stale and cannot properly classify `pick_one` or `fuse_with_critiques`.

## Recommendation

**Revise and re-review.**

The structural architecture and macro-model framing are pristine. You are clear to proceed with closing the operational blockers. The next round of revisions should strictly target the measurement quality bugs (parsers, fallbacks, stochasticity) and Phase 1 readiness gates. Once those are addressed, the system will be ready to proceed to benchmark integration and actual execution.