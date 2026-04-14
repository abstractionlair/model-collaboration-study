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
  `experimental-design_draft.md` as a meaningful extra axis but
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
