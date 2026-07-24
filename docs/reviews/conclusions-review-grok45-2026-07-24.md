# Review: Pilot conclusions given the data (round 8)

**Reviewer:** Grok 4.5 (xAI / opencode)  
**Date:** 2026-07-24  
**Artifacts reviewed / analyses run:**
- `docs/research/pilot-findings.md` (artifact under review)
- `docs/reviews/review-brief-round8-2026-07-24.md`, `docs/status.md`, `docs/reviews/synthesis-round7-2026-07-23.md`, `docs/research/experimental-design.md`, `docs/research/power-analysis.md`
- Raw: `data/mini_bench_runs/pilot-lcb-2026-07-24T20-46-16.json` (688 rows), `data/livecodebench/test6.jsonl` (difficulty labels), calibration JSON (structure only)
- Independent recomputation: condition means/costs; paired bootstrap 10k on reported pairs + extras; Holm on the five reported CIs; strict McNemar-style contingency; oracle selection ceiling; cost-sensitive router; $/strict and $/frac-unit; A(gemini) cap-proximity split (output_tokens ≥ 97.5% of 32,768); D−G decomposition by cap/stratum; D vs best-of-A generation residual; C selection regret; LOO on B−A(gpt); medium/hard splits

## Summary assessment

The negative headline — collaboration does not beat the best single model here — is directionally right and mostly earned. Several load-bearing phrasings are not: “matched compute,” “statistical parity,” “only significant positive” without multiplicity, and “consistent with the strata hypothesis” once D’s apparent hard-band lift is decomposed into Gemini truncation recovery.

## Claim-by-claim verdicts

1. **“No collaboration condition beats the best single model at matched compute.” — OVERCLAIMED (direction SUPPORTED)**  
   Recomputed means match the table (A(gemini) 0.797, D 0.816, C 0.605, E 0.638, B 0.617; total $62.00). No collab mean exceeds A(gemini) with a CI excluding zero; E and C are clearly worse. But **matched compute is not what was run against A(gemini)**: D is 3.90× $/task, E 2.15×, B 0.47×, D′ 0.51×. The only near-matched collab arm is **C at 1.19×**, and it loses by −0.193 [−0.285, −0.101]. B is realized-cost-matched to D′ only (~$0.036 vs $0.039), as the doc admits in caveats but not in the headline sentence. Honest form: *no collab beat A(gemini); the near-cost comparator (C) lost large; the only near-score comparator (D) cost ~4× for a nonsignificant blip.*

2. **“D achieves statistical parity with A(gemini) at 3.9× cost.” — OVERCLAIMED**  
   Bootstrap: D−G = **+0.0186 [−0.070, +0.110]**, p≈0.68 — **inconclusive**, not parity. Parity language implies a tight equivalence finding; this CI is compatible with −7pp harm or +11pp help. On **strict** pass, D is **behind**: −0.012 [−0.116, +0.093] (59/86 vs 60/86); contingency both 49 / D-only 10 / G-only 11 / neither 16. Efficiency: gemini **$0.110**/strict solve vs D **$0.438**. More important: the +0.019 point estimate is a **mixture**. On 60 tasks with Gemini not near the 32k cap, D−G = **−0.072 [−0.166, +0.013]**; on 26 near-cap tasks, D−G = **+0.228**. On 60 tasks where Gemini scored 1.0, D averages 0.900 (11 destructions). Strip truncation-recovery credit on the 11 near-cap zeros and the point estimate flips to about **−0.05**. “Parity at 3.9×” is the wrong summary of “expensive, inconclusive, and cap-confounded.”

3. **“B’s +0.094 over its own base model is the pilot’s only significant positive.” — SUPPORTED with multiplicity caveat (borderline OVERCLAIMED)**  
   Recomputed B−A(gpt) = **+0.093 [+0.015, +0.175]** (n=85), p≈0.024; strict +0.141 [+0.059, +0.235]. LOO means stay in ~0.08–0.11 (not a single-task fluke). B−D′ +0.028 [−0.031, +0.088] n.s. — correct. **But** among the five CIs the doc prints as a family, Holm–Bonferroni at α=0.05: C−G and E−G survive; **B−A(gpt) does not** (p=0.024 > 0.05/3≈0.0167). Uncorrected “only significant positive” is defensible as descriptive; as an inferential claim it overreaches. Also E−A(gpt) is +0.104 [+0.022, +0.190] uncorrected — another positive vs a weak base that the “only” framing sidesteps by anchoring everything to gemini or to B’s own base without saying so cleanly.

4. **“D vs D′ (+0.228) is dominated by pool composition, not structure.” — SUPPORTED**  
   D−D′ = **+0.228 [+0.140, +0.322]**; D−G ≈ 0; D′−A(gpt) = +0.064 n.s.; B−D′ ≈ 0. Structure-with-same-pool (B vs D′) does not win; adding Gemini does. Corr(D, A_gemini)≈0.34 vs corr(D′, A_gpt)≈0.58 — D is not a thin wrapper on Gemini either, but the **gap D−D′ is not a clean heterogeneity-structure effect**. The doc’s preferred reading (look at D vs A(gemini); C destroyed the same drafts) is the right one.

5. **Ceiling analysis (+0.056; C realized none) — SUPPORTED; scope mostly honest**  
   Best-of-3 A drafts = **0.8538** vs gemini 0.7974 → **+0.0564**. C−oracle mean regret **−0.252**; C matches best-of-A fraction on only **41/85** tasks. Scope sentence (binds C; B has a different ceiling; D/E can generate) matches the data and Scott’s correction in status. Doc correctly notes part of the ceiling is truncation artifact; true selection headroom is lower. Missing one sharpening: C is not just “no headroom capture” — it often lands **below every A draft** (39/85 with C < all three), i.e. active damage / off-pool behavior, not merely weak picking.

6. **“Consistent with (not confirmation of) the strata hypothesis.” — OVERCLAIMED / confounded**  
   Pool is easy for the true best subject (0.797) — correct. Easy-band harm is real: on 66 tasks with A(gemini)≥0.7, D−G = **−0.111** (CI excludes 0). The suggestive “hard helps” pattern is **not clean strata evidence**: of 16 tasks with A(gemini)≤0.5, **11 are near-cap zeros**; only 3 are clean hard_lo. D’s +0.51 on hard_lo is largely **recovery when Gemini blanks at the cap**, plus a few generation wins (e.g. arc191_c, arc195_e). Pre-registered utility curve was about true difficulty strata vs compute-matched baseline, not instrument-failure recovery. Underpowered disclaimer is good; “direction matches” overstates once the hard tail is opened.

7. **Robustness-direction argument (open issues bias against best single / toward fake collab wins ⇒ negative headline robust). — PARTIALLY SUPPORTED**  
   Correct about **direction of bias for a “collab wins” claim**: cap suppresses Gemini; collab arms can route around a truncated member; unsandboxed execution could inflate scores. So “we did not find a collab win” is robust to those biases. **Incorrect if read as ratifying the full narrative**, especially D≈gemini parity: that parity is exactly what the cap artifact manufactures. Unsandboxed execution is symmetric across conditions only if exploitation risk is similar; collab prompts with more code/revisions are not obviously lower risk. Single seed / no generation seeds cuts both ways. Net: **negative capability claim is robust; D-parity and strata-consistency are not.**

8. **Oracle router: 0.832 at 49% of all-gemini cost. — SUPPORTED (define the rule)**  
   Reproduced exactly with: *among A drafts with fraction ≥ A(gemini), pick cheapest* → mean_frac **0.832**, cost ratio **0.490**, **48/86** routed off-gemini. A pure best-of-3 oracle is **0.854** at similar cost if ties break on price. The corollary (cost-side objective is live on this pool) holds. Say “quality-preserving cost router,” not bare “oracle router,” so readers don’t assume best-of-pool quality at that number.

## Statistical methodology findings

1. **Paired bootstrap on per-task mean_frac differences is appropriate** for this paired design (same 86 tasks across conditions). 10k resamples; my CIs match the doc within MC noise.

2. **Multiplicity is unhandled.** Five highlighted CIs share tasks and baselines. Under Holm on those five, only C−G and E−G remain significant; **B−A(gpt) falls out**. Calling B the “only significant positive” without that caveat is inferentially sloppy for anything that will be quoted.

3. **Comparisons are not independent** (shared tasks, shared A(gemini) baseline, D/C/E share draft pool structure). Fine for description; overconfident if treated as five independent discoveries.

4. **Strict vs fractional:** Primary metric is mean_frac (locked). Doc under-discusses that **D “wins” on mean_frac point estimate and loses on strict**. For a blog, that discrepancy needs one explicit sentence, not burial in the table.

5. **Test-case clustering ignored.** mean_frac averages many private tests per task; bootstrap at task level is reasonable but not the same as a test-case-clustered or beta/binomial model the design’s power note gestured at. With N=86 descriptive pilot this is acceptable if claimed limits stay soft.

6. **Single seed, single provider replicate, no generation seeds** (round-7): variance understated; B’s lift especially needs a second seed before strong mechanism language (“the variance-harvest mechanism works”).

7. **Denominator:** one abort excluded from A(gpt) (85 vs 86) — correct and documented. Good.

8. **“Dollars per solved task”** under fractional scoring is a strict-pass construct; doc uses it for gemini vs D appropriately as a headline efficiency gloss, but should not pretend it is the pre-registered primary.

## Missing analyses (with results)

1. **Cap decomposition of D−A(gemini)** (decision-critical):  
   - not near cap (n=60): D−G = **−0.072 [−0.166, +0.013]**  
   - near cap (n=26): D−G = **+0.228**  
   - Gemini perfect (n=60): D mean 0.900 (−0.100)  
   Overall +0.019 is not a stable structural finding.

2. **True near-matched collab vs best single = C vs A(gemini)** at 1.19× cost: **−0.193**, decisive loss. This is the pilot’s best compute-matched collab test and belongs in the headline block.

3. **Holm on the five reported CIs:** B−A(gpt) does not survive; uncorrected uniqueness claim weakens.

4. **Generation residual:** D − best(A drafts) = **−0.038** overall; **−0.074** on non-cap tasks. Net, D does not beat the one-draw pool ceiling; any D>G wins are outnumbered by D destroying good Gemini answers on easy tasks (14 vs 15 task wins on raw D>G counts; 11 destructions when G=1).

5. **C regret:** mean best−C = 0.252; equals best on 41/85 — worse than “recovered none of +0.056”; often worse than the worst draft path.

6. **Router rule sensitivity:** ≥gemini-then-cheapest → 0.832 @ 49% cost (doc); pure max-frac → 0.854. Specify rule.

7. **B cost-match honesty:** n=8 matches D′ dollars, not A(gemini). Matching A(gemini) dollars with B-style sampling would need ~n≈17 at observed $/sample; matching D would need ~n≈67 — so D never faced a Best-of-N discipline peer (round-7 finding stands in the results, not only the plan).

8. **Medium vs hard (LCB labels):** no qualitative rescue of collab; D−G n.s. in both bands; B−A(gpt) concentrates a bit on hard (+0.105 vs +0.065 medium).

## Publishability

Object to these if quoted verbatim (fixes in italics):

| Sentence / phrase | Problem | Fix |
|---|---|---|
| “No collaboration condition beats the best single model **at matched compute**.” | D/E not matched to A(gemini); tiers unenforced. | “No collaboration condition beat A(gemini). The only near-cost collab arm (C, ~1.2×) lost by ~19pp; D reached a nonsignificant +2pp at 3.9× cost.” |
| “D achieves **statistical parity** with A(gemini)” | Wide CI, p≈0.68; strict lean negative; cap-confounded. | “D was statistically indistinguishable from A(gemini) on mean_frac (+0.019, 95% CI crosses 0), at 3.9× cost — not an equivalence win.” |
| “B’s +0.094 … is the pilot’s **only significant** positive” | No multiplicity control; fails Holm in the printed family. | “B’s +0.094 vs its own base was the only uncorrected CI excluding zero among the five highlighted comparisons; it does not survive Holm adjustment.” |
| “the variance-harvest mechanism **works**” | One seed, N=86, multiplicity-fragile. | “repeat sampling helped this base model on this pool (descriptive; confirm with more seeds).” |
| “**Consistent with** … the strata hypothesis” | Hard-band lift confounded with Gemini truncation recovery. | “Easy-band collab harm is visible; hard-band patterns are entangled with cap failures and are not clean support for the pre-registered curve.” |
| “All open instrument issues bias against the best single model … so the **negative headline is robust**” | True for “no collab win”; false comfort for D-parity / strata. | Split: negative capability headline robust in direction; D≈G and strata-consistency are not. |
| “An **oracle** per-task router achieves 0.832” | Ambiguous oracle. | “A quality-preserving router (cheapest draft with score ≥ Gemini’s) achieves 0.832…” |

Table itself is fine if CIs and $ ratios stay attached. Failure accounting and harness history are strengths — keep them near the claims.

## Recommendation

**Publish with edits.**

Do not re-run the pilot for the blog. Do rewrite the headline block around: (i) C as the real near-matched loss, (ii) D as expensive+inconclusive+cap-confounded rather than “parity,” (iii) B as a promising but multiplicity- and seed-fragile same-model sampling lift, (iv) strata language demoted until hard-tail tasks are separated from truncation. After those edits, a second full review round is optional; a thin pass on the revised paragraphs is enough.
