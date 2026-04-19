# Review: Phase 1 Operational-Readiness Fixes (Round 3)

**Reviewer:** Gemini (Independent Cross-Lineage Reviewer)
**Date:** 2026-04-17
**Artifact reviewed:** System at commit `2b98c49` (fixes from commits `10a2f5b` and `2b98c49`), updated docs, and Codex's round-3 review.

## Summary assessment
Most of the round-2 operational blockers are genuinely fixed. The catastrophic homogeneous mode-collapse from `temperature=0` is averted, the positional tie-breaking is fixed, the API reliability/infrastructure categorization is much sharper, and the calibration gates are properly enforced. However, I agree with Codex that the parser logic is inverted and actively harmful to measurement, and I found a critical new regression in the observability layer: the telemetry you just added is being silently discarded. My recommendation remains **Revise and re-review** to close these final two holes before kicking off Phase 1.

## Specific findings

**1. The Telemetry Black Hole (New Finding, Critical)**
You successfully added `InterpreterTelemetry` to track parse failures and ties. However, the `run()` function in `src/executor/interpreter.py` instantiates an `Interpreter`, calls `evaluate()`, and returns *only* the resulting AST node value. The `Interpreter` instance—along with its `self.telemetry` object—is immediately garbage-collected upon return. The runner has absolutely no way to access the telemetry data you just built. 
*Recommendation:* `run()` must either return a `(result, telemetry)` tuple, or the runner needs to instantiate and retain the `Interpreter` directly instead of using the `run()` convenience wrapper.

**2. Parser Priorities are Inverted (Agree with Codex)**
Codex's catch regarding the "scale echo" (`"On a scale of 0.0-1.0, I'd rate this 7 out of 10"`) is exactly right. Because `_parse_score` checks for generic raw floats *before* checking for the highly specific "N out of 10" pattern, the prompt echo (`1.0`) short-circuits the parser, causing it to return a confidently wrong `1.0`. 
The identical logic flaw exists in `_parse_pick`: if a judge says `"I pick 2 because candidate 3 is incomplete"`, Priority 2 grabs the *last* integer in range (`3`) instead of the explicitly labeled one.
*Recommendation:* Highly structured, high-signal patterns (`N out of 10`, `Candidate N`) must *always* be evaluated before unstructured fallback patterns (last float, last int). Invert the priority order in both parsers.

**3. Temperature and Vendor-Level Variance**
Dropping `temperature=0` and delegating to vendor defaults successfully fixes the homogeneous mode-collapse. Does vendor-level temperature variance introduce a new confound between D and D'? Conceptually, yes. Mixing different vendor default temperatures creates a broader combined search space (another axis of heterogeneity beyond pure lineage diversity).
However, because we are matched-by-dollars and testing protocols against "off-the-shelf" capability profiles, this is acceptable. A model's default temperature is intrinsic to its API offering. Just ensure this interpretive confound is explicitly named in the analysis (similar to the price-arbitrage subtlety) when discussing *why* heterogeneity works. 

**4. Cost Tracking and ApiClient Boundary**
`PricingTable × CallRecord.tokens` is the exact right shape. `ApiClient` should remain oblivious to dollars because prices fluctuate and run-attribution is not the client's job. Leaving the cost-rollup logic to the upcoming runner is the correct architectural boundary. There is nothing in the current code that needs adjustment for the runner to layer cleanly; the runner can simply snapshot `len(client.calls)` before and after execution to isolate a run's token spend.

**5. Selector-as-Oracle Re-audit**
The discipline remains mathematically clean. The new AST nodes (`PickOne`, `ParPeerReview`, `FuseWithCritiques`), the new parser fallbacks, and the pricing tables introduce no path for the oracle (executable test cases) to leak into the pipeline. The executor remains hermetically sealed from ground truth.

## Recommendation
**Revise and re-review.**

You are extremely close. Invert the parser regex priorities so specific semantic patterns beat generic floats/ints, add Codex's edge cases to `test_parsers.py`, and fix the `run()` function so the runner can actually read the telemetry. Once the parsers are honest and the telemetry is visible, you are clear for Phase 1 kickoff.