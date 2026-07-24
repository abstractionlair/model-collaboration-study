# Review: Pilot conclusions given the data (round 8)

**Reviewer:** Claude Fable 5 (fresh context)
**Date:** 2026-07-24
**Artifacts reviewed / analyses run:** `docs/research/pilot-findings.md`; raw log `pilot-lcb-2026-07-24T20-46-16.json` (688 rows); `calibration-all-2026-04-24T23-37-45.json`; context docs (status, experimental-design, synthesis-round7, power-analysis). Independent Python: reproduced all 8 headline aggregates; re-ran the 5 paired bootstraps (10k, seed 0); Bonferroni-corrected + p-valued the B comparison; strict-vs-fractional paired bootstraps for D and C; reconstructed the ceiling and the oracle router; Gemini output-token cap forensics; a cap-sensitivity decomposition of the D-parity result; D−D′/D−haiku bootstraps; correlation matrix of the five diff vectors; April complementarity-ceiling recompute.

## Summary assessment
Every quantitative claim in the doc reproduces exactly from the raw data, and the core negative conclusion is not only supported but strengthened by an analysis the write-up did not run. The problems are in the framing of three sentences ("at matched compute," "the pilot's only CI-excluding-zero gain," and the unqualified robustness claim) plus one material missing decomposition — all fixable in-place, none requiring re-analysis.

## Claim-by-claim verdicts

1. **"No collaboration beats the best single model at matched compute"** — OVERCLAIMED (wording); underlying conclusion SUPPORTED. No collaboration-vs-single comparison in the pilot is compute-matched: D/E/C cost 3.90× / 2.15× / 1.19× A(gemini) respectively, and the one genuinely matched pair (B↔D′, $0.036 vs $0.039) is homogeneous-gpt, not collaboration-vs-single. The true matched-compute test (an A⁺ inference-scaling arm giving Gemini D's budget) was not run. The honest — and actually stronger — statement is "no collaboration condition beats the best single model *even at 1.2–3.9× its compute*."

2. **"D achieves statistical parity with A(gemini) at 3.9× cost"** — SUPPORTED but incomplete. +0.019 [−0.068,+0.109] (n.s.) is correctly read as parity; the sign is symmetric across metrics (strict −0.012 [−0.116,+0.093], also n.s.; D solves 10 tasks gemini misses, loses 11 gemini solves). But the parity is entirely a cap-rescue artifact: on the 11 tasks where Gemini's single shot truncated to fraction 0.000, D scores 0.552 (5/11 strict); remove those 11 and D−gemini flips to **−0.060 [−0.143,+0.017]**. D's apparent parity is "the ensemble rescuing the dominant member's token-cap failures," not structure adding value — and the doc should say so.

3. **"B's +0.094 is the pilot's only significant positive; five CIs"** — OVERCLAIMED, two ways. (a) "The pilot's only CI-excluding-zero gain" is literally false: D−D′ = +0.228 [+0.136,+0.320] and D−haiku = +0.271 [+0.174,+0.367] also exclude zero (the doc discusses D−D′ elsewhere, but the sentence as written is wrong). (b) B−A(gpt) is nominal only: two-sided bootstrap p ≈ 0.023, and its Bonferroni-5 (99%) CI is [−0.011,+0.201] — it does **not** survive multiplicity correction across the five reported comparisons. "The one significant positive" needs the qualifier "nominal; does not survive multiplicity correction."

4. **"D vs D′ (+0.228) dominated by pool composition, not structure"** — SUPPORTED. +0.228 [+0.136,+0.320]; the matched-cost structural contrast (B vs D′) is only +0.028 (n.s.); D−haiku is +0.271. The heterogeneity gain tracks Gemini's presence, as claimed.

5. **Ceiling analysis (+0.056 selection headroom; C realized none)** — SUPPORTED. Oracle best-of-pool over the 3 A drafts = 0.8538 vs gemini 0.7974 = +0.0564 exactly. C's judge returned 0.605 — below even "always take Gemini" (0.797), i.e. negative recovered headroom. Scope limits (binds C only; part is a cap artifact) are correctly stated. Worth noting claims 4/5/6 are largely the *same* headroom fact viewed three ways, not independent evidence.

6. **"Consistent with (not confirmation of) the strata hypothesis"** — SUPPORTED; appropriately hedged. Pool is easy-band for the best subject (0.797), utility curve predicts neutral-to-harmful, that is what was observed; the doc correctly flags it as underpowered and directional. Note this is near-tautological with the ceiling (easy band → high base rate → low headroom → no room to gain).

7. **Robustness-direction argument** — SUPPORTED in thrust (and my cap decomposition strengthens it: removing Gemini's truncation failures moves D from +0.019 to −0.060), but the universal "**all** open instrument issues bias against the best single model or toward fake collaboration wins" is too strong. The cap also suppresses the Gemini-bearing collaboration arms (D/C/E logged 38/15/23 truncated calls), and unsandboxed execution inflates every condition's score symmetrically, not collaboration preferentially. The headline direction is robust; "all … toward fake collaboration wins" is not.

8. **Routing corollary (oracle router 0.832 at 49%)** — SUPPORTED, reproduces exactly. The router = "cheapest model achieving ≥ Gemini's per-task fraction" gives 0.8323 mean_frac at 49% of all-Gemini cost, 48/86 routed to cheaper models. It is explicitly an oracle (ground-truth-dependent upper bound), and the doc labels it so.

## Statistical methodology findings
1. Paired task-level bootstrap on per-task fraction differences is appropriate and reproduces to Monte-Carlo noise. Task-level (rather than test-case-level) is the *conservative* correct unit given strong within-task test correlation — a genuine strength that goes unstated; test-case-level clustering would shrink CIs anti-conservatively.
2. Multiplicity is under-handled. Five comparisons are reported and the "only significant positive" framing is itself a selection over them. They are not independent: the three vs-gemini diffs correlate r ≈ 0.46–0.51 (shared reference), the two B diffs r = 0.36. B−A(gpt) fails Bonferroni-5; the negatives (C, E) survive easily.
3. Single seed / single generation replicate: the bootstrap captures between-task variance only, treating each realized per-task fraction as fixed. Vendor-default temperature with no generation seeds means true uncertainty is wider than the reported CIs — most relevant for B, whose 8 samples are one uncontrolled draw.
4. Strict-vs-fractional handled honestly but not explicitly. D's point estimate flips sign between metrics (frac +0.019 / strict −0.012), both n.s. — the doc prints both numbers but never names the flip; parity survives either metric, so no misrepresentation. C is far worse on strict (−0.314 [−0.430,−0.198]) than on frac (−0.193); reporting frac is the more C-charitable, pre-registered choice.
5. Abort/denominator rule applied consistently (abort excluded; A(gpt) N=85, mean_frac 0.529). Verified.

## Missing analyses (with results if you ran them)
1. **Cap-sensitivity of the D-parity result (most decision-relevant omission).** Excluding Gemini's 11 cap-truncated-to-zero tasks, D−gemini = −0.060 [−0.143,+0.017]; D scores 0.552 on exactly those 11 tasks. The single most-quoted collaboration number (D "parity") is a token-cap rescue artifact and should be decomposed in the write-up.
2. **Multiplicity-corrected inference for B.** Bonferroni-5 99% CI [−0.011,+0.201] includes zero; sign test 32 wins / 14 losses / 39 ties; bootstrap p ≈ 0.023.
3. **D−D′ and D−haiku bootstraps** — both exclude zero (+0.228, +0.271), directly contradicting the "only CI-excluding-zero gain" wording.
4. **$/solved beyond the D-vs-gemini pair.** B costs $0.091/solved vs Gemini $0.110 — a condition *beats* the best single model on the doc's own "headline efficiency metric." The doc's efficiency narrative (gemini vs D only) should acknowledge this Pareto point rather than imply the single model dominates efficiency universally.
5. **April complementarity recompute.** Ceiling = +0.111 (matches the "marginal green light"), best subject = haiku 0.606 (not gpt 0.539). Gemini-2.5-flash = 0.023 there vs gemini-3-flash 0.797 here — so the best-subject "flip" conflates the truncation fix with a 2.5→3 model upgrade; the pilot cannot attribute the flip to the truncation bug alone, and caveat 1's "substantially artifact" slightly overstates the bug's isolated role.

## Publishability
- "No collaboration condition beats the best single model at matched compute." → Reword: "…even at 1.2–3.9× the compute," or add that the genuine compute-matched (A⁺) baseline is not yet run. As written it names a comparison the pilot did not perform.
- "B's +0.094 … is the pilot's only CI-excluding-zero gain." → Factually wrong (D−D′, D−haiku also exclude zero) and multiplicity-fragile. Reword to "the only significant gain not attributable to pool composition, and nominal only — it does not survive multiplicity correction."
- "D achieves statistical parity with A(gemini)." → Publishable only with the cap-rescue caveat attached; if the blog leads with this number, the −0.060-on-clean-tasks decomposition is mandatory, not optional.
- "All open instrument issues bias against the best single model or toward fake collaboration wins." → Drop "all"; the cap suppresses the collaboration arms too and the execution issue is symmetric.

## Recommendation
**Publish with edits.** The data fully backs the headline and the core negative is robust (strengthened, once the cap-rescue tasks are removed). The four wording/completeness fixes above — matched-compute phrasing, the "only significant positive" claim plus a multiplicity note, the D-parity cap decomposition, and softening the universal robustness claim — are required before the blog quotes any of these sentences verbatim, but none require re-running the pilot.
