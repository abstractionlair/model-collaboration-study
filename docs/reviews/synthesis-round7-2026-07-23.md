# Round-7 Review Synthesis — 2026-07-23

Four independent fresh-context reviews of plan + code by the new
model generation: Claude Fable 5 (fresh context), GPT-5.6 Sol
(codex), Grok 4.5 (opencode/xai), Kimi K3 (opencode/openrouter).
First-ever reviews from the xAI and Moonshot lineages.

**Verdict: 4/4 Revise and re-review.** All four judge the design
core (macro-model framing, dollars-as-compute, Best-of-N
discipline, selector-as-oracle rule, pre-registered fallback)
sound; all four find the same shape of problem: measurement
machinery lagging the design's commitments. No reviewer called
for a rethink.

Verification status below reflects the coordinating session's
direct checks against code/data, not reviewer assertion.

## Convergent findings (≥3 reviewers)

| # | Finding | Reviewers | Verified |
|---|---------|-----------|----------|
| 1 | Aggregation layer is task-blind: `_PICK_ONE_USER` and `_SCORE_USER` carry no `{query}`; affects B/C judge and D/D′ confidence scoring. Same defect class as the 2026-04-21 revise-prompt fix, one layer down. | Grok, Sol, Kimi | **Yes** (prompts.py:167-178, interpreter.py:562,603) |
| 2 | Condition E's peer critics still use `PEERS_GROUPED` (task hidden); D was moved to `ALL_VISIBLE` in April, E was not. | Grok, Sol, Kimi | **Yes** (conditions.py:177) |
| 3 | No finish-reason/truncation detection on any provider; the Gemini fix was a threshold bump, not a class fix. A cap-exhausted response on any vendor still scores 0 silently. | Fable, Sol, Kimi | **Yes structurally** (no `finish_reason`/`stop_reason` handling in src/). **Empirically clear in pilot A-columns**: max total completion gpt 2932/4096, haiku 3463/4096, zero at cap. |
| 4 | Budget tiers are unenforced labels; compute-matching holds only for B↔D′; D (≈6× D′ realized) has no matched B comparator, so the design's own Best-of-N discipline is not satisfiable for D/C/E from this run. | All 4 | **Yes** (runner.py:8-13; smoke cost table) |
| 5 | Google 8× output budget deviates from the design's "same max output length" constraint without a decision-log entry; needs an explicit policy (equalize vs instrumented asymmetry). | All 4 | **Yes** (api_client.py:385; no decisions.md entry) |
| 6 | April calibration is invalid (truncation artifact + model swap); recalibration on the fixed harness must precede any re-anchoring of `best_model`; band must be re-frozen from A-column data only, before condition-level results are peeked at. | All 4 | **Yes** (pilot A-columns: gemini 0.797 vs gpt 0.523 / haiku 0.545 mean_frac) |
| 7 | Abort semantics inconsistent: design says infra failures are retried not scored; runner scores them 0 but excludes from `pass_rate`; pilot summary includes them. Two denominators in one pipeline. | Grok, Sol, Kimi | **Yes** (runner.py:74 vs run_pilot.py summarise) |
| 8 | Power analysis (binary, unpaired, binomial) no longer matches the adopted mean_fraction outcome; fractional/paired/clustered re-analysis and multiplicity policy still unregistered. | Grok, Sol, Kimi | **Yes** (known-pending since 2026-07-04; reviewers elevate it to a confirmatory gate) |
| 9 | Deterministic orderings create vendor-aligned biases: candidate order fixed (C), cyclic reviewer pairs fixed per vendor (D), same interpreter seed per task makes fallback randomness positionally biased. | Grok, Sol, Kimi | **Yes by construction** (interpreter.py:316,596; runner.py:107-116) |
| 10 | ParScore parse failure → hardcoded 0.5, not an AST-level policy like PickOne's; fabricates mid-confidence on the live D/D′ path. | Grok, Fable | **Yes** (interpreter.py:564-572) |

## High-value unique findings

- **Sol:** (a) Band-anchoring inconsistency — calibration defines the middle band by Condition **A**'s rate, the power analysis baselines on Condition **B**; unresolved across six prior rounds. (b) **LCB candidate execution is unsandboxed**: generated code runs as the local user with the decoded private tests readable on disk — an execution-side oracle-access hole (prompt-side hermeticity is clean; this is the other side). *Both pending direct verification before patching.* (c) Checkpoint resume validates nothing (code/config drift can silently mix rows). (d) "Dollars per solved task" is undefined under fractional scoring.
- **Kimi:** (a) Empirical infeasibility check — within the current pool, only ~5 tasks put Gemini in [0.3,0.7] (16 at ≤0.5, where gpt/haiku fall to 0.2–0.3): a Gemini-anchored middle band **cannot be carved from test6**; pool expansion is the only viable option, not one of three. (b) Capability-gap flatness assumption now broken in both directions — Phase 1 becomes a gapped-pool (weak-reviewer) experiment either way; utility curve needs re-derivation. (c) The pilot's content-filter abort is an unhandled third failure class (provider refusal ≠ capability ≠ infra). (d) `decisions.md` 2026-07-04 item 4's rationale ("2.5-flash is noise beyond easy") was measured through the truncation bug and should be annotated as corrupted evidence. (e) Contamination window for Gemini 3 on test6 unexamined.
- **Fable:** (a) The truncation *class* framing and the fence-extraction mechanism that renders truncation invisible (unclosed fence → whole response executed → runtime error → 0.0). (b) Dollars-as-compute composes across tokenizers but not across *hidden reasoning* — vendor default-reasoning is simultaneously billed cost and uncaptured capability lever; should be named a first-class confound alongside price arbitrage. (c) Seed-variance is not a real metric (no generation seeds are sent). (d) The $115 spend watchdog lives outside the repo.
- **Grok:** The most complete per-condition map of which arms are touched by which task-blind step, and the cleanest statement that reclassifying thinking spend as "behavior, not compute" would be changing the compute unit mid-experiment.

## Notable disagreement

**Cap-asymmetry remedy.** Grok and Fable lean toward equalizing
(one generous shared budget for all providers); Sol wants the
*visible-answer* cap equalized with vendor-native thinking room
plus full telemetry; Kimi argues the asymmetry is acceptable as
"same policy, not same number" (the temperature precedent) —
conditional on truncation telemetry and a decision-log entry.
All four agree on the prerequisites: finish-reason telemetry,
token-split recording, and an explicit `decisions.md` entry.

**Pilot fate.** Sol/Kimi/Fable: let the pilot finish as a
declared-descriptive artifact; Grok: fix the task-blind prompts
first. (The coordinating session had already paused the run
with A-columns complete; the marginal cost of patching before
resuming is small since B/C/D/D′/E rerun regardless.)

## Where the reviewers were wrong (verification notes)

- Fable's headline concern — gpt-5.4-mini silently truncating in
  the pilot data — is **refuted for this dataset** (zero
  cap-saturated calls at N=86 per subject). The structural
  criticism stands; the claimed contamination is absent.
- No other checked claim failed verification so far. Sol's
  sandbox/oracle finding and A-vs-B anchoring claim are queued
  for direct verification before the patch set is finalized.
