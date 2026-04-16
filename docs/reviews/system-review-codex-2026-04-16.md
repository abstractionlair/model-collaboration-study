# Review: Phase 1 system implementation

**Reviewer:** OpenAI Codex (GPT-5)
**Date:** 2026-04-16
**Artifact reviewed:** The system as of commit `16e1f78`, with primary attention to `src/ir/`, `src/executor/`, `src/experiment/`, `src/protocols/`, `scripts/smoke_test.py`, and the Opus review at `docs/reviews/system-review-opus47-2026-04-16.md`. Checked against `docs/research/experimental-design.md`, `docs/decisions.md`, and `docs/design/system-architecture.md`.

## Summary assessment

The system shape is still sound: the three-layer split is real, the IR remains small and intelligible, and the macro-model framing survives contact with code. I agree with Opus 4.7's overall recommendation of **Revise and re-review**. Most of the implementation-bug findings hold. On the design-faithfulness questions, Opus is directionally right on B/C aggregation and E composition, but it missed the larger faithfulness gap: the D-family implementation is self-review informed by peers, while the promoted design text describes peer review.

## Specific findings

1. The biggest faithfulness gap is not B/C or E; it is D/D'/E's review semantics. `ReviseRound` is implemented as each model reviewing its **own** draft in light of peer drafts (`src/executor/interpreter.py`, `_review_and_revise_one` / `_one_round`), and the default prompt is explicitly self-review ("Review your draft answer in light of the peer drafts below" in `src/experiment/prompts.py`). But the promoted design describes D as each draft being reviewed by 1-2 peers and E as "reviewers critique the drafts" before meta-synthesis (`docs/research/experimental-design.md`, Macro-Model Conditions). That is a substantive macro-model difference, not wording noise. This is the highest-priority design/implementation reconciliation issue in the current system, and Opus did not flag it.

2. Opus finding #1 on B/C aggregation holds in substance, but "silent reinterpretation" overstates it slightly. The implementation of B and C is indeed pointwise `ParScore + WeightedVote`, so the judge never sees candidates side-by-side (`src/protocols/conditions.py`, `condition_b`, `condition_c`; `src/executor/interpreter.py`, `ParScore`, `WeightedVote`). That is materially different from the promoted design's wording that the same-model peer judge / peer-LLM "chooses among the N candidates" (`docs/research/experimental-design.md`, Macro-Model Conditions B and C). However, this is not completely silent: `src/protocols/conditions.py` says so in the docstring, and `docs/design/system-architecture.md` already describes B as `ParGen + ParScore + WeightedVote`. The real problem is that the locked experimental design and the implementation-side docs disagree. Either adopt pointwise scoring explicitly in the design/decision layer or add a comparative-selection node.

3. Opus finding #2 on E also holds in substance, but the precise mismatch is narrower than Opus describes. The implementation is `ParGen -> ReviseRound -> Fuse(meta over revised drafts)` (`src/protocols/conditions.py`, `condition_e`). The promoted design committed to "reviewers critique the drafts; a separate meta-reviewer synthesizes the critiques and writes the final response directly," explicitly rejecting the "writers revise, then aggregate" alternative (`docs/research/experimental-design.md`, Condition E). The implemented E is therefore a third variant. But it is still closer to the approved design than Opus allowed: the meta-reviewer does write the final response directly, and there is no separate aggregation step. The mismatch is specifically the inputs to the terminal synthesis stage: revised drafts rather than critiques.

4. The promoted experimental design artifact is internally inconsistent in a way that makes faithfulness review harder than it should be, and Opus missed this. The macro-model framing section correctly forbids evaluator-as-selector and requires aggregation to happen inside the pipeline, but the Independent Variables section still contains stale text saying that with executable scoring "the selection rule is fixed to pick the candidate that passes the executable check." The document also contains a duplicated "What the matrix tests" section. This should be cleaned up before or alongside any code/design reconciliation, otherwise future reviewers will be comparing implementation against contradictory design text.

5. Opus finding #3 on Google retry classification is correct. `src/executor/api_client.py` treats `google.genai.errors.ClientError` as infrastructure-retryable, but the installed SDK raises `ClientError` for all 4xx responses. That would misclassify malformed requests, auth failures, and bad model IDs as retryable infra failures. This should be narrowed to status-based retryability (408 / 429 / 5xx), not exception-class-wide retryability.

6. Opus findings #4 and #5 together are a real measurement-quality problem, not just polish. `_parse_score()` in `src/executor/interpreter.py` takes the first parseable float token and silently falls back to `0.5` on non-numeric output; `WeightedVote` breaks ties positionally by returning the first max. Those two behaviors compose badly: parse drift or non-numeric score responses collapse selection to positional bias. This is especially damaging in B/C where pointwise scoring is already the only aggregation signal.

7. Opus finding #6 on empty-response handling is directionally correct, but the deeper gap is that the current runtime does not preserve enough boundary information to distinguish capability failure from malformed/no-response failure cleanly. `ApiClient` adapters coerce empty provider outputs to `""`, and the executor treats that as an ordinary draft. The design wants zero-length output treated as capability failure, but the current runtime path silently threads it through scoring and aggregation. That needs an explicit representation or at least explicit telemetry at the executor boundary.

8. Opus findings #7, #8, and #9 on Phase 1 gating all hold. `_best_model()`, `_n_samples_for_b()`, and `PHASE1_PRICING` are placeholders in `src/experiment/phase1.py`, but `build_phase1_conditions()` and `build_phase1_spec()` remain callable without any pre-calibration guard. That means the system can currently build a Phase 1 spec that quietly violates the matched-budget discipline and the "best single model" baseline assumption. These should fail loudly before calibration.

9. Opus finding #11 on `temperature=0` plus `seeds=5` also holds. As currently wired, the seeds field in `ExperimentSpec` is mostly decorative for API-backed runs. If variance across seeds is intended as a real metric, either the generation settings need stochasticity or the design/status docs should stop implying that seed variance is already meaningful.

10. Opus finding #13 on missing FakeClient tests holds, and the architecture doc currently overclaims this coverage. `docs/design/system-architecture.md` says the executor and all six condition factories have been smoke-tested end-to-end with `FakeClient`, including expected call counts, but I could not find committed tests for that. Since identity memoization, Par-* alignment, and D/E call-count semantics are exactly the things likely to regress silently, this is worth fixing soon even if it is not the next blocking item.

11. One additional implementation gap Opus did not mention: failed infrastructure attempts are not recorded in `ApiClient.calls`. Only successful calls append `CallRecord`. The design and status artifacts now talk about infra failures as diagnostics, retries, and non-budgeted events, but the current client does not preserve enough information to audit exhausted retries or provider-specific failure rates after the fact. This is less urgent than the parser/retry bugs, but it will matter once real runs begin.

12. I agree with Opus that the remaining items around real parallelism and `TracingClient` prompt-text heuristics are real but non-blocking for the next review round. They should be tracked, but they are not the reason to hold promotion of the implementation work.

## Recommendation

**Revise and re-review.**

The right next round is narrower than a general redesign:

1. Reconcile the three design-faithfulness gaps explicitly: D-family self-review vs peer review, B/C pointwise scoring vs comparative choice, and E's revised-drafts-to-meta shape vs the promoted critique-synthesis description. Record the decisions.
2. Fix the concrete measurement bugs: Google retry classification, score parsing, WeightedVote tie handling, and empty-response / parse-failure telemetry.
3. Gate Phase 1 builders against pre-calibration use.
4. Clean the promoted design artifact's stale selector language and duplicate subsection so future reviews have one source of truth.

After that, re-review should be enough; nothing here points to architectural collapse.
