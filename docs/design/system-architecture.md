# System Architecture

The implementation-side design doc for the model collaboration
study. This is the permanent home for what has been built and what
the planned shape of the system is. Independent of the experimental
design (variables, tasks, judges) — those live in
`docs/research/experimental-design.md`.


## Three-layer architecture

The system is organized as three layers, each with a different
responsibility and a different audience:

```
┌─────────────────────────────────────────┐
│ 1. Prose inventory                      │  human-readable design space
│    docs/research/protocol-inventory.md  │  semi-formal notation
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ 2. Typed protocol IR                    │  executable abstract structure
│    src/ir/, src/protocols/              │  Python typed AST
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ 3. Experiment spec layer                │  concrete instantiation
│    src/experiment/                      │  prompts, models, tasks, budgets
└─────────────────────────────────────────┘
```

**Why the split exists.** The IR is about the *abstract structure*
of a multi-model protocol — who reviews what, with what visibility,
in how many rounds. It deliberately excludes anything that varies
per experiment: which concrete models, which prompt templates,
which task slice, which judges, what budget. Those belong in the
experiment-spec layer. The split lets a single IR definition of
(say) ReConcile be instantiated against many model assignments and
task sets without duplicating the protocol logic.

**Audiences.** The prose inventory is for humans thinking about
what to test. The typed IR is what tools (the executor, the
mutation engine, the type checker) consume. The experiment-spec
layer is what an experiment runner consumes.

This split was Codex's early push and was accepted after some
back-and-forth about whether it was just "spec vs implementation."
It's slightly more than that: the IR is the *abstract* protocol,
the experiment spec is the *concrete instantiation*.


## Layer 1: Prose inventory

`docs/research/protocol-inventory.md` is a human-readable catalog of
multi-model collaboration protocols using a semi-formal notation.
It is the thinking tool, not the execution artifact. It documents
roughly 37 protocol variants and 19 structural variables across
families like CCR, debate, ReConcile, RouteLLM, judge panels, etc.

Things the inventory can express that the IR can't yet (deliberately
deferred — wait for a concrete use case before adding nodes):

- Blackboard protocols
- Dynamic topology
- Agentic trajectories

The IR will grow toward these as concrete needs arise. Don't try to
force them in speculatively.


## Layer 2: Typed protocol IR

The IR is the object of study. It's what gets type-checked,
serialized, traversed by the executor, and (eventually) mutated by
the autoresearch engine. Every architectural decision below was
made with mutation safety in mind.

### Language choice: Python with surface authoring layer

Python typed AST, validated under `mypy --strict`. The decision
was made after writing both Python and Haskell versions side-by-side
and consulting Codex and Gemini. Haskell has nicer authoring syntax
but loses at the HOAS-serialization boundary and can't own the
mutation engine, which is Python-native by necessity (interleaved
with execution and API calls). The surface authoring layer
(`src/ir/surface.py`) brings Python ergonomics close enough to the
Haskell aesthetic that the loss is acceptable.

The Haskell reference at `src/ir_haskell/ProtocolIR.hs` stays as
documentation of the target aesthetic, not as a source language.

### Type universe (`src/ir/types.py`)

The IR types describe what flows through a protocol, not just data
shapes:

- `Query` — the input task
- `Answer[Stage]` — a response, parameterized by lifecycle stage
- `Critique[T]` — feedback targeting `T`
- `Flag[T]` — structured problem marker (location + label, no rationale)
- `Score[T]` — numeric quality signal for `T`

**Stage tags as phantom types.** `Draft`, `Final`, and `Plan` are
nominal types used as phantom parameters on `Answer`. `Answer[Draft]`
is in-progress and revisable; `Answer[Final]` has been committed.
The type checker prevents accidentally feeding a draft into a step
that expects a final answer. Mutations that violate stage
invariants fail at edit time.

**Parameterized judgment types.** `Critique[Answer[Draft]]` and
`Critique[Answer[Final]]` are distinct types even though both carry
text. This prevents a mutation engine from substituting a critique
of one target for a critique of another.

### Annotations: ContextMode and Visibility

Two enum-valued parameters that are the main structural knobs for
many protocols:

- `ContextMode.{FRESH, ACCUMULATED}` — whether a step runs in a
  fresh context or inherits session history
- `Visibility.{ARTIFACT_ONLY, WITH_PRODUCTION, PEERS_GROUPED, ALL}`
  — what a reviewer sees alongside the target artifact

These are not types in the strict sense — they don't change type
signatures — so mutations can flip them freely. They're the
"cheap, type-safe knobs" the mutation engine will turn most often.

### AST nodes (`src/ir/ast.py`)

The current node set, all frozen dataclasses inheriting from
`Expr[T]`:

| Node            | Type signature                                                            |
|-----------------|---------------------------------------------------------------------------|
| `QueryVar`      | `Query`                                                                   |
| `Gen`           | `Model -> Query -> Answer[Draft]`                                         |
| `Review`        | `Model -> Answer[Draft] -> Critique[Answer[Draft]]`                       |
| `Revise`        | `Model -> Answer[Draft] -> Critique[Answer[Draft]] -> Answer[Draft]`      |
| `Finalize`      | `Answer[Draft] -> Answer[Final]`                                          |
| `ParGen`        | `[Model] -> Query -> [Answer[Draft]]`                                     |
| `ReviseRound`   | `[Model] -> [Answer[Draft]] -> [Answer[Draft]]`                           |
| `Rounds`        | `Int -> [Model] -> [Answer[Draft]] -> [Answer[Draft]]`                    |
| `ParScore`      | `[Model] -> [Answer[Draft]] -> [Score[Answer[Draft]]]`                    |
| `Fuse`          | `Model -> [Answer[Draft]] -> Query -> Answer[Draft]`                      |
| `WeightedVote`  | `[Answer[Draft]] -> [Score[Answer[Draft]]] -> Answer[Draft]`              |
| `Var`           | reference to a Let-bound variable                                         |
| `Let`           | `Expr[T1] -> (Expr[T1] -> Expr[T2]) -> Expr[T2]`                          |

**Why bundled nodes like `ReviseRound` and `Rounds` exist.** They
are not primitives — `ReviseRound` is morally
`[revise(m_i, d_i, review(m_i, d_i, peers)) for ...]`, and `Rounds`
is just N applications of `ReviseRound`. They exist as single
nodes because:

1. Mutating "the number of rounds" should be a local field change,
   not a structural tree edit.
2. Unrolling N rounds across M models would balloon the AST and
   slow traversal.
3. Some node should "own" the per-round semantics so the mutation
   engine has a clean target.

Add a primitive only when a protocol forces a per-step variation
that the bundle can't express.

**Fuse and the "many → one" family.** `Fuse` is a model that
reads multiple peer drafts and writes a fresh response — needed
for Condition E's meta-reviewer. It's one member of a family of
operations that share the shape "model reads multiple artifacts
and writes fresh" but differ in what those artifacts are:

- `Fuse`: `[Answer[Draft]] → Answer[Draft]` — this node
- `ReviseFromMany`: `Answer[Draft] + [Critique] → Answer[Draft]`
  — future, for multi-critic revision
- Pre-draft advisory synthesis: `Query + [Advisory] → Answer[Draft]`
  — future, needs a new type for advisory inputs

Named specifically to leave namespace room for the siblings.
Add them when a concrete protocol requires them.

**Runtime type reification.** Every node has a `result_type`
attribute readable at runtime — a `ClassVar` for fixed-type nodes,
an instance field on `Var` (propagated from the bound value), a
`@property` on `Let` (delegating to body). This is for the
mutation engine, which can't rely on `mypy` or `typing.get_args()`
at runtime. Gemini flagged this as the foundation work needed
before the mutation engine itself can be written.

### Surface authoring layer (`src/ir/surface.py`)

A thin facade in front of the AST classes:

- Lowercase factory functions: `query()`, `gen()`, `review()`,
  `revise()`, `finalize()`, `par_gen()`, `revise_round()`, `rounds()`,
  `par_score()`, `weighted_vote()`.
- Bare enum constants: `FRESH`, `ACCUMULATED`, `ARTIFACT_ONLY`,
  `WITH_PRODUCTION`, `PEERS_GROUPED`, `ALL_VISIBLE`.
- `bind(value, lambda v: body)` for Let bindings, with optional
  debug name hint.

Protocol definitions in `src/protocols/` import from `surface`,
not from `ast`. The core IR remains the source of truth; the
surface layer just changes the authoring ergonomics.

### Let bindings: HOAS authoring, first-order storage

Let bindings let you name a sub-expression so it can be referenced
multiple times in a body without duplicating the AST. The
authoring API uses a Python closure (HOAS):

```python
bind(
    rounds(n, models, par_gen(models, q)),
    lambda r: finalize(weighted_vote(r, par_score(models, r))),
)
```

Internally we store the body as a static `Expr` with a `Var` node
substituted for the binding, not as a closure. This keeps the AST
pure-data for serialization, mutation, and traversal, while still
letting the user write the natural closure form.

**Alpha-equivalence is a known limitation.** `Let.var_name` is
debug metadata only. Two Lets that differ solely in their
generated variable name are semantically identical. The current
dataclass-generated `__eq__` is *not* alpha-aware. Callers needing
alpha-equivalence should use a dedicated structural comparison;
this will be revisited when serialization / canonicalization land.

### Sharing semantics

A subtree referenced multiple times in the AST means *the same
runtime value*. The user writes:

```python
d = gen(model, q)
return finalize(revise(model, d, review(model, d, FRESH, ARTIFACT_ONLY)))
```

`d` appears in both the `review` and the `revise` call. There is
exactly one draft, reviewed and then revised. The executor honors
this via identity-based memoization (see below). Authors who want
two independent drafts must write two separate `gen(...)` calls.


## Layer 3: Executor (`src/executor/`)

A minimal tree-walking interpreter that turns an `Expr` into an
actual run by calling a model client. The first version covers
every node currently in the IR, so CCR and ReConcile run end-to-end.

### Components

- `runtime.py` — runtime value types (`RQuery`, `RAnswer`,
  `RCritique`, `RScore`). `RAnswer` carries a stage tag (`Draft`
  or `Final` class) and a small amount of provenance
  (`production_query`) needed for `WITH_PRODUCTION` reviews.
- `client.py` — `ModelClient` Protocol with one method:
  `complete(model, system, user) -> str`. `FakeClient` is a
  deterministic stand-in for tests, recording every call and
  returning structured strings. A real client (Anthropic, OpenAI)
  satisfies the same Protocol.
- `interpreter.py` — `Interpreter` class with `evaluate(expr, env)`
  that pattern-matches on AST nodes. `Env` is an immutable
  binding environment for `Let`/`Var`. `run(expr, client, query)`
  is the top-level entry point.

### Identity-based memoization

The interpreter caches results by `id(expr)` so a shared sub-expression
produces the same runtime value every time it's referenced. This
matches the sharing semantics described above. Without it, CCR
would issue four model calls (gen, gen, review, revise) instead of
the expected three.

The cache is per-`run`; it's instantiated fresh on each `Interpreter`
construction. Identity-keyed caching is safe because:

- The IR is immutable.
- `Var` instances are uniquely created by `Let.make` with fresh
  names, so within a single run a `Var`'s identity uniquely
  determines its binding.

### Placeholder prompts

The interpreter currently inlines default prompt templates
(`GEN_USER`, `REVIEW_ARTIFACT`, etc.). These are explicitly
placeholders — they belong in the experiment-spec layer. When that
layer exists, the interpreter will accept prompt templates as
configuration instead of inlining them.

### What ContextMode does in the executor today

`FRESH` vs `ACCUMULATED` only matters for clients that maintain
session history. The current executor passes a different system
string but otherwise treats both modes identically. Implementing
real session continuation requires a stateful client and is
deferred until a real client is wired in.


## Layer 3: Experiment spec (`src/experiment/`)

Maps an IR protocol expression plus concrete inputs into a
runnable experiment. The spec layer fully determines a run:
which macro-model conditions to compare, on which tasks, at
what dollar budgets, with which prompt templates.

### Core types (`src/experiment/spec.py`)

| Type              | Purpose                                                        |
|-------------------|----------------------------------------------------------------|
| `BudgetTier`      | Dollar tiers (X, 2X, 4X) anchored to Condition A cost         |
| `PricingEntry`    | Per-model pricing anchor (in/out per 1M tokens)                |
| `PricingTable`    | Pinned pricing for all models; computes call costs and caps    |
| `Stratum`         | Difficulty band defined by one-shot success rate range          |
| `TaskBucket`      | Benchmark + instance IDs                                       |
| `PromptTemplates` | Templates for gen, review, revise, score (replaces interpreter placeholders) |
| `RetryPolicy`     | Infrastructure-failure retry (separate from capability failures)|
| `ConditionSpec`   | One cell of the matrix: name + label + IR tree + tier + models |
| `ExperimentSpec`  | Complete spec: conditions, tasks, strata, pricing, prompts     |

### Prompt templates (`src/experiment/prompts.py`)

Default structured-critique templates for Phase 1. The critique
rubric dimensions (correctness, completeness, unnecessary
assumptions, tool-use correctness, code safety, confidence) match
`docs/research/experimental-design.md`. The interpreter still
uses its own hardcoded placeholders until the integration is wired;
the spec-layer templates are the canonical source and will replace
the interpreter's strings when the real `ModelClient` lands.

### Phase 1 builder (`src/experiment/phase1.py`)

Constructs the concrete Phase 1 `ExperimentSpec`: 12
condition-tier pairs (A at $X; B at $X/$2X/$4X; C, D, D', E each
at $2X/$4X), three task buckets (SWE-bench Verified,
LiveCodeBench, BFCL), three difficulty strata, pinned pricing.

### Condition factories (`src/protocols/conditions.py`)

Phase 1 macro-model factories, each returning a typed IR
expression:

- `condition_a(model)` — single Gen
- `condition_b(model, n_samples)` — ParGen + ParScore + WeightedVote
- `condition_c(subject_models, judge_model)` — heterogeneous ParGen + peer scoring
- `condition_d` — re-exported `reconcile()` from `reconcile.py`
- `condition_d_prime(model, pool_size, n_rounds)` — homogeneous ReConcile
- `condition_e(subject_models, meta_reviewer)` — ParGen + ReviseRound + Fuse

All six build cleanly, pass `mypy --strict`, and run end-to-end
through the executor with `FakeClient`.

### Why the spec layer is separate from the IR

A single IR definition of ReConcile should be runnable against
many model pools, prompt variants, and task slices without
copy-pasting the protocol structure. The spec layer handles the
concrete instantiation: which models, which prompts, which tasks,
what budget. The IR handles the abstract protocol structure: who
reviews what, with what visibility, in how many rounds.


## Validation discipline

- `mypy --strict` passes on `src/ir/`, `src/protocols/`,
  `src/executor/`, and `src/experiment/`. Treat strict-mode
  failures as bugs.
- Deliberately-broken protocols produce the expected type errors
  at check time. This is the bedrock of mutation safety: if a
  mutated protocol type-checks, it has a fighting chance of running.
- The executor has been smoke-tested end-to-end with a
  deterministic `FakeClient` against CCR (3 calls), SA (3 calls,
  production query visible to reviewer), ReConcile (12 calls
  for 2 models × 2 rounds + 2 par_score, 4 for the 0-round
  ablation), and all six Phase 1 condition factories (A: 1 call,
  B(N=3): 6 calls, C: 6 calls, D: 12 calls, D': 12 calls,
  E: 10 calls).


## Looking ahead

These are identified but not in progress. Listed so they aren't
lost.

**Mutation engine.** Type-preserving subtree replacement, driven
by `result_type`. Will need a scoped-traversal visitor that tracks
`Let` binding scope. Codex flagged that explicit role/actor
metadata may become necessary if mutations start quantifying over
"all reviewer steps" independent of node kind — wait for a use
case.

**Sharing recovery from Python object identity.** An authoring
helper that detects shared subexpressions by `id()` and lowers
them to explicit `Let`s automatically. Wait until manual `bind()`
feels painful.

**Micro-parser for a text DSL.** A small parser for a Haskell-like
text syntax that produces the Python AST. Defer until the surface
layer feels inadequate.

**Prompt template integration.** The experiment-spec layer defines
`PromptTemplates` with structured-critique defaults. The executor
still inlines its own placeholder strings. When the real
`ModelClient` lands, the interpreter should accept a
`PromptTemplates` instance and use it instead of the hardcoded
strings.

**Real model clients.** Anthropic and OpenAI adapters satisfying
the `ModelClient` Protocol. Trivial mechanically; the design
question is how session/`ACCUMULATED` mode maps onto the real APIs.

**Replication ladder.** CCR → PoLL → ReConcile → RouteLLM /
FrugalGPT → Debate or Vote → ColMAD. CCR and ReConcile already
exist in `src/protocols/`. Phase 1 conditions A–E are expressed
as factories in `src/protocols/conditions.py`. The remaining gap
is the real `ModelClient`.
