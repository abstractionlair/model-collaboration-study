# Review Brief — Round 8: conclusions given the data (2026-07-24)

You are one of four independent reviewers. The artifact under
review this round is **an interpretation, not a system**:
`docs/research/pilot-findings.md` — the conclusions drawn from
the just-completed Phase 1 pilot. Your job is to audit whether
those conclusions actually follow from the data, and what the
write-up gets wrong, overclaims, underclaims, or misses.

The author of the findings doc is the coordinating (in-context)
Claude session; you are its independent check. Round-7 context:
four reviewers (you or your counterparts) audited the plan and
code on 2026-07-23 (`docs/reviews/synthesis-round7-2026-07-23.md`);
several of the caveats in the findings doc exist because of
that round.

## Ground rules

- **Do not modify any repository file. Do not call any model
  API.** You MAY (and are encouraged to) run Python locally to
  analyze the data files — read-only analysis with in-memory
  computation. The round-7 review's most decision-relevant
  finding came from a reviewer who interrogated the data
  directly rather than trusting the prose; that move is
  explicitly invited for everyone this round.
- **Honest assessment** (house norm): criticism carries no
  penalty; inventing faults is as unhelpful as overlooking
  real ones.
- Output the complete review as markdown to stdout, using the
  template at the bottom.

## Data and context

Primary data (all JSON, self-describing):

- `data/mini_bench_runs/pilot-lcb-2026-07-24T20-46-16.json` —
  the complete pilot: 688 (condition × task) rows with
  per-task fraction, strict pass, dollars, tokens, truncation
  counts, abort labels.
- `data/mini_bench_runs/calibration-all-2026-04-24T23-37-45.json`
  — April calibration (pre-truncation-fix; per-task rows under
  `rows[].tasks`).
- `data/mini_bench_runs/pilot-lcb-smoke-*.json` — smoke runs.

Context documents, in reading order: `docs/status.md`
("Currently routed to" carries the full two-day history),
`docs/research/pilot-findings.md` (the artifact under review),
`docs/research/experimental-design.md` (what the design permits
claiming), `docs/reviews/synthesis-round7-2026-07-23.md`,
`docs/research/power-analysis.md`.

## What to audit

**(a) Each claim in the findings doc, against the data.** The
headline conclusions to check individually:

1. "No collaboration condition beats the best single model at
   matched compute" — including whether "matched compute" is
   used honestly given that tier caps were unenforced and B was
   realized-cost-matched to D′ only.
2. "D achieves statistical parity with A(gemini) at 3.9× cost"
   — is parity the right reading of +0.019 [−0.068, +0.109]?
3. "B's +0.094 over its own base model is the pilot's only
   significant positive" — check the statistics and whether
   the five reported CIs needed multiplicity handling.
4. "D vs D′ (+0.228) is dominated by pool composition, not
   structure."
5. The ceiling analysis (+0.056 selection headroom; C realized
   none of it) and its scope limits.
6. "Consistent with (not confirmation of) the strata
   hypothesis."
7. The robustness-direction argument: "all open instrument
   issues bias against the best single model or toward fake
   collaboration wins, so the negative headline is robust in
   direction."
8. The routing corollary (oracle router: 0.832 at 49% of
   all-gemini cost).

**(b) Statistical methodology.** Paired bootstrap on per-task
fraction differences (10k resamples): appropriate for this
data? What about: non-independence across the five comparisons;
task-level pairing vs test-case-level clustering; strict-vs-
fractional discrepancies (D beats gemini on mean_frac but not
strict — does the doc handle that honestly?); single seed /
single provider replicate.

**(c) Missing analyses.** What cheap, decision-relevant
computation on this data did the write-up not run? (Run it
yourself if you can.)

**(d) Publishability.** The findings feed a public blog post.
Which sentences, if quoted verbatim, would you object to?

## Output template

```markdown
# Review: Pilot conclusions given the data (round 8)

**Reviewer:** [model name and version]
**Date:** 2026-07-24
**Artifacts reviewed / analyses run:** [list, incl. any
computations you performed on the raw data]

## Summary assessment
[1-2 sentences]

## Claim-by-claim verdicts
[Numbered 1-8 per the brief: SUPPORTED / OVERCLAIMED /
UNDERCLAIMED / UNSUPPORTED, each with 1-4 sentences of
evidence.]

## Statistical methodology findings
[Numbered list.]

## Missing analyses (with results if you ran them)
[Numbered list.]

## Publishability
[Specific objectionable sentences, if any, with fixes.]

## Recommendation
[Publish as-is / Publish with edits / Revise and re-review]
```
