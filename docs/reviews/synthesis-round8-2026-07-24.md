# Round-8 Review Synthesis — conclusions given the data (2026-07-24)

Four independent reviews of `docs/research/pilot-findings.md`
(rev. 1) against the raw pilot data. All four reviewers ran
their own Python analyses on the log — the brief explicitly
invited it, following the round-7 lesson.

**Verdicts:** Grok 4.5 *Publish with edits*; Claude Fable 5
(fresh) *Publish with edits*; Kimi K3 *Publish with edits*;
GPT-5.6 Sol *Revise and re-review*. The edit lists converge
almost completely; rev. 2 of the findings doc incorporates the
union. **Every table entry and CI in rev. 1 reproduced exactly
for all four reviewers.** The casualties were interpretive
sentences.

## Findings that changed the document (verified by the coordinator)

1. **D's "parity" is cap-borne** (Fable, Sol, Kimi — three
   independent decompositions, consistent): D−gemini = +0.228
   on gemini's 26 cap-strained tasks, −0.072 on the other 60;
   excluding gemini's 11 truncated-to-zero rows flips the
   aggregate to −0.060; cap counterfactual ≈ −0.090. Rev. 2
   reframes D as "ensemble rescue of the bounded member,"
   unresolved (not parity) against an unbounded best model.
2. **True complementarity ≈ zero** (Sol, Kimi): oracle-minus-
   best headroom is +0.186 on cap-strained tasks and +0.0004
   on the clean 60. The pool's apparent complementarity was
   manufactured by the output cap.
3. **C's judge ≤ random** (Kimi; verified at the 27th
   percentile of a 10k random-pick null). The most actionable
   new fact of the pilot: task-visible selection failed to
   match a coin. Elevated to a headline conclusion.
4. **"Only CI-excluding-zero gain" was false** (Fable):
   D−D′ and D−haiku also exclude zero. **B fails multiplicity**
   on the primary metric (Holm p≈.08, Bonferroni p≈.14; Fable,
   Sol, Kimi concur) but survives on strict and by sign test.
   Rev. 2 downgrades B to "nominal, replication-worthy."
5. **"Zero tie events" was false** (Sol): 24 weighted-vote
   ties (20 in D′ = 23% of its tasks, 4 in D), a real
   single-seed sensitivity for D′.
6. **"Matched compute" wording** (all four): nothing in the
   run compute-matches collaboration against the best single
   model; D lacks its Best-of-N comparator. Rev. 2: "no
   *demonstrated* win; D unresolved; C/E conclusively negative
   at 1.2–2.2× the single model's cost."
7. **Robustness-direction sentence deleted** (Kimi's
   empirical refutation: D−gemini = −0.119 on D's own
   truncation-bearing tasks vs +0.055 clean — the cap binds
   both sides). C/E negatives and B's direction remain robust;
   D is unresolved in both directions.
8. **Strata language corrected** (Sol, Kimi): 0.797 is above
   the pre-registered easy band — outside the declared strata;
   consistency is weak and overdetermined by the ceiling.
9. **B beats A(gemini) on $/solved** ($0.091 vs $0.110; Fable,
   Kimi) — a Pareto point rev. 1 missed; now in the table.
10. **Best-subject-flip attribution softened** (Fable, Sol):
    the flip conflates the truncation fix with the 2.5→3
    model swap; post-fix 2.5-flash measurement (already
    queued) isolates it.

## Reviewer-error ledger (verification matters in both directions)

- Kimi's claim that the router figure 0.832@49% "failed to
  reproduce / is arithmetically incompatible" is **wrong** —
  it reproduces exactly under the doc's stated rule (cheapest
  model ≥ gemini's per-task fraction; Sol reproduced it too).
  Kimi computed a different, also-valid rule (cheapest among
  per-task argmax: 0.854@50%). Rev. 2 states both rules
  explicitly.
- No other reviewer claim failed verification this round.

## Performance notes (for the reviewer-roster record)

All four materially improved the artifact. Fable-r8
(reproduced everything, found the cap-rescue decomposition and
the false "only significant" sentence) and Kimi-r8 (random-pick
null, truncation-subset refutation, difficulty breakdowns) were
the standouts; Sol was the most statistically complete
(contest-cluster bootstrap, TOST/equivalence framing, tie
telemetry, metric definitions) and supplied directly adoptable
replacement sentences; Grok was fastest with the correct
top-line reframes. The "run your own analyses" instruction —
added after round 7 — is what produced findings 1–3 and 7.
