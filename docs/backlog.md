# Backlog

Durable ideas, open threads, and future directions that don't belong
in `status.md` (which is only about the immediate horizon). No
particular priority order within each section.

Update when: an idea is worth not losing but isn't being worked on
right now. When an item becomes "the next thing," move it into
`status.md`'s *Next up*. When it's acted on and completed, move the
outcome into `docs/decisions.md` (if it's a decision) or into the
appropriate artifact (if it's work).


## Project directions not yet scheduled

- **Autoresearch / structural search over protocol shapes.** Beyond
  parameter tuning. The typed AST was designed with this in mind;
  the mutation engine should operate on type-preserving subtree
  replacements, not just field tweaks. See
  `docs/design/system-architecture.md` § "Looking ahead" for the
  foundation work already done (runtime type reification).

- **Recursion prediction.** Applying collaborative protocols to
  their own sub-tasks probably doesn't help at Phase 1 difficulty
  but may at higher complexity. Worth a dedicated test once the
  basic matrix is run.

- **Blackboard, dynamic topology, and agentic-trajectory protocols.**
  The protocol inventory has these but the IR can't express them
  cleanly yet. Don't force them in; add nodes when a concrete use
  case demands.

- **Adversarial debate condition.** Flagged in
  `experimental-design.md` as a meaningful extra axis but
  deferred from the Phase 1 matrix on compute-cost grounds. Revisit
  after Phase 1 results.

- **Session-continuation (`ContextMode.ACCUMULATED`) semantics for
  real clients.** The executor passes ContextMode through but the
  real-client design question — how ACCUMULATED maps onto
  Anthropic/OpenAI session models — is unresolved.


## Replication ladder (near-term work driver)

The progression the project is following:

1. CCR (done in IR)
2. PoLL / judge panel
3. ReConcile (done in IR)
4. RouteLLM / FrugalGPT (routing/cascade family)
5. Debate or Vote
6. ColMAD (collaborative vs adversarial framing)

CCR and ReConcile already exist in `src/protocols/`. The gap before
any of these can run is the experiment-spec layer plus a real
`ModelClient`.


## Process / infrastructure ideas

- **Post-compaction re-read norm and a hook to enforce it.** The
  repo has a `pre-compact-continuity.sh` hook; worth extending so
  the post-compaction agent is reminded to re-read `status.md`.

- **Run manifest schema.** Codex and Gemini both flagged this in the
  April managerial review. Needed before the first real client run:
  run ID, timestamp, git commit, fully-resolved IR AST, model
  versions, prompt versions, total tokens, dollar cost, condition
  matrix slice, anomalies. See `docs/reviews/` once that review
  lands.

- **Resolution section on the review template.** Gemini's
  suggestion: review files become closeout records, not just inbox
  items. Primary driver appends a Resolution section with actions
  taken or explicit rejection rationale.

- **Context and Consequences fields in the decision log template.**
  Both Codex and Gemini flagged these independently. Small template
  change; worth backfilling recent entries when done.

- **Risk / assumptions log.** Codex's proposal — a separate artifact
  for load-bearing project assumptions (judges behave as expected,
  API pricing holds, task calibration lands, etc.). Not a decision
  log (no path chosen) and not an open question (more durable).


## Model coordination

- **Codex and Gemini MCP sessions** are live (`mcs-coord`,
  `mcs-coord-gemini`). Use for substantive design questions and
  commitment-artifact reviews, not routine work. Evaluate their
  contributions critically per the `codex_critical_eval` memory;
  same principle applies to Gemini.

- **Review index / matrix.** Currently no central view of
  "which artifacts have been reviewed by whom, and what the
  disposition was." Codex flagged this; worth building when the
  first formal reviews land on the rewritten experimental-design
  draft.


## Follow-on experiments and retrospective improvements (2026-07-24)

Captured from the round-7 review period and the question-level
design discussion with Scott. These are "ways the experiment
could have been done better" that are now follow-on work rather
than retrofits; several are pre-conditions for the confirmatory
phase (marked ⚑), the rest are candidate arms or analyses.

### Rival-baseline arms the matrix lacks

- **A⁺: native inference-scaling of the best single model —
  as an allocation sweep, not a single point.** The fair "best
  single model at $2X/$4X" includes the vendor's own compute
  dial (thinking budget / reasoning effort), not just B's
  repeat-and-select. Design as a grid over budget divisions at
  matched dollars — e.g. at 4× budget: 1 call × 4× thinking,
  2 × 2×, 4 × 1× + pick — per difficulty stratum. Literature
  (Snell et al. 2024 compute-optimal test-time scaling; Brown
  et al. 2024 repeated-sampling coverage) says neither pure
  strategy dominates: sequential thinking tends to win on tasks
  a single attempt can't finish, parallel sampling wins where
  attempts fail decorrelated and selection is possible, and the
  optimal mix shifts with difficulty. "Think N× longer beats
  repeat N times" is NOT a known truth — the allocation curve
  is the real object of study, and it doubles as the strongest
  honest baseline for any collaboration claim.
- **Pre-hoc router baseline.** A cheap dispatcher that picks
  *which single model* answers each task, at ~1× cost. If a
  router captures most of the oracle-ensemble gap, the
  collaboration category loses to dispatch. C is post-hoc
  routing at N× cost; the matrix has no pre-hoc arm.
- **Frontier-judge-at-true-cost arm.** Scott's original
  2026-04-08 scheme, dollar-honest: small pool + frontier
  aggregator, judge's real price counted, vs. single model at
  the same total dollars. Doubles as the first oversight-framing
  test. See the 2026-07-24 annotation on the 2026-04-08
  decision entry.

### Measurement upgrades

- ⚑ **Complementarity-ceiling gate on pool selection.** The
  oracle-minus-best gap (per-task max across subjects vs. best
  subject mean) must be ≥ the assumed effect size for
  selection-shaped conditions, recomputed at every
  recalibration. Five lines of analysis; its absence let a pool
  with +0.056 selection headroom carry a +10pp pre-registered
  effect. Caveat learned 2026-07-24: the ceiling binds
  one-draw-per-member selection (C) only — it scales with the
  affordable draft set and never bound D/E; use it as a
  decomposition baseline (selection component vs. generation
  component of any protocol gain).
- ⚑ **Retain and offline-score unchosen candidate drafts.**
  Costs nothing but local execution; makes the
  selection-vs-generation decomposition measurable (realized
  recovery rate vs. ceiling; whether D/E wins come from picking
  or from improving). Fold into the run-manifest schema.
- **Score-all-drafts diagnostics for B.** B's ceiling is
  E[max over its n same-model draws] — currently unmeasurable
  because losing drafts are discarded. Same retention fix.

### Process rules (cheap, learned the hard way)

- ⚑ **Recalibration protocol.** Re-run Condition-A columns on
  the current harness immediately before any confirmatory run;
  if the best subject changed, re-anchor and re-stratify from
  A-column data only; disclose task overlap with any
  already-observed condition-level results.
- ⚑ **Anchor recomputation on metric change.** Any change to
  the scoring rule (e.g. strict → mean_fraction, 2026-07-04)
  invalidates "best subject" determinations made under the old
  rule; recompute at decision time (April's best subject under
  mean_fraction was haiku, not gpt — discovered 2026-07-24).
- **Contamination-window check.** Record each subject's
  training cutoff against the benchmark release window at
  calibration time (Kimi K3, round 7).

- **Repeat-variance diagnostic (Scott, 2026-07-24).** k≈5
  repeats × 20–30 middle-band tasks × 3 subjects (~$12–15):
  per-task outcome distributions (prices the sampling lever —
  expected-max-of-n curves per task), and failure-pattern
  overlap across repeats (same tests failing = correlated =
  depth wall → thinking; different tests = decorrelated →
  sampling). Pair with a 2–3-level thinking sweep to price the
  sequential axis, which repeat statistics cannot predict.
  Together these let the A⁺ allocation curve be predicted, not
  just measured. Doubles as the design's "variance across
  seeds" metric (vendor stochasticity is the actual variance
  source; harness seeds don't reach generation). Requires
  retaining per-test pass vectors in ScoreResult (currently
  discarded; one-line adapter change).

- **Cost-side objective flip (Scott + Mijan conversation,
  2026-07-24).** Re-pose the experiment as "equivalent results
  for fewer dollars" instead of "better results for the same
  dollars": fix the quality bar at the best single model's
  level, minimize spend. Empirical hook from the pilot
  A-columns: an oracle per-task router achieves gemini-level
  quality (0.832 vs 0.797 mean_frac) at **49% of all-gemini
  cost**, routing 48/86 tasks to 10–20x cheaper models — on
  the same pool where the capability objective returned
  "nothing to gain." Capability gaps are routing opportunities
  inverted; the imbalanced pool that broke the capability
  instrument is this experiment's ideal input. Conditions:
  cascades (cheap-first + escalate) and learned routers
  (FrugalGPT / RouteLLM lineage), evaluated with the same
  honesty machinery (oracle bounds, realized recovery rates,
  matched-quality discipline). Note the durability asymmetry:
  capability scaffolds compete with frontier quality (moving
  target); cost scaffolds only need price dispersion (stable
  market property) — plausibly the longer-lived research
  direction under continued scaling.

- **Capability-leveled pools via composite members (Scott,
  2026-07-25).** Replace weak pool members with macro-model
  subgraphs of themselves (e.g. best-of-n) sized at calibration
  time to match the strongest member — manufacturing the
  near-peer pool the market doesn't offer, and isolating
  diversity from capability gap by construction. Recursive
  application of the project's own macro-model framing.
  Feasibility check first: the repeat-variance diagnostic
  predicts each member's sampling-saturation ceiling (if below
  the target level, boost via the A⁺ compute-optimal allocation
  instead of samples alone). Open empirical questions: does
  leveling preserve the decorrelated-error diversity
  heterogeneity feeds on (best-of-n narrows the output
  distribution), and does the member-internal judge hold up
  (pilot: same-model judge worked (+0.09), cross-model judge
  ≤ chance)? Cost note: B(gpt,8) ≈ $0.036/draft vs gemini's
  ≈ $0.07 — leveling capability roughly levels per-draft cost
  on the pilot pool. Implementation: condition factories take
  model names for pool slots; needs IR extension to accept
  sub-expressions as members + semantics for composite-member
  revise/critique. Complementarity-ceiling gate applies to
  boosted A-columns unchanged.
