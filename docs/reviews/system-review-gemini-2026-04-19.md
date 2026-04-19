# Review: Phase 1 Operational-Readiness Fixes (Round 4)

**Reviewer:** Gemini (Independent Cross-Lineage Reviewer)
**Date:** 2026-04-19
**Artifact reviewed:** System at commit `c5211a2`, updated `src/executor/interpreter.py`, `tests/`, `scripts/smoke_test.py`, and Codex's round-4 review.

## Summary assessment
The final two operational blockers from round 3 (inverted parser priorities and discarded telemetry) are fully and elegantly resolved. The parser logic correctly implements a most-specific-first extraction, and exposing telemetry alongside the result is the pragmatic choice that unblocks the observability requirement. I recommend **Proceed**.

## Specific findings

**1. Telemetry Exposure:**
Returning `(result, telemetry)` from `run()` directly addresses my Round 3 catch. This is the right API shape at this stage. It avoids forcing callers to manage the `Interpreter` object lifecycle, while cleanly bubbling up the `InterpreterTelemetry` dataclass. The upcoming runner will simply accumulate these per-task-instance telemetry objects across the entire benchmark run.

**2. Parser Priorities:**
I strongly concur with Codex that the inverted priorities resolve the substantive measurement vulnerabilities. `_parse_score` properly handles the scale-echo hijacking by evaluating highly specific semantic patterns (`N/10`, labeled score) before falling back to the last generic float. `_parse_pick`'s pick-verb matching handles negative framing correctly. While edge cases like `"0.7/1.0"` might technically fall through to `1.0`, these are edge cases on an edge case; the parser is robust enough for Phase 1. 

**3. Temperature Default and Vendor Variance:**
Setting `ApiClient`'s default temperature to `None` effectively delegates to vendor defaults, averting the homogeneous mode-collapse. As discussed in Round 3, mixing different vendor default temperatures does introduce an additional axis of search-space variance. However, at a matched-dollar constraint, a model's default temperature is intrinsic to its capability profile. This is a feature of the macro-model, not a confound to eliminate.

**4. Smoke Test Temperature Flag:**
Codex noted that `scripts/smoke_test.py` explicitly initializes `ApiClient(temperature=0.0)`. This is entirely appropriate. A smoke test should be as deterministic as possible to test pipeline plumbing without wasting API variance. As long as `ApiClient` defaults to `None` in production, the smoke test configuration does not threaten Phase 1 calibration.

**5. Selector-as-Oracle Re-audit:**
The system remains hermetically sealed from the oracle. `PickOne` and the telemetry tracking do not introduce any leakage paths. 

**6. Cost Tracking Architecture:**
The `PricingTable × CallRecord.tokens` setup is exactly right for the upcoming runner. The `ApiClient` should remain stateless regarding dollar cost. The runner will handle run attribution by capturing `client.calls` slices and applying the pricing table.

## Recommendation
**Proceed.**

The operational blockers are cleared. You are ready to move to the next phase: benchmark adapters, experiment runner with budget-cap enforcement, and the pre-kickoff power analysis.