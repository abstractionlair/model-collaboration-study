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

**Status:** Active
