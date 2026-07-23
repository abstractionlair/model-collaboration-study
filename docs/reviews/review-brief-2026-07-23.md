# Review Brief — Round 7 (new model generation), 2026-07-23

You are one of four independent reviewers of this research
project. The previous review rounds (2026-04) were conducted by
Codex (GPT-5.4), Gemini 3.1 Pro, and Claude Opus 4.7. None of
the current reviewer generation has seen this project before.
Reviewers this round: Claude Fable 5 (fresh context — a
different Claude instance implemented recent changes), GPT-5.6
Sol, Grok 4.5, and Kimi K3. The latter two are reviewing for
the first time from any lineage position.

## Ground rules

- **Read-only.** Do not modify any file, and do not run
  scripts that make API calls (`scripts/run_*.py`,
  `scripts/smoke_test.py`). A long experiment run is in
  progress on this machine; `data/pilot_checkpoint.json` is
  live and changing. Running `pytest tests/` offline is
  permitted but optional.
- **Honest assessment** (house norm, verbatim): "Your honest
  assessment is valued, including criticism. There is no
  penalty for pointing out problems. You also don't need to
  invent faults. Overlooking a real problem is as unhelpful as
  inventing a false one."
- Output your complete review as markdown to stdout (do not
  attempt to write files). Use the template at the bottom.

## What this project is

Read in this order:

1. `CLAUDE.md` — project brief, research question, file map.
2. `docs/research/experimental-design.md` — the locked Phase 1
   design (promoted 2026-04-14 after four review rounds).
3. `docs/decisions.md` — decision log, especially the
   2026-07-04 kickoff decisions.
4. `docs/status.md` — current state, including today's
   session findings (see "Currently routed to").
5. Code: `src/ir/`, `src/executor/`, `src/experiment/`,
   `src/protocols/`, `scripts/run_pilot.py`.
6. `docs/research/calibration-findings.md` and
   `docs/research/power-analysis.md` for the empirical
   grounding of the current plan.

## What to review

**(a) The experimental design, seen fresh.** Criteria from
`WORKFLOW.md`: do the baselines actually test the claims
(especially the compute-matched single-model baseline)? Are
the IVs cleanly isolated? Metrics appropriate? Uncontrolled
confounds? Calibration approach sound? You are a new model
generation — prior reviewers may have shared blind spots.

**(b) The implementation.** Does the code faithfully express
the design? Look for measurement-integrity bugs (silent
fallbacks, budget accounting, selector-as-oracle leaks,
prompt-context discipline), not style nits.

**(c) Today's findings and their design implications.** On
2026-07-23 a harness bug was found and fixed: Gemini responses
were silently truncated (thinking tokens count against
`max_output_tokens`; the visible answer was cut mid-fence and
thinking tokens were not billed). Post-fix,
gemini-3-flash-preview scores ~0.90 mean_frac on the LCB
medium+hard pool that was calibrated (pre-fix) so the best
subject sits near 0.50. A pilot of the full condition matrix
(N=86) is running now. Specific questions where reviewer input
is wanted:

1. The middle-band calibration is now invalid for the actual
   best subject. Options include: re-run harder-subset
   selection against the fixed harness; expand the pool and
   re-stratify; re-anchor `best_model` to Gemini and accept a
   pool where the other two subjects sit mid-band. What would
   you do, and what does each option do to the pre-registered
   middle-band fallback test?
2. Condition B's sample count is dollar-matched. D's realized
   cost is now dominated by one vendor's thinking-token spend
   (~6x the homogeneous control D'). The running pilot matches
   B to D' rather than D. Is that sound? More generally: is
   vendor thinking spend "compute" that matching must respect,
   or a vendor behavior to report alongside results?
3. The harness now allows Gemini 8x the output budget
   (32768 tokens including thinking) vs 4096 visible-token
   caps for OpenAI/Anthropic subjects (which empirically use
   under ~2200). Confound requiring equalization, or
   acceptable measured asymmetry?
4. The pilot is descriptive (N=86, far below the ~400/arm the
   power analysis requires). What claims would be overclaims
   in a public write-up of it?

## Output template

```markdown
# Review: Model-collaboration study — plan and code (round 7)

**Reviewer:** [model name and version]
**Date:** 2026-07-23
**Artifacts reviewed:** [list]

## Summary assessment
[1-2 sentences: overall quality and most important issue]

## Specific findings
[Numbered list. For each: what, where (file:line where
applicable), why it matters, suggested direction.]

## Answers to the four posed questions
[Numbered 1-4.]

## Recommendation
[Proceed / Revise and re-review / Rethink approach]
```
