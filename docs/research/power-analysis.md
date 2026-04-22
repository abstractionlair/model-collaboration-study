# Pre-kickoff Power Analysis

> **Status: Drafted 2026-04-21.** The numbers below are the
> operational gate referenced in `experimental-design.md` §
> "Pre-declared middle-band fallback rule." Re-run
> `analysis/power_analysis.py` before Phase 1 kickoff to confirm
> the numbers still hold with any last-minute change to the
> utility curve, matrix size, or alpha.

## The gate

The Phase 1 design names a pre-declared fallback: if the primary
Protocol × Stratum interaction test has <80% power (α = 0.05) at
the Phase 1 N per stratum per condition under a fixed assumed
utility curve, the experiment is automatically collapsed to the
middle band and the primary test becomes a two-proportion
main-effect test there. Computing that power is what this
document does.

## Assumed utility curve

Protocol effect on success rate, absolute, relative to a
compute-matched single-model baseline (from
`experimental-design.md`):

|                | baseline | collab | effect |
|----------------|---------:|-------:|-------:|
| easy (60–70%)  |     0.65 |   0.60 | −5 pp  |
| middle (45–55%)|     0.50 |   0.60 | +10 pp |
| hard (30–40%)  |     0.35 |   0.35 |  0 pp  |

"baseline" here is the best compute-matched single-model
condition the multi-model protocol is being held against (B at
the same tier, per the Best-of-N discipline). The curve
encodes the strata hypothesis directly: collaboration slightly
degrades on easy, helps substantively on middle, adds nothing
on hard.

## Method

For each candidate N (task instances per stratum per protocol),
2,000 simulated datasets are drawn from the 6-cell design
(2 protocols × 3 strata), each cell's success count drawn as
`Binomial(N, p_cell)` under the utility curve above. On each
draw we fit two binomial GLMs — a reduced model with main
effects only (`P + S_easy + S_hard`) and a full model adding
the two interaction terms (`+ P·S_easy + P·S_hard`) — and take
the LRT statistic `2(ℓ_full − ℓ_red)`, referred to a χ²(2) null.
Power is the fraction of draws where the LRT p-value is below
α = 0.05.

Calibration check: under utility curves with no interaction
(either flat 0.5 across all cells, or a pure +10 pp main
effect), empirical rejection rates land at 0.054 and 0.062
respectively against a nominal 0.05 — within Monte Carlo
tolerance at n_sims = 2000.

Per-stratum two-proportion z-tests on the same draws give the
middle-band fallback's simulated power, plus easy / hard
single-stratum tests as diagnostics. An analytical
two-proportion calculation cross-checks the middle-band number.

Code: `analysis/power_analysis.py`. Raw grid:
`analysis/power_results.json`.

## Results

### Primary interaction test

Simulation-based power for the 2-df Protocol × Stratum
interaction LRT, 2,000 draws per N:

| N per cell | power (interaction) | MC SE  |
|-----------:|--------------------:|-------:|
|         25 |               0.116 |  0.007 |
|         50 |               0.153 |  0.008 |
|         75 |               0.213 |  0.009 |
|        100 |               0.267 |  0.010 |
|        150 |               0.376 |  0.011 |
|        200 |               0.493 |  0.011 |
|        300 |               0.647 |  0.011 |
|        400 |               0.819 |  0.009 |
|        600 |               0.931 |  0.006 |
|        800 |               0.978 |  0.003 |
|       1200 |               0.998 |  0.001 |
|       1600 |               1.000 |  0.000 |

Narrower refinement at 4,000 sims around the threshold:

| N per cell | power (interaction) | MC SE  |
|-----------:|--------------------:|-------:|
|        325 |               0.694 |  0.007 |
|        350 |               0.736 |  0.007 |
|        375 |               0.769 |  0.007 |
|        400 |               0.787 |  0.007 |
|        425 |               0.822 |  0.006 |
|        450 |               0.846 |  0.006 |

**Headline: the 80% threshold sits at N ≈ 425 task instances per
stratum per protocol.** At that N, each two-protocol × three-
stratum comparison consumes 6 × 425 = 2,550 task-instance
outcomes per comparison per tier (1,275 distinct instances if
both protocols run on the same task set).

### Middle-band fallback

Power for the two-proportion z-test comparing 0.50 vs 0.60
success rates in the middle band alone (N per arm):

| N per arm | power (analytical) | power (simulated) |
|----------:|-------------------:|------------------:|
|       100 |              0.296 |             0.298 |
|       200 |              0.528 |             0.544 |
|       300 |              0.695 |             0.709 |
|       400 |              0.808 |             0.823 |
|       600 |              0.937 |             0.945 |
|       800 |              0.978 |             0.977 |

**Headline: the middle-band fallback needs N ≈ 388 per arm
(analytical) / 400 per arm (simulated) for 80% power.** Cost in
task instances: 2 × 388 = 776 per comparison per tier.

### Per-stratum diagnostics

Simulated power for single-stratum two-proportion tests at the
utility-curve effect sizes:

| N per arm |  easy (−5 pp) |  hard (0 pp) |
|----------:|--------------:|-------------:|
|       100 |         0.120 |        0.053 |
|       400 |         0.320 |        0.054 |
|       800 |         0.559 |        0.042 |
|      1600 |         0.834 |        0.051 |

The easy band is meaningfully under-powered at any N realistic
for Phase 1; a reliable easy-band estimate requires roughly
1,500+ task instances per arm. The hard band stays at α, as it
should — there is nothing to detect at a 0 pp effect.

This matters for reporting: the interaction test can be
well-powered overall while the *per-stratum* estimate in the
easy band is not a reliable standalone finding. The design
already treats stratified estimates as pre-specified detail
rather than as independent confirmatory tests, which is the
right posture.

### Why not the usual 4× rule of thumb

Gemini's rough heuristic in the design-doc discussion was that
interaction tests need ~4× the instance count of a main-effect
test at equivalent power. Here the interaction test reaches
80% at N ≈ 425 per cell and the middle-band main-effect test
reaches 80% at N ≈ 400 per arm — per-cell, they are nearly
identical. The 4× factor does show up in **total instances**
(interaction: 6 × 425 ≈ 2,550; middle-band: 2 × 400 = 800; so
~3× more total). The utility curve we pre-declared happens to
concentrate strong signal in the middle band and add a
moderate opposite-signed signal on easy, which the 2-df LRT
exploits well. If the utility curve were flatter (e.g., +5 pp
in middle, 0 elsewhere), the interaction test would need
substantially more.

## Implications for Phase 1 N and the fallback decision

The Phase 1 matrix has 5 multi-model conditions (B, C, D, D', E)
× 2–3 budget tiers (A only at $X; B at $X, $2X, $4X; others at
$2X, $4X) × 3 buckets (SWE-bench Verified, LiveCodeBench, BFCL)
× 3 strata. The question is whether each
protocol-vs-compute-matched-baseline comparison at a given tier
has ≥80% power across the three strata for the interaction test.

**Binding constraint by bucket:**

- **SWE-bench Verified** has 500 instances total. Stratified
  into thirds by one-shot baseline difficulty, that's ~167 per
  stratum. 167 is well below the 425 needed. SWE-bench
  *cannot* support the interaction test at 80% power even at
  maximum capacity — the fallback triggers for SWE-bench
  purely on instance availability, before dollar cost enters
  the picture.
- **BFCL** has thousands of instances across the five widened
  categories; 425 per stratum is feasible on availability.
  The binding constraint here is *headroom*, not N: the 2026-04-21
  widening session confirmed 100% ceiling on Condition A across
  all live categories at small N, so the baseline rate has no
  room to reflect a 0.50 middle stratum without either
  higher-difficulty subsets or harder categories yet to be
  added.
- **LiveCodeBench** instance counts sit between the two and
  the bucket is not yet adapted. Difficulty stratification
  ought to be achievable but needs confirmation once the
  adapter lands.

**What the rule as written implies.** The design's fallback
trigger is keyed on "estimated power below 80% at the Phase 1
N per stratum per condition." On SWE-bench at the natural
maximum N per stratum (~167), the interaction test has
roughly 42% power (interpolating the grid). That is below
threshold and the middle-band fallback triggers for that
bucket. The rule does not require the same call across all
buckets, but uniform fallback is simpler to pre-register and
to report.

**Recommendation.** Trigger the middle-band fallback for
Phase 1 as a whole, not on a per-bucket basis. The argument:

1. SWE-bench forces the fallback for structural reasons
   (bench size vs. interaction-test N).
2. Running the full interaction test on BFCL and LiveCodeBench
   only, while SWE-bench runs the fallback, produces a split
   primary test that is hard to pre-register cleanly and
   harder to report as a single Phase 1 result.
3. The middle band is exactly where the strata hypothesis
   predicts collaboration actually helps. A confirmatory
   Phase 1 test concentrated there is consistent with the
   design's narrative.
4. The easy and hard strata are not discarded — they can be
   observed descriptively in Phase 1 and promoted to a
   full-interaction Phase 2 test if the middle-band result
   supports pursuing collaboration at all.

This is a recommendation for the Phase 1 kickoff decision, not
a design change. The call belongs at kickoff, once the dollar
ceiling is pinned and per-bucket calibration on the subject
models is run (one-shot success rates per bucket, to confirm
the middle band actually exists at the target rates for the
planned subjects).

## What this analysis does not decide

- **The exact middle-band N per arm per condition per tier.**
  400 per arm gives 80% power for a single protocol-vs-baseline
  comparison. The matrix has 5 protocol comparisons × 2 tiers =
  10 such comparisons per bucket; multiple comparisons and
  shared task instances across conditions change the picture.
  This is a task for the experiment-runner planning work once
  the dollar ceiling is set.
- **Multiplicity correction** across the 10 comparisons per
  bucket. A Bonferroni-style adjustment to α = 0.005 raises
  the required N per arm to ~620 analytically; a less
  aggressive FDR procedure would land between 400 and 620.
  Pre-register the adjustment policy before kickoff.
- **Per-bucket calibration.** The utility curve's absolute
  rates (0.35 / 0.50 / 0.65) are placeholders anchored to the
  strata hypothesis. Per-bucket one-shot rates on the actual
  subject models may not span the target bands cleanly (the
  BFCL ceiling is direct evidence that this is a live
  problem). Calibration runs on the subject models per bucket
  are still needed to confirm the middle band is reachable
  and to select within-bucket subsets for each stratum.

## Reproducing

```
python3 analysis/power_analysis.py
```

No external API calls; pure simulation against `numpy` and
`statsmodels`. Runs in ~75 s on a laptop at the default grid
size. Raw output lands in `analysis/power_results.json`.
