# Review: Model-collaboration study — plan and code (round 7)

**Reviewer:** Grok 4.5 (xai/grok-4.5)  
**Date:** 2026-07-23  
**Artifacts reviewed:** `CLAUDE.md`, `docs/status.md`, `docs/decisions.md` (incl. 2026-07-04 kickoff), `docs/research/experimental-design.md`, `docs/research/calibration-findings.md`, `docs/research/power-analysis.md`, `docs/reviews/review-brief-2026-07-23.md`, `src/ir/`, `src/executor/{api_client,interpreter,runner paths}`, `src/experiment/{phase1,prompts,runner,spec,benchmarks/livecodebench}`, `src/protocols/{conditions,reconcile}`, `scripts/run_pilot.py`

## Summary assessment

The design is unusually careful for a multi-model collaboration study: macro-model framing, Best-of-N discipline, D′ heterogeneity control, selector-as-oracle avoidance, and a pre-registered interaction/fallback plan are all real strengths. The most important issue is that **today’s Gemini harness fix plus several still-open measurement gaps (PickOne without task context, E still task-blind, budget caps unenforced, infra aborts scored as failures) put the pilot and any near-term write-up on soft ground until recalibration and a small integrity patch set land.**

## Specific findings

1. **PickOne omits the task (measurement integrity — high).**  
   `src/experiment/prompts.py:172-178` and `src/executor/interpreter.py:592-618` show candidates to the judge with no `{query}`. This is the same failure class as the 2026-04-21 revise-context bug, now on **B and C** — i.e. the compute-matched single-model baseline and the diversity-only screen. For free-form code, a task-blind judge mostly pattern-matches completeness/authority. **Direction:** add the original task to `_PICK_ONE_USER` and pass `production_query` (or interpreter `query_text`) at the PickOne call site; re-smoke B/C.

2. **Condition E peer review still hides the task (faithfulness / integrity — high).**  
   D was moved to `ALL_VISIBLE` (`src/protocols/reconcile.py:72`); E still uses `PEERS_GROUPED` (`src/protocols/conditions.py:177`). E reviewers are asked for Correctness without the problem. **Direction:** default E to `ALL_VISIBLE` for the same reason as D; keep `PEERS_GROUPED` only as an explicit ablation.

3. **Budget-cap semantics vs realized D cost are currently incoherent (design–ops — high).**  
   Design: tiers are **caps**; over-cap models are truncated or excluded (`experimental-design.md` Compute Budget Structure). Runner: **does not enforce caps** (`src/experiment/runner.py:8-10`). Pilot: B n=8 matched to **D′**, while D is ~6× D′ from Gemini thinking and is still compared in-matrix. Under the written design, uncapped D is not a valid same-tier arm. **Direction:** decide explicitly (a) enforce caps and truncate/exclude over-cap D, or (b) amend design to report uncapped realized cost with B matched per comparator; do not silently do neither.

4. **Vendor thinking spend is compute under the project’s own unit (design — high).**  
   Compute is **USD API spend**. Thinking tokens billed as output (`api_client.py:405-412`) correctly enter dollars. Exempting them from matching while keeping dollar-matched claims would redefine the DV after seeing the data. **Direction:** treat thinking as billable compute; report a decomposition (visible vs thoughts tokens) as analysis, not as a matching carve-out.

5. **Per-vendor output-cap asymmetry violates a locked interface constraint (confound — high).**  
   Design requires the same max output length across providers (`experimental-design.md` Common Interface Constraints). Implementation: Google gets `8 * max_tokens` (32768), others 4096 (`api_client.py:383-386`). The pre-fix shared 4096 was a worse bug (silent truncation). **Direction:** prefer equalizing a high shared completion budget for all providers and letting dollar-matching absorb cost differences; if vendor-native thinking regimes stay asymmetric, amend the design text and pre-register that asymmetry.

6. **Middle-band calibration is multiply stale (ops — high).**  
   Calibration used `gemini-2.5-flash` under a truncating harness; subjects are now `gemini-3-flash-preview` under a fixed harness; smoke suggests Gemini may dominate LCB. Middle band is defined by **best subject’s** one-shot rate (`experimental-design.md` Task difficulty strata). A pool where best≈0.90 is not a middle band. **Direction:** use pilot A×3 only to re-rank; then re-select harder subsets / expand releases until **current** best lands ~0.45–0.55 mean_frac; do not redefine “middle” as “where the weaker two sit.”

7. **Infra failures are scored like capability failures (design violation — medium-high).**  
   Design: infra failures are retried, not scored as task failures, and not billed to the capability budget. Runner catches `InfrastructureError`, sets `aborted=infra_failure`, `passed=False`, `fraction=0.0` (`runner.py:120-147`). Pilot `summarise()` includes those zeros in mean_frac. Multi-call arms (D/D′/E) have more infra surface → mechanical bias against collaboration. **Direction:** exclude infra-aborted items from success aggregates; retry or requeue; never fold them into protocol pass rates.

8. **ParScore parse failure → hard-coded 0.5 (measurement — medium).**  
   `interpreter.py:564-571`: failed confidence parses become 0.5, not an AST policy / seeded fallback. That flattens D/D′ WeightedVote toward noise-ties. PickOne has `ParseFailurePolicy`; scores do not. **Direction:** align with explicit policy (random / raise / drop), telemetry already exists.

9. **PickOne candidate order is deterministic (bias — medium).**  
   Candidates are emitted in `subject_models` / sample order with no seed shuffle (`interpreter.py:596-598`). Position bias can favor early vendors or early samples in B. **Direction:** shuffle under the run seed; record permutation in the trace/manifest.

10. **Power analysis and scoring model are out of sync (stats — medium).**  
    Kickoff chose LCB `mean_fraction`; power analysis is binomial GLM / two-proportion on binary success (`power-analysis.md`). Decision log correctly flags test-case-level binomial or beta regression as kickoff work — it is still undone. **Direction:** re-run power under the actual outcome model before any confirmatory N commitment; until then treat N≈400 as indicative only.

11. **Phase 1 is a screen, not a four-axis isolation (design honesty — medium, not a bug).**  
    RQ names heterogeneity, topology, critique format, round count; Phase 1 only cleanly isolates heterogeneity (D′→D) plus coarse family screens. The design already says this — keep it loud in any write-up. **Direction:** no change to matrix; forbid language that Phase 1 “identified which of the four axes drive gains.”

12. **C/E judge and meta-reviewer pinned to `best_model` (interpretive confound — low-medium).**  
    Peer-LLM aggregation / meta synthesis always uses the calibrated best subject (`phase1.py`, `run_pilot.py`). That is defensible as “strongest available peer” but is not a neutral peer draw and couples “best model’s taste” into C/E. **Direction:** name it; optional ablation with rotating or weaker judges later.

13. **Pilot is single-seed, N=86, no run-manifest schema yet (ops — expected).**  
    Fine for a machine/descriptive pilot; not fine for variance or confirmatory claims. Checkpointing and fail-loud unpriced models (`runner.py:153-167`) are good.

14. **What looks solid (credit where due).**  
    IR/executor split; identity memoization; D peer-revise (not self-review); E FuseWithCritiques shape; selector not using executable GT; thinking tokens now billed; Gemini truncation fixed; pricing gates; telemetry on parse/tie; LCB private tests not in query; revise/D task-context fix. Prior review rounds clearly improved the system.

## Answers to the four posed questions

1. **Invalid middle-band / best-subject after the Gemini fix — what to do?**  
   **Re-run harder-subset selection (and pool expansion) against the fixed harness; do not re-anchor best_model from n=3 smoke; do not “accept Gemini best with others mid-band” as the middle band.**  
   - Pilot A×3 @ N=86: descriptive re-ranking only.  
   - Then Condition-A calibration on the expanded medium+hard (and harder-within-hard) pool until **current best** mean_frac ≈ 0.45–0.55.  
   - Re-anchoring best to Gemini while leaving a saturated pool abandons the pre-registered band definition and weakens the fallback test (effect size assumptions were for baseline≈0.50, collab≈0.60).  
   - Expanding/re-stratifying preserves the fallback test’s estimand; only the task IDs and best_model label update. Document that April calibration is historical, not operative.

2. **B dollar-matched to D′ rather than D; is thinking “compute”?**  
   **Matching B→D′ is sound for B↔D′ and as a lower-spend control; it is not sufficient for a Best-of-N claim against D (or E) if those arms spend ~6× more.** Under dollar denomination, **vendor thinking spend is compute** and must enter matching and/or caps. Report thinking vs visible tokens as a finding; do not match it away and still claim compute-matched wins for the expensive arm. Preferred policy: enforce tier caps (design-as-written) *or* pre-register uncapped realized-cost comparisons with B retuned per comparator. The running pilot’s B=n=8 choice is acceptable **only** if write-ups treat D’s extra spend as unmatched cost, not as a free heterogeneity win.

3. **Gemini 8× output budget vs 4096 elsewhere?**  
   **A real confound under the current locked “same max output length” rule — not an acceptable silent asymmetry.** Best fix: raise a shared high completion bound for all subjects and rely on dollar accounting; second-best: keep vendor-native thinking but amend the design, log visible vs thought tokens, and run a sensitivity check (e.g. Gemini with thinking disabled or tighter cap) before confirmatory claims. Leaving the asymmetry unnamed while arguing protocol structure drove gains is not defensible.

4. **What would be an overclaim in a public pilot write-up (N=86)?**  
   Overclaims: statistically significant protocol effects; confirmation of the strata utility curve; “heterogeneous collaboration beats the best single model at matched compute”; generalizable effect sizes; Phase 1 confirmatory results; any claim that B was compute-matched to D; any claim that calibration still places the best subject in-band.  
   Fair claims: end-to-end harness works; cost structure (thinking-token dominance, per-condition $/task); descriptive pass/mean_frac tables with uncertainty; discovery and fix of Gemini truncation/under-billing; that April middle-band anchors are invalidated and recalibration is required; qualitative failure modes (if traced). Frame as **engineering + calibration pilot**, not as the pre-registered test.

## Recommendation

**Revise and re-review**

Do not rethink the research question or macro-model matrix. Before treating pilot numbers as scientific signal or launching confirmatory Phase 1:

1. Fix PickOne task context and E visibility (same bug family as the known D fix).  
2. Decide and document budget policy for thinking-heavy D (caps vs uncapped + per-arm B matching).  
3. Stop scoring infra aborts as capability failures.  
4. Equalize or explicitly re-register output-budget policy.  
5. Recalibrate middle band on the fixed harness; re-run power under mean_fraction.  

After those, a short re-review focused on measurement integrity is enough; the architecture does not need another ground-up redesign.
