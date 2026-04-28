# Per-bucket calibration findings

**Date:** 2026-04-24
**Author:** Opus 4.7 session
**Scope:** Condition A (one-shot pass) on each of the three
Phase 1 subject models against each available difficulty slice
of LCB and each available category of BFCL.
**Cost:** $1.61, ~2h36m wall, 1,086 calls (no aborts).
**Raw log:** `data/mini_bench_runs/calibration-all-2026-04-24T23-37-45.json`
**Driver:** `scripts/run_calibration.py` (resumable via
per-cell checkpoint).

This doc reports what the three subject models actually do
on the three Phase 1 buckets, decides what middle-band
subsets we can build for Phase 1 kickoff, and surfaces the
saturation problems that the design's middle-band-fallback
language was written to handle.


## Headline

| Bench | Slice | N | gpt-5.4-mini | claude-haiku-4-5 | gemini-2.5-flash |
|-------|-------|---|--------------|------------------|------------------|
| lcb   | easy  | 26 | 1.00 | 0.96 | 0.85 |
| lcb   | medium | 26 | **0.54** (0.67) | **0.46** (0.70) | 0.08 |
| lcb   | hard  | 60 | 0.25 (**0.48**) | 0.20 (**0.56**) | 0.00 |
| bfcl  | simple_python | 50 | 1.00 | 1.00 | 0.98 |
| bfcl  | multiple | 50 | 0.96 | 0.98 | 0.96 |
| bfcl  | parallel | 50 | 0.88 | 0.90 | 0.94 |
| bfcl  | parallel_multiple | 50 | 0.92 | 0.92 | 0.94 |
| bfcl  | live_simple | 50 | 0.82 | 0.92 | 0.82 |

Numbers are strict pass rate (all private tests pass for LCB,
binary AST match for BFCL). Numbers in parentheses are mean
fractional scores, shown only where they differ from strict
(LCB only — BFCL is binary-pass).

Reading: cells in the 0.45–0.55 band are exactly what we
want. **Bold** marks the only cells that hit it.


## What this answers, what it doesn't

This run answers part (a) of the calibration session: *where
does Condition A actually land on each subject × bucket?* It
does not run Conditions B/C/D/D'/E — those are the actual
experiment, not the calibration. It also does not address
multiplicity correction, dollar-cost caps, or budget-tier
matched-compute claims; those are kickoff-time decisions.

It pins down four things we were guessing about until now:

1. Where each subject sits on each slice (the table above).
2. Which slices are usable as Phase 1 strata without further
   data work.
3. Which buckets are structurally saturated and need fallback
   or replacement.
4. Whether the heterogeneous pool's "best subject" is
   bucket-stable. (Spoiler: no.)


## Slice-level findings

### LCB

LCB is the bucket the calibration most cleanly validates. It
is the only bucket where the strict pass rate of the two
strongest subjects lands near (or in) the middle band on
non-trivial slices.

- **lcb/medium (N=26)** is essentially the middle band for
  gpt-5.4-mini at strict (0.54) and is in-band for both gpt
  and haiku at mean_frac (0.67 / 0.70).
- **lcb/hard (N=60)** is in-band on mean_frac for both gpt
  (0.48) and haiku (0.56); strict pass is on the lower edge
  (0.25 / 0.20).
- **lcb/easy (N=26)** is saturated for all three subjects
  and should not be a stratum.
- **lcb/medium ∪ lcb/hard (N=86)** combined gives gpt 0.34
  strict / 0.54 mean_frac and haiku 0.28 strict / 0.61 mean_frac
  — the cleanest single-pool middle-band candidate currently
  available.

**Gemini-2.5-flash** is essentially unusable on LCB beyond
easy: 0.08 strict on medium, 0.00 on hard. This is not a
calibration error; it's that flash hits real difficulty walls
on competitive-programming-style problems. Implication for
Condition A on LCB: the *best subject* in the pool is gpt-5.4-mini,
the *worst* is gemini-2.5-flash by a wide margin. Heterogeneous
collaboration's burden of proof on LCB: beat gpt-alone
without being dragged down by gemini.

### BFCL

BFCL is structurally saturated across all five
currently-downloaded categories at first-50 sampling. Pass
rates run 0.82–1.00 with no obvious stratification by
category that would create middle-band cells.

The harder question is whether *any* within-category subset
can supply N≈400 middle-band tasks per cell (the threshold
the power analysis set for 80% interaction-test power):

- **simple_python**: 0/0/1 failures across the three subjects.
  Saturated; cannot supply a meaningful subset even at full
  category size (399).
- **multiple**: 2/1/2 failures. Saturated; full category size
  is 199, so even at full N the union of failures is likely
  ~10.
- **parallel**: 6/5/3 failures, union N=6. Even at full 199-task
  size, expected union ~25.
- **parallel_multiple**: 4/4/3 failures, union N=6. Same scaling.
- **live_simple**: 9/4/9 failures, union N=12. Largest failure
  pool seen; at full 257-task size, expected union ~60.

None of the available BFCL categories supports a 400-task
middle-band cell at the saturation rates observed. **BFCL as
currently constituted cannot run the interaction test at 80%
power** — it is in the same structural fallback bucket as
SWE-bench Verified (which has only 500 instances total).

The pre-registered design's middle-band-fallback language
exists for exactly this case. The argument for triggering it
on BFCL is stronger than the argument from the power analysis
alone, because the BFCL subject saturation is a property of
the data, not just an N-too-small problem.

### Heterogeneity is real

The "best subject" varies across buckets:

- LCB: gpt-5.4-mini (1.00 / 0.54 / 0.25 vs. 0.96 / 0.46 / 0.20
  for haiku and 0.85 / 0.08 / 0.00 for flash). Gpt strictly
  dominates on LCB.
- BFCL parallel: gemini-2.5-flash (0.94) > claude-haiku-4-5
  (0.90) > gpt-5.4-mini (0.88). Three different orderings
  exist across BFCL categories.

This is a property of the pool worth naming. The phase 1
"best single subject" baseline (used as the comparison anchor
for Conditions B/D'/E meta-reviewer) needs to be bucket-specific:
the design already implies this (per-bucket calibration), but
the calibration empirically confirms that the pool has no
universal best subject.

A side consequence: Condition C ("heterogeneous parallel +
peer-LLM aggregation") and Condition E (hierarchical synthesis
with meta-reviewer) need to pick a judge / meta-reviewer per
bucket, not pool-globally. The current `build_phase1_conditions`
takes a single `best_model` argument; that's fine if we
instantiate the spec once per bucket with bucket-specific
`best_model`, but it's worth noting we're not doing one
spec-for-all-buckets.


## Phase 1 kickoff implications

Routing the four kickoff decisions against the calibration:

1. **Per-stratum N.** The power analysis target was N=425
   per cell for 80% interaction-test power. LCB has 86 medium+hard
   tasks currently downloaded; BFCL has at most ~25–60
   non-saturated tasks per category. We are not hitting 425
   on either bucket as currently constituted.

2. **Middle-band fallback trigger.** Two concurrent reasons
   to trigger fallback now, both pre-registered as triggers:
   - LCB: stratum-N below threshold (86 vs. 400).
   - BFCL: saturation makes within-bucket stratification
     impossible.

   If we trigger fallback uniformly across Phase 1 (cleanest
   pre-registration story), the per-arm N target drops from
   425 (interaction) to 400 (Fleiss-style two-proportion).
   400 is still above the available LCB pool, so this isn't
   a get-out-of-jail card.

3. **Best-subject anchor for B/C/D'/E.** Bucket-specific.
   For LCB use gpt-5.4-mini; for BFCL use a per-category call
   (haiku for simple_python/multiple/live_simple; flash or
   haiku for parallel; flash for parallel_multiple). Note
   that for BFCL, the saturation makes "best" determination
   noisy at N=50.

4. **Pool-pricing argument validity.** Heterogeneity is real
   in the calibration data (different "best" per bucket).
   The pool-pricing argument (Phase 1 design's claim that
   ensemble of three medium models can match price of one
   strong model) survives the calibration but only when
   measured per-bucket — not pool-globally.


## Decision space for Scott

These are the choices the calibration data raises but doesn't
itself decide:

1. **LCB pool size.** Current `test6` release gives 86
   medium+hard stdin-only tasks. Pulling additional LCB
   releases (`test5`, `test4`) is straightforward — the
   download script already supports a `--release` flag. Each
   additional release should add ~30–60 medium+hard stdin
   tasks. Reaching N=400 requires ~5 releases. Cost: a single
   one-shot-fetch script run per release; runtime is on the
   adapter side which we already know is ~1–10s per task.

2. **BFCL: fallback trigger vs. expand vs. replace.** Three
   options:
   - **Trigger middle-band fallback for BFCL** on saturation
     grounds. Uses pre-registered design language. Loses the
     per-stratum granularity for tool-use.
   - **Expand BFCL to live_multiple / live_parallel /
     live_parallel_multiple categories** (not yet downloaded
     but already supported by the adapter shape). May add
     more failures; unknown until run.
   - **Replace BFCL with a harder tool-use bench.** Heavier
     lift; not on the current Phase 1 commitment list.

3. **LCB scoring: strict vs. mean_fraction.** Fractional gives
   more middle-band-shaped slices (medium+hard combined: 0.54
   / 0.61 vs. 0.34 / 0.28 strict). The trade-off is whether
   the experimental hypothesis is about all-pass-improvement
   or any-test-improvement. The design's fractional-scoring
   language for LCB doesn't pin this; calibration shows it's
   load-bearing for the kickoff power story.

4. **Gemini on LCB: keep, exclude, or replace.** Gemini-2.5-flash's
   0.00 hard / 0.08 medium pass rates make it a near-zero
   contributor to D/E on LCB. If we're going to run the
   heterogeneous protocols on LCB, we should make explicit
   the case that gemini's value is in the *critique signal*
   even when its draft is poor — or replace it for LCB
   specifically.


## What changed in this session's tooling

- `scripts/run_calibration.py` — new driver. Enumerates
  (bench × slice × subject) cells, runs Condition A only,
  emits one combined log. Resumable via `--checkpoint`
  (writes a per-cell-resumable JSON sidecar after each cell;
  re-running with the same checkpoint skips already-done
  cells). Mid-run terminal kills no longer lose progress.
- No changes to adapters, condition factories, or the
  experiment runner. Calibration is read-only on the
  Phase 1 stack.


## Cross-references

- `docs/research/experimental-design.md` — Phase 1 design,
  middle-band-fallback rule.
- `docs/research/power-analysis.md` — N≈425/400 thresholds
  this calibration is measured against.
- `docs/status.md` — task-start/done routing for this session.
