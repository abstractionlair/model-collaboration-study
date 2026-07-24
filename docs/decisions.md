# Decision Log

Significant choices and their rationale. See WORKFLOW.md for format guidance.

---

## 2026-04-08 Use API models for the study, not self-hosted

**Decision:** Run all experiments via commercial APIs (frontier lab small
models as subjects, frontier large models as judges) rather than
self-hosting open-weight models.

**Alternatives considered:** Self-hosting open models on rented GPUs
(explored in detail in the initial GPT conversation).

**Rationale:** The research question is about multi-model protocol design,
not about specific models. APIs remove confounds from quantization,
serving configuration, and deployment instability. They also give genuine
training-lineage diversity (Claude, GPT, Gemini) that open models often
lack. Self-hosted open models are a valid follow-up to test whether
results transfer.

**Status:** Active

---

## 2026-04-14 Formal research question (capability-first, compute-matched)

**Decision:** The formal research question is: "At matched compute
budget, when does a heterogeneous multi-model collaboration protocol
outperform the best single model in the pool, and which structural
properties (heterogeneity, topology, critique format, round count)
drive the difference?"

**Alternatives considered:**
- "Under what structural conditions does a multi-model protocol
  produce outputs of higher capability than its strongest constituent,
  at matched compute?" (broader)
- "Which structural properties determine whether the protocol's
  output capability exceeds, matches, or underperforms its strongest
  constituent?" (closest to the old "oversight quality" wording but
  capability-first)
- The original motivating question ("Can we systematically and
  reliably enable more capabilities…"). Rejected as the formal
  question because it is too broad to drive an experimental design.

**Rationale:** The compute-matched constraint is load-bearing — any
multi-model result that fails to beat a compute-matched single-model
baseline is not a real win, only a more expensive way of spending
inference. Naming four starting structural axes (heterogeneity,
topology, critique format, round count) commits the design to
investigating these without precluding later additions from the
protocol inventory. The capability-first framing replaces the
earlier "oversight quality" wording, matching the motivation pivot
already reflected in `docs/research/inspiration.md`.

**Status:** Active. Gates the rewrite of
`docs/research/experimental-design.md`.

---

## 2026-04-14 Three-layer architecture: prose inventory, typed IR, experiment spec

**Decision:** Organize the system into three layers with distinct
responsibilities: (1) the prose protocol inventory as the
human-readable design space, (2) a typed Python IR as the
executable abstract structure of a protocol, (3) a separate
experiment-spec layer (not yet built) for prompts, model
assignments, task slices, judges, and budgets.

**Alternatives considered:** Folding everything into one layer
(YAML-only, or a single annotated Python module). Two layers (IR +
experiment spec, no prose inventory).

**Rationale:** The IR is about the *abstract structure* of a
protocol — who reviews what, with what visibility, in how many
rounds. Things that vary per experiment (which concrete models,
which prompts, which task slice) belong elsewhere. The split lets
a single IR definition of (say) ReConcile be instantiated against
many model assignments and task sets without duplicating the
protocol logic. Codex pushed for this split early; we accepted it
after recognizing it's slightly more than "spec vs implementation"
— it's "abstract protocol vs concrete instantiation."

**Status:** Active. See `docs/design/system-architecture.md` for
the full layered design.

---

## 2026-04-14 Python typed AST with surface authoring layer (not Haskell)

**Decision:** Implement the typed protocol IR in Python (with a
lowercase surface authoring layer), not in Haskell. The Haskell
file at `src/ir_haskell/ProtocolIR.hs` stays as documentation of
the target aesthetic, not as a source language.

**Alternatives considered:** Haskell as the primary language
(rejected), a hybrid where Haskell generates Python (rejected),
plain Python without a surface layer (close call).

**Rationale:** Haskell has nicer authoring syntax for typed ASTs
but loses at the HOAS-serialization boundary, and the mutation
engine is Python-native by necessity (interleaved with execution
and API calls). Decision was made after writing both versions
side-by-side and consulting Codex and Gemini. The surface authoring
layer (`src/ir/surface.py`) brings Python ergonomics close enough
to the Haskell aesthetic that the loss is acceptable.

**Status:** Active.

---

## 2026-04-14 Identity-memoized tree-walking executor

**Decision:** The executor caches sub-expression evaluation by
`id(expr)`. A subtree referenced multiple times in the AST means
*the same runtime value*, not two independent re-evaluations.

**Alternatives considered:** Re-evaluating each reference (rejected
— breaks CCR's intent that the reviewer and reviser see the *same*
draft). Forcing all sharing to go through explicit `bind()`
(rejected — boilerplate, surprising to authors who write
`d = gen(...)` and reuse `d`).

**Rationale:** In CCR, the canonical authoring pattern is
`d = gen(model, q); finalize(revise(model, d, review(model, d, ...)))`.
The intended semantics is one draft, reviewed and then revised. The
IR is immutable, so identity-keyed caching is safe. Without
memoization the executor issues four model calls instead of three
on CCR.

**Status:** Active. See `src/executor/interpreter.py`.

---

## 2026-04-14 Experimental design promoted — macro-model framing, executable-only Phase 1

**Decision:** Promote `docs/research/experimental-design.md` out
of draft after four rounds of independent review by Codex and
Gemini. Both reviewers signed off on the structure and the
macro-model framing in the fourth round. The load-bearing
commitments this promotion locks in:

- **Macro-model framing.** A collaborative pipeline *is* a
  model — a function from context to response built from
  smaller input models. The experimental question becomes
  whether macro-models can be more capable than any of their
  input models at matched dollar cost. The unit of experimental
  comparison is a fully-specified macro-model; the typed IR
  building blocks in `src/ir/` are the shared substrate.
- **Phase 1 scope: executable scoring only.** No LLM-as-judge
  apparatus in Phase 1. Walk-before-run. Makes the measurement
  unarguable and decouples the protocol question from the
  judge-reliability question. Open-ended tasks and the LLM-judge
  apparatus return in Phase 2, calibrated against Phase 1
  results.
- **Compute unit: US dollars, as caps.** Dollar-denominated
  budget tiers ($X, $2X, $4X) with $X anchored to the single-
  model one-pass cost. Tiers are caps, not exact-spend targets
  — macro-models that spend less than the cap are rewarded in
  the dollars-per-solved-task metric.
- **Condition matrix: A / B / C / D / D' / E.** Each pinned to
  one concrete macro-model specification composed of typed IR
  building blocks, with no `or` branches. D' is a homogeneous
  counterpart to D added for the cleanest heterogeneity
  comparison the matrix can support.
- **Statistical primary test: Protocol × Stratum interaction,
  pre-registered.** Three difficulty strata (30–40%, 45–55%,
  60–70% one-shot success for the best subject model). Fallback
  to the middle band alone is pre-declared and triggers
  automatically if a pre-kickoff power analysis against an
  assumed utility curve yields below 80% power.
- **Variable K (identity blinding) locked** as a fixed default
  across all conditions in Phase 1.
- **Infrastructure failures separated from capability failures.**
  Infra failures (Docker, network, rate limits) are retried and
  do not count against the dollar budget. Capability failures
  are scored normally.

**Alternatives considered:**

- Running Phase 1 with LLM judges on open-ended tasks. Rejected
  in favor of walk-before-run: fewer load-bearing assumptions
  at once, unarguable measurement, Phase 2 calibrated against
  Phase 1 results.
- Token-based compute matching. Rejected in favor of dollars
  because tokens don't compose across tokenizers and dollars
  are the real-world binding constraint.
- Pooling strata for the primary statistical test. Rejected
  because the strata hypothesis predicts opposing effects
  across strata that would average to approximately zero.
- "Selector discipline" as a cross-cutting rule imposed from
  outside each protocol. Rejected in favor of treating
  aggregation as a typed IR building block that some
  macro-models contain and others do not — the non-oracle
  property falls out of the type system rather than needing
  its own enforcement machinery.

**Rationale:** The four review rounds converged rather than
diverging — round one found structural issues, round two found
substantive flaws (the selector-as-oracle trap and the pooled-
primary-test trap), round three addressed those with both
reviewers nearly approving, and round four adopted the
macro-model framing that turned several round-three fixes from
procedural discipline into structural properties. Both reviewers
ended round four recommending promotion with no substantive
reservations.

**Status:** Active. Gates the experiment-spec layer and the
real `ModelClient` work. The pre-kickoff power analysis is an
operational gate, not a design gate.

---

## 2026-04-16 Fuse node and the "many → one" naming family

**Decision:** Name the node for "model reads multiple drafts and
writes a fresh response" as `Fuse`. Reserve `ReviseFromMany` for
the future "one draft + multiple critiques → fresh draft" variant,
and leave the pre-draft advisory synthesis unnamed until the type
for advisory inputs is designed.

**Alternatives considered:** `Synthesize` (rejected — too broad,
would foreclose namespace for the siblings). `DraftFromDrafts`
(rejected — ugly). `Resynthesize` (considered acceptable but less
clean than `Fuse`).

**Rationale:** Three patterns share the shape "model reads multiple
artifacts and writes fresh" but differ in what flows in:
(A) multiple drafts → fresh draft, (B) one draft + multiple
critiques → fresh draft, (C) query + advisory inputs → fresh draft.
The type differences are load-bearing for the mutation engine.
Naming each specifically avoids the trap of a single overloaded
node with optional fields that the mutation engine can't reason
about.

**Status:** Active. `Fuse` is implemented. `ReviseFromMany` and
the advisory-synthesis node are named but not implemented — add
them when a concrete protocol requires them.

---

## 2026-04-16 Rename ReviseRound/Rounds to SelfReviseRound/SelfRounds; add peer-review siblings later

**Decision:** Rename the existing `ReviseRound` and `Rounds` IR
nodes to `SelfReviseRound` and `SelfRounds` to make their
self-review-with-peer-context semantics explicit, and commit to
adding `PeerReviseRound` / `PeerRounds` as sibling nodes for the
peer-review macro-model that the experimental design's D-family
specifies. Both flavors are intended to coexist as typed
building blocks. Conditions D, D', and E continue to use the
self-review nodes for now and will migrate to the peer-review
siblings as those land.

**Alternatives considered:**

- **Mutate the existing nodes' semantics in place** (change
  `ReviseRound` from self-review to peer-review under the same
  name). Rejected: loses the self-review macro-model as an
  available building block. Several protocols in
  `docs/research/protocol-inventory.md` use self-review-with-
  peer-context as their core (consensus-via-self-reflection,
  single-pass-then-self-critique). The IR is supposed to be the
  substrate for the broader inventory, not just for whichever
  conditions Phase 1 tests.
- **Generalize `ReviseRound(reviewer_role: Self | Peer)`** as a
  parametric node. Rejected: adds authoring-time complexity for
  no Phase 1 payoff. Two distinct node names compose more
  cleanly with mutation (a structural mutation that swaps Self
  for Peer is just a node-class swap; no field-validity rules to
  reason about).
- **Generalize `Rounds(n, single_round_expr)`** so the round
  count is orthogonal to the round kind. Rejected for now (same
  reason — adds authoring complexity for no Phase 1 payoff). May
  revisit if more round kinds appear.
- **Update the experimental design to adopt self-review.**
  Rejected: would defeat the heterogeneity comparison D/D' is
  built around. All three independent reviewers (Opus 4.7,
  Codex, Gemini) flagged self-review as destroying the
  cross-lineage critique signal that makes the D-family
  meaningful.

**Rationale:** The faithfulness gap was identified in three
independent reviews (`docs/reviews/system-review-*-2026-04-16.md`).
The pattern of choice — keep the existing component as a renamed
typed building block, then add the design-faithful sibling — was
adopted as the project-wide pattern for resolving this round's
faithfulness gaps (see also `decisions.md` entries to come for
B/C aggregation and E composition). The principle is that the IR
is a substrate for the protocol-inventory space, not a minimum
expression of just the locked Phase 1 conditions; pluggable
typed components are higher-leverage than tightly-fit ones.

**Status:** Active. SelfReviseRound and SelfRounds implemented
in commit `82627d3` (2026-04-16). PeerReviseRound and PeerRounds
implemented and D/D'/E migrated in the follow-up commit on the
same day; cyclic 1-peer-per-draft assignment (lower bound of
the design's "1–2 peers"); requires N >= 2. Other peer-
assignment rules (2-peer cyclic, all-N-1) deferred — see
`docs/design/system-architecture.md` "Peer-assignment rules."

---

## 2026-04-16 Add PickOne for comparative selection; B/C migrate

**Decision:** Add `PickOne(judge, drafts) -> Answer[Draft]` as
a new IR node for comparative selection — a single judge sees
all candidates side-by-side and picks one. Migrate Conditions
B and C from `ParScore + WeightedVote` (independent pointwise
scoring + argmax) to `PickOne`. Keep `ParScore + WeightedVote`
unchanged as the per-draft confidence-aggregation building
block; D and D' continue using it for ReConcile-native
confidence-weighted aggregation.

**Alternatives considered:**

- **Reinterpret `ParScore + WeightedVote` to be the design's
  "chooses among the N candidates" mechanism.** Rejected:
  pointwise scoring is genuinely different from comparative
  selection (different failure modes, different prompt shapes,
  different telemetry). Conflating them under one name would
  obscure the distinction the experimental design depends on.
- **Parameterize a single selection node with a mode field
  (`PointWise | Comparative`).** Rejected for the same reason
  the Self/Peer review nodes were kept distinct: structural
  variations are cleaner as named nodes than as enum-tagged
  modes (mutation engine reasons over node classes; no
  field-validity rules to track).
- **Update the design to specify pointwise scoring as the B/C
  aggregation mechanism.** Rejected: all three independent
  reviewers read "chooses among the N candidates" as
  comparative selection; aligning code to the natural reading
  is preferable to rewriting the design to fit the
  implementation.

**Rationale:** Same pattern as the SelfReviseRound /
PeerReviseRound rename: the IR is a substrate for the broader
protocol-inventory space, not just for the locked Phase 1
conditions. Pointwise scoring (used by D, D' for ReConcile-
native confidence aggregation) and comparative selection
(used by B, C per the design) are both real macro-model
shapes. Keep both as typed building blocks.

**Implementation notes:**

- `PickOne` parses a 1-indexed candidate selection from the
  judge response (`_parse_pick`). Silent fallback to candidate
  1 on parse failure, mirroring the `_parse_score` pattern;
  this fallback shares the silent-failure / position-bias
  issue tracked under "Implementation bugs" in `docs/status.md`
  and will be fixed alongside the other parser fixes.
- Identity blinding preserved: candidates are presented as
  numbered options ("Candidate 1, Candidate 2, …"), never with
  vendor labels. Per the K=blinded lock.
- Call counts changed: B(N=3) and C now have N+1 calls (was
  2N). The architecture doc's smoke-test reference numbers were
  updated.

**Status:** Active. PickOne implemented; conditions B and C
migrated. ParScore + WeightedVote unchanged (still used by D,
D' via reconcile.py).

---

## 2026-04-16 Add ParPeerReview and FuseWithCritiques; condition E migrates; old variant kept

**Decision:** Add two new IR nodes — `ParPeerReview(models,
drafts, ctx, vis) -> [Critique[Answer[Draft]]]` (peer review
producing critiques only, cyclic 1-peer assignment, no
revision step) and `FuseWithCritiques(model, drafts,
critiques, query) -> Answer[Draft]` (a model reads drafts
paired with aligned critiques and writes fresh). Migrate
`condition_e` from `ParGen → PeerReviseRound → Fuse(meta over
revised drafts)` to the design-faithful `ParGen → ParPeerReview
→ FuseWithCritiques(meta over drafts + raw critiques)`. Keep
the previous shape as `condition_e_writers_revise_then_fuse`,
a documented alternative macro-model.

**Alternatives considered:**

- **Mutate `condition_e` in place.** Rejected for the same
  reason as the SelfReviseRound rename: the previous shape is
  a coherent macro-model worth keeping as a typed building
  block. Someone may want to ablate "does the writer-revision
  step before meta-synthesis help?" later.
- **Generalize `Fuse` to optionally accept critiques** (single
  node with optional critiques field). Rejected: matches the
  pattern of keeping structural variations as distinct named
  nodes (Self/Peer review, ParScore+WeightedVote vs PickOne).
  The mutation engine reasons over node classes; an
  enum-tagged or optional-field node introduces field-validity
  rules.
- **Decompose `PeerReviseRound` into `ParPeerReview` +
  `ParReviseFromCritiques`.** Considered. Would let
  `PeerReviseRound` become syntactic sugar for the composition
  and make the bundling structure explicit. Deferred — adds
  a third new node for marginal payoff at the moment. Worth
  revisiting if any macro-model wants to use the per-step
  decomposition directly.
- **Update the design to specify the "writers revise then
  meta fuses" variant as the canonical E.** Rejected: all
  three reviewers read the design's E as the meta-does-all-
  work version, and that version is structurally cleaner (no
  implicit aggregation rule). The previous implementation was
  a silent third option, neither of the two the design
  explicitly considered.

**Rationale:** Same pattern as the previous two reconciliations
in this round (Self/Peer review and PickOne for B/C). The IR
is a substrate for the broader protocol-inventory space; the
current design-faithful E and the previous "writers revise
first" variant are both real macro-model shapes. Keep both as
typed building blocks; phase1.py uses whichever matches the
locked design.

**Implementation notes:**

- `ParPeerReview` reuses the existing `peer_review_*` prompt
  templates (the review step is identical between
  `PeerReviseRound` and `ParPeerReview`; only the downstream
  differs — revise vs surface critiques).
- `FuseWithCritiques` adds one new prompt template
  (`fuse_with_critiques_user`) that frames the meta task as
  "synthesize a final response, drawing on drafts and
  critiques, write your own."
- The `drafts` ParGen is referenced twice in the new
  `condition_e` AST (once by `ParPeerReview`, once by
  `FuseWithCritiques`). The executor's identity-based
  memoization guarantees the meta-reviewer sees the same
  drafts that were peer-reviewed; no `bind` needed.
- Call counts: new E is 2N + 1 (down from 3N + 1). For Phase 1's
  3-subject-model E configuration, this is 7 (was 10).
  `condition_e_writers_revise_then_fuse` retains the 3N + 1
  shape.

**Status:** Active. ParPeerReview and FuseWithCritiques
implemented. `condition_e` migrated. The previous variant
remains callable as `condition_e_writers_revise_then_fuse`.
phase1.py uses `condition_e` (no change there). All three
faithfulness reconciliations from the cross-lineage review
round are now complete.

---

## 2026-04-16 Temperature policy: vendor default, not 0 or any fixed number

**Decision:** `ApiClient.temperature` is `Optional[float]`
defaulting to `None`. When None, the kwarg is omitted from
each provider call and each vendor's default temperature takes
over. Explicit numeric overrides remain available for
reproducibility testing and temperature ablations, but are not
used in the normal Phase 1 run.

**Alternatives considered:**

- **`temperature=0` uniform across providers** (the previous
  default). Rejected: Gemini's round-1 review observation
  showed that at `temperature=0`, `ParGen` on a homogeneous
  pool produces N identical drafts, mathematically collapsing
  Conditions B and D' into single-pass baselines. The round-2
  review reinforced this: with `PickOne`, B at `temperature=0`
  presents N indistinguishable candidates to the judge, which
  destroys the compute-scaling comparison. Forcing mode
  collapse defeats the experiment's purpose.
- **A specific non-zero temperature (e.g., 0.7) uniform across
  providers.** Rejected: each vendor has tuned its default
  for its own model family; picking a specific number is
  guessing against the vendor's tuning without evidence. "Same
  temperature policy across providers" was always a fair-
  comparison requirement; it is better read as same *policy*
  (leave it alone) than same *number*.
- **Make temperature a per-call field on prompt templates.**
  Rejected as premature until a concrete use case wants
  per-step temperature control.

**Rationale:** The original motivation for pinning temperature
was fair comparison across providers. But the interaction
between `temperature=0` and homogeneous-pool conditions
(collapsing them to single-pass baselines) was a larger threat
to fair comparison than the vendor-default variance this
policy was trying to eliminate. Leaving temperature at
vendor defaults restores the ensemble diversity that the
macro-model matrix depends on, without introducing a
guessed-number bias.

**Status:** Active. Implemented in
`src/executor/api_client.py`: `temperature: Optional[float] =
None` in `__init__`; provider calls conditionally include the
kwarg. Tests in `tests/test_api_client.py`.

---

## 2026-04-16 Phase 1 calibration parameters required, not defaulted

**Decision:** `build_phase1_conditions()` and
`build_phase1_spec()` take `best_model`, `n_samples_for_b`, and
`pricing` as required keyword arguments — no defaults.
Previously these were supplied by `_best_model()` (returning
Haiku as a "conservative" placeholder), `_n_samples_for_b()`
(hand-picked 1/3/6), and a hardcoded `PHASE1_PRICING`. All
round-1 reviewers flagged these placeholders as footguns:
running pre-calibration could silently violate the matched-
budget discipline at the heart of the research question.

The module constants stay (`SUBJECT_MODELS`, the renamed
`PHASE1_PRICING_DRAFT`), so a caller can explicitly pass them
after verifying — but bare `build_phase1_spec()` calls are no
longer possible.

**Alternatives considered:**

- **Gate the placeholders with a `calibrated=True` flag.**
  Works but is easier to bypass by accident.
- **Raise `NotImplementedError` from `_best_model()` and
  `_n_samples_for_b()`.** Fine for those two, but doesn't help
  with the pricing case (which had a real placeholder value).
  Making everything a required argument is more uniform.
- **Keep the placeholders and rely on an external pre-run
  check.** Rejected: the round-1 reviewers' concern was
  specifically that nothing forces the check. An external
  discipline that isn't enforced is a policy, not a gate.

**Rationale:** The matched-budget discipline is load-bearing
for the entire research question. Quietly miscalibrated
baselines would taint the main comparison. Making the builder
refuse to run without explicit calibration parameters is the
cheapest way to enforce the discipline — no new tooling, just
a function signature change.

**Status:** Active. Implemented in `src/experiment/phase1.py`;
tests in `tests/test_phase1.py`.

---

## 2026-04-19 Tie-break and parse-failure policy live on the AST, not the interpreter

**Decision:** Add `TieBreakPolicy` (RANDOM / FIRST / LAST) and
`ParseFailurePolicy` (RANDOM / RAISE) enums in
`src/ir/types.py`, alongside the existing `ContextMode` and
`Visibility` enums. Attach `tie_break: TieBreakPolicy =
TieBreakPolicy.RANDOM` to `WeightedVote` and
`on_parse_failure: ParseFailurePolicy = ParseFailurePolicy.RANDOM`
to `PickOne`. The interpreter dispatches on the enums (via
`_resolve_tie()` and `_recover_parse_failure()` helpers). Seeded
RNG stays on the interpreter as a run-level resource; what
moves to the AST is the *choice* of whether to use it.

**Alternatives considered:**

- **Leave the policies baked into the interpreter.** Status quo
  before this decision. Rejected: tie-break and parse-failure
  fallback are protocol-design choices, not executor
  implementation details. Hardcoding them at the interpreter
  level forecloses the design space — every `WeightedVote` /
  `PickOne` across every macro-model inherits the same rule,
  with no way to vary it per-condition or mutate it in
  follow-on ablations.
- **Sibling nodes per policy** (e.g., `WeightedVoteRandomTie`,
  `WeightedVoteFirstTie`). Rejected: tie-break and parse-
  failure don't change the node's type signature or the shape
  of its children. That's the structural cue the existing
  `ContextMode` / `Visibility` enums use: same type, same
  children, different behavior. Enum parameters match that
  precedent; sibling nodes are reserved for variations that
  change structure (Self/PeerReviseRound, ParScore+WeightedVote
  vs PickOne, Fuse vs FuseWithCritiques).
- **Only include RANDOM** in the enums. Rejected: if we're
  moving the policy to the AST at all, including the
  alternatives we've actually considered (FIRST = the old
  position-biased behavior, still occasionally desired for
  determinism; LAST as the symmetric counterpart; RAISE for
  tests and dry runs) is cheap and keeps the design space
  visible rather than hidden behind "add it later."

**Rationale:** The IR exists to be the substrate for the
protocol-inventory space, not just for the locked Phase 1
conditions. When a policy decision gets baked into the
executor, the IR stops being able to express the research
question the executor is enacting. This pattern —
interpreter-level fallback quietly growing into a protocol-
design choice — is the one Scott caught when reviewing the
operational-readiness fixes. Moving it up to the AST is a
structural correction, not a feature add.

Both Codex and Gemini missed this across four review rounds:
they treated the tie-break logic as an implementation detail.
The lesson for future review rounds is that any time a
reviewer-approved "implementation fix" introduces a policy
that affects measurement, it's worth checking whether the
policy belongs at the AST level.

**Status:** Active. Implemented in `src/ir/types.py`,
`src/ir/ast.py`, `src/ir/surface.py`, `src/ir/describe.py`,
`src/executor/interpreter.py`. Defaults preserve current
behavior (RANDOM for both). `ParseFailure` exception added to
`src/executor/interpreter.py` for the RAISE case. Tests in
`tests/test_interpreter.py` pin each enum value's dispatch
behavior.

---

## 2026-04-21 Include the task in revise and peer-review-D prompts

**Decision:** The `_REVISE_USER` prompt template now includes
the original task text (`{query}` variable at the top). The
ReConcile-style `condition_d` protocol now uses `ALL_VISIBLE`
visibility for peer review (was `PEERS_GROUPED`), so the peer
reviewer sees the original task alongside the target draft and
the other peers' drafts.

**Alternatives considered:**

- **Keep the status quo** (revise prompt has only `{critique,
  draft}`; D uses `PEERS_GROUPED` visibility, which hides the
  task from the reviewer). Rejected: under cross-lineage
  review of the BFCL widen session, Codex identified this as
  the concrete cause of a real capability failure
  (`parallel_2::calculate_resistance`), where a peer critique
  said "use the physical resistivity value, not just the
  label," and the revising writer had no way to cross-check
  that against the schema — because the schema/task was no
  longer in its context. Single-model runs of the same task
  passed; D failed. The status quo was a bug in the protocol
  definition, not a deliberate narrowing.
- **Treat the context-loss as a deliberate ablation variant
  to measure.** Rejected as a default: if the experimental
  framework's *default* peer-review behavior silently omits
  the task, every D result is measuring "collaboration
  degrades under schema-violating authoritative critique"
  rather than the intended "collaboration over solo." The
  ablation itself (does hiding the task hurt?) is valuable
  but should be an explicit variant of D, not the default.
  The current `PEERS_GROUPED` variant remains available in
  the IR for that future ablation.
- **Only fix the revise template, leave D's visibility at
  `PEERS_GROUPED`.** Rejected: the peer reviewer is asked to
  assess "Correctness" in the structured-critique dimensions
  list. Without the task, correctness is essentially
  unreachable — the reviewer can only pattern-match on what
  looks authoritative. That's the mechanism by which the
  plausible-sounding-but-wrong critique got through.

**Rationale:** This is a protocol-definition bug, surfaced by
cross-lineage review (Codex round-6, 2026-04-21) and validated
by re-running `parallel_2` with D: it failed before the fix,
passes after. The `_REVISE_USER` change adds `{query}` to the
template and updates three call sites in
`src/executor/interpreter.py` (self-revise, peer-revise, and
the standalone `Revise` IR node case) to pass
`target.production_query`. The `reconcile()` change swaps one
import (`PEERS_GROUPED` → `ALL_VISIBLE`) and the visibility
argument in `peer_rounds(...)`. Neither change adds new IR
constructs; both use the existing design's expressive range.

Neither Opus 4.7 (first-round system review), Codex, nor
Gemini caught this across the first five review rounds. Codex
found it in round 6 only because the BFCL widen validation
produced a concrete failure it could trace. The lesson: a
prompt template that *seems* self-contained may still be
mis-specified relative to what a downstream critique can do
with it; hermetic sealing from ground truth (the
selector-as-oracle discipline) should not be confused with
hiding the task from participants in a protocol round.

**Status:** Active. Implemented in
`src/experiment/prompts.py` (`_REVISE_USER` template),
`src/experiment/spec.py` (field-comment update),
`src/executor/interpreter.py` (three `revise_user.format(...)`
call sites), `src/protocols/reconcile.py` (import + protocol
body). Re-validation run: `parallel_2` under D, 1/1 pass
(was 0/1 before the fix); A and E remain passing.

---

## 2026-04-08 Small models as subjects, frontier models as judges

**Decision:** Use small/mid-tier models (e.g. Haiku, GPT mini, Gemini
Flash class) as the models under study, with frontier models as automated
judges.

**Alternatives considered:** Testing frontier models against each other
(stronger contribution but harder to judge automatically); testing only
open models (cheaper but less lineage diversity).

**Rationale:** Calibrating tasks so small models succeed ~40-60% one-shot
means those tasks should be easy for frontier judges, avoiding the main
failure mode of LLM-as-judge (judging at or above the judge's own
capability). This enables a mostly-automated evaluation pipeline. The
capability gap is a feature, not a limitation — it simulates the
weak-overseer-strong-agent dynamic the oversight literature cares about.

**Status:** Partially superseded (annotated 2026-07-24; see below)

**Annotation 2026-07-24:** the 2026-04-14 design split this
decision's judge role in two, and this entry was never updated
to say so (caught in discussion with Scott during the round-7
review period). (a) Judge-as-evaluation-instrument: removed
from Phase 1 in favor of executable scoring (walk-before-run);
frontier judges deferred to Phase 2 per
`docs/research/judge-design-notes_draft.md`, where this entry's
scheme and rationale remain the plan. (b) Judge-as-in-protocol-
aggregator: pinned to peer models drawn from the subject pool
(macro-model framing — the aggregator is part of the measured
macro-model and its cost counts toward the dollar budget; a
frontier judge would import capability from outside the pool
and change the claim). A frontier-judge-at-true-cost arm is a
candidate for the confirmatory phase alongside the router and
native-inference-scaling baselines. The subjects-side of this
decision (small models, three lineages) remains active.

## 2026-07-04 Kickoff decisions: LCB pool, BFCL dropped, fractional scoring, Gemini replaced

**Decision (four items, resolving the 4/28 kickoff blockers; Scott, via
decision packet in the work-graph workbench session):**

1. **LCB pool: expand.** Pull ~5 additional `test5`/`test4` releases to grow
   the medium+hard pool from N=86 toward N≈400 (the 80%-power threshold for
   the fallback test per `docs/research/power-analysis.md`).
2. **BFCL: dropped from Phase 1**, and the pre-declared **uniform middle-band
   fallback is adopted for the phase as a whole** (the power write-up's
   operational recommendation; SWE-bench's 500-instance ceiling forces the
   fallback structurally, and uniform application keeps the pre-registration
   unfragmented). Function-calling coverage may return in Phase 1.5 via
   `live_*` expansion if wanted.
3. **LCB scoring: mean_fraction.** The declared 45–55% middle band exists for
   the best subject only under fractional scoring (0.54 vs 0.34 strict).
   Carries an implementation note: the power analysis assumed a binomial GLM,
   so the test moves to test-case-level binomial or beta regression —
   kickoff work, not a design change.
4. **Gemini subject: gemini-2.5-flash replaced by gemini-3-flash** (newly
   available since the April calibration), preserving the three-lineage
   cross-critique signal the D-family requires. Requires one cheap
   recalibration of the Gemini cells.

**Alternatives considered:** staying at N=86 (underpowered); BFCL `live_*`
expansion (uncertain payoff against structural saturation) or replacement
benchmark (longest delay); strict scoring (kills the middle band); keeping
2.5-flash (noise, not signal, beyond easy) or a two-lineage LCB bucket
(weakens heterogeneity comparison).

**Status:** Active. Kickoff is no longer decision-blocked; remaining
pre-kickoff work is the SWE-bench Verified adapter (multi-session),
run-manifest schema (~½ session), the LCB pool pull, and the gemini-3-flash
recalibration run.


## 2026-07-23 Round-7 pre-resume patch set: task-visible aggregation, truncation telemetry, abort taxonomy

**Context.** The round-7 cross-model review (Fable 5, GPT-5.6
Sol, Grok 4.5, Kimi K3 — 4/4 Revise-and-re-review; synthesis at
`docs/reviews/synthesis-round7-2026-07-23.md`) converged on a
set of verified measurement-integrity defects while the N=86
pilot was mid-flight. The pilot was paused (A-columns complete)
and this patch set applied before resuming. Confirmatory-phase
items (recalibration protocol, cap-policy decision, fractional
power analysis, execution sandboxing) are deliberately NOT
included and remain open.

**Decisions.**

1. **Aggregation steps see the task.** `_PICK_ONE_USER` and
   `_SCORE_USER` now carry `{query}`; Condition E's peer review
   moved from `PEERS_GROUPED` to `ALL_VISIBLE`. Extends the
   2026-04-21 principle (hermetic sealing from ground truth ≠
   hiding the task from participants) to the selection layer,
   where three of four reviewers independently found it missing.
2. **ParScore parse failure is an AST-level policy.** Same
   `ParseFailurePolicy` enum as PickOne; RANDOM now draws a
   seeded uniform value instead of the previous hardcoded 0.5
   (which fabricated deterministic mid-confidence). Completes
   the 2026-04-19 decision's half-applied lesson.
3. **Truncation is telemetry, not silence.** All four provider
   adapters read the finish/stop reason; `CallRecord.truncated`
   plus per-task `truncated_calls` make length-cut responses
   visible. Policy: a truncated response still scores as-is —
   a bounded harness is part of the measured system — but the
   event is always counted. The Google visible/thoughts token
   split is recorded (`CallRecord.thoughts_tokens`); billing
   already included thoughts.
4. **Three-way abort taxonomy with one denominator rule.**
   New `ProviderRefusal` class for provider-side moderation
   declines (neither capability nor infra; vendor-asymmetric at
   scale). Rule, applied identically in `ConditionResults.
   pass_rate` and driver summaries: capability failures score 0
   and are INCLUDED; infra failures, provider refusals, and
   unexpected harness errors are EXCLUDED and reported as
   separate counts. Previously the library excluded all aborts
   while the pilot summary included them.
5. **PickOne presents candidates in seeded-shuffled order**,
   mapping the parsed index back through the permutation, so
   judge position bias cannot systematically favor a vendor (C)
   or early samples (B). Reviewer-rotation for D is deferred to
   the confirmatory phase and documented as a known asymmetry.
6. **In-process spend cap** (`--max-dollars`) in the pilot
   driver; graceful stop with resumable checkpoint.

**Alternatives rejected for now.** Equalizing all providers to
one giant shared output cap (Grok/Fable's preference) — kept
the 8x Google asymmetry as an instrumented, now-measurable
deviation pending the cap-policy decision entry; retrying
truncated calls with larger budgets — changes the measured
system mid-pilot.
