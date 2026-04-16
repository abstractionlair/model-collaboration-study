# Review: Phase 1 system implementation (round 2)

**Reviewer:** OpenAI Codex (GPT-5)
**Date:** 2026-04-16
**Artifact reviewed:** The reconciliation work on top of commit `16e1f78`, specifically commits `f295e59`, `82627d3`, `a704cf0`, `4609c33`, and `87909d6`, plus the current `docs/research/experimental-design.md`, `docs/decisions.md`, `docs/status.md`, and the updated code in `src/ir/`, `src/executor/`, `src/experiment/`, and `src/protocols/`.

## Summary assessment

The three faithfulness gaps I flagged in round 1 are now resolved at the code-and-design level. The macro-model conditions finally match the promoted design closely enough that I would stop treating faithfulness as the main risk. The remaining reasons not to proceed are operational: parser/retry/empty-response bugs, pre-calibration placeholders still callable, and the still-degenerate generation stochasticity setup. Recommendation remains **Revise and re-review**, but now for implementation-readiness rather than design/implementation mismatch.

## Specific findings

1. The three round-1 faithfulness gaps are resolved cleanly.
   - The D-family no longer uses self-review semantics. `reconcile()` now uses `PeerRounds`, and the interpreter implements reviewer ≠ writer via explicit peer-review logic (`src/protocols/reconcile.py`, `src/executor/interpreter.py`).
   - B and C no longer silently reinterpret "chooses among the N candidates" as pointwise scoring. `PickOne` is a genuine comparative-selection node, and B/C now use it (`src/protocols/conditions.py`, `src/ir/ast.py`, `src/executor/interpreter.py`).
   - E now matches the design's "meta sees drafts plus raw critiques and writes the final response directly" shape via `ParPeerReview + FuseWithCritiques`, while the previous variant survives as a distinct named macro-model (`src/protocols/conditions.py`).

2. The cyclic 1-peer assignment is a reasonable Phase 1 operationalization, not a design failure. The promoted design said "1–2 peers"; the implementation picks the lower bound, keeps the per-round call count at 2 per draft, and documents it as the specific `PeerReviseRound` / `PeerRounds` rule (`src/ir/ast.py`, `docs/design/system-architecture.md`, `docs/research/experimental-design.md`). I would keep this for Phase 1 rather than jumping to 2-peer review now. The one caveat is that with a fixed model ordering it also hard-codes reviewer→writer edges. That is acceptable for a screened family comparison, but it should be understood as the particular D-family instantiation being tested, not "peer review in general."

3. The "keep old as renamed building block, add design-faithful sibling" pattern is principled here, not over-engineering.
   - `SelfReviseRound` vs `PeerReviseRound`
   - `ParScore + WeightedVote` vs `PickOne`
   - `condition_e_writers_revise_then_fuse` vs design-faithful `condition_e`
   
   In each case the retained old form is a semantically distinct macro-model family already present in the protocol inventory or a plausible follow-on ablation. This is exactly the kind of distinction the typed substrate is supposed to preserve. The caution is scope discipline: this pattern is good for genuinely different structural families, not for every small prompt or policy tweak.

4. One new blind spot was introduced by the reconciliation work: `TracingClient.step_type` is now stale relative to the new nodes. It can classify `fuse`, `score`, `review`, and `revise`, but not `pick_one` or `fuse_with_critiques`, so the smoke-test trace no longer has a clean way to distinguish those steps (`src/executor/tracing.py`). That does not invalidate the implementation, but it weakens the already-limited smoke-test audit story and should be updated soon.

5. The remaining parser issues are now more consequential than before and still block trustworthy Phase 1 measurement.
   - `_parse_score()` still takes the first float token and silently falls back to `0.5`.
   - `_parse_pick()` silently falls back to candidate 1 on parse failure.
   - `WeightedVote` still resolves ties positionally.
   
   Before the reconciliations, these mostly threatened pointwise-scored conditions. Now `_parse_pick()` directly affects B and C, so silent parse failure becomes silent first-candidate bias in the compute-matched baseline itself. This should be fixed before any real run.

6. The Google retry classification issue still holds and remains worth fixing before real runs. `ApiClient` still treats `google.genai.errors.ClientError` as infrastructure-retryable (`src/executor/api_client.py`), which is too broad for 4xx client failures. This is not theoretical; it directly affects the "infra failures don't count against budget" discipline once a runner exists.

7. Empty-response handling and infra-failure telemetry are still under-specified in the actual runtime path. `ApiClient` still only records successful calls in `self.calls`, and empty provider responses still collapse to ordinary text outputs (`src/executor/api_client.py`). Those behaviors are survivable in scaffolding, but they are not yet compatible with the failure accounting the design and status docs describe. I still consider these pre-Phase-1-run fixes, not optional cleanup.

8. The pre-calibration placeholders remain callable and therefore remain blocking for Phase 1 readiness. `_best_model()`, `_n_samples_for_b()`, and `PHASE1_PRICING` in `src/experiment/phase1.py` still build a full `ExperimentSpec` without any guardrails. The reconciliations improved structural faithfulness, but they did not change the fact that the matched-budget baseline can still be built from placeholders.

9. The generation stochasticity issue also remains blocking for a real Phase 1 run. `ApiClient` still defaults to `temperature=0.0`, `ExperimentSpec` still defaults to `seeds=5`, and nothing in the execution stack currently makes those seeds materially different (`src/executor/api_client.py`, `src/experiment/spec.py`, `src/experiment/phase1.py`). This now matters even more because homogeneous-pool conditions like D' and same-model B are central controls; without stochasticity they collapse toward duplicate drafts.

10. FakeClient-backed unit tests are still missing in committed form. I agree with the updated architecture doc that the call-count math has been hand-verified, but that is not a substitute for executable tests now that the IR has more branching families and more subtle alignment invariants (`docs/design/system-architecture.md`, `src/executor/client.py`). I still do not consider this a blocker for the next review round, but it should not slide much further.

11. I did not find a new structural regression in the reconciliations themselves. The new nodes are type-coherent, the intended alignments are explicit in the code and docs, and the "keep old, add sibling" decisions are recorded clearly enough in `docs/decisions.md` to be reviewable later.

## Recommendation

**Revise and re-review.**

The design-faithfulness work is now good enough. I would not spend another round on reinterpreting macro-model semantics unless a new issue appears. The next round should instead close the operational blockers:

1. Fix parser behavior (`_parse_score`, `_parse_pick`, `WeightedVote` tie handling) and add telemetry for parse failures and ties.
2. Fix Google retry classification, empty-response handling, and failed-call telemetry.
3. Gate `_best_model`, `_n_samples_for_b`, and `PHASE1_PRICING` against pre-calibration use.
4. Make generation stochasticity real for seeded runs.
5. Update tracing/smoke-test instrumentation to understand `PickOne` and `FuseWithCritiques`.

After that, I would expect the next review round to be capable of recommending `Proceed`.
