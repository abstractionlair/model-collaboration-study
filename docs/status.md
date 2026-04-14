# Project Status

**Last updated:** 2026-04-14

A rolling snapshot of where the project is. Updated at natural
checkpoints. Read this at the start of a session to know what's
happening without replaying the whole conversation.


## Current phase

**Inspiration → Question transition, with DSL infrastructure being
built in parallel.** The protocol inventory is mature enough to drive
implementation; the experimental design isn't formalized yet but the
pilot replications will inform it.


## What's been decided

### Motivation (locked)

Capability-enhancement-first: "Can we systematically enable more
capabilities in a collaborative process involving multiple models
than any of the models exhibit themselves?" Alignment/oversight
applications are secondary — particularly the future scenario where
earlier-generation aligned models help steer newer frontier models.

### Experimental approach (locked)

- Small API models as subjects, frontier models as automated judges.
- Tasks calibrated to the subjects' capability level so the judges
  operate comfortably within their own competence envelope.
- Compute-matched comparisons across protocols.
- Phased: method validation on API models first; transfer tests and
  human validation later.

### Protocol notation (locked)

- Three-layer architecture:
  1. **Prose inventory** (`docs/research/protocol-inventory.md`) —
     human-readable description, semi-formal notation, design space.
  2. **Typed protocol IR** (`src/ir/`, `src/protocols/`) — executable
     core, Python typed AST, `mypy --strict` validated.
  3. **Experiment spec layer** (not yet built) — model assignments,
     prompt templates, judge config, budgets, task slices, metrics.

- Language choice: **Python with a surface authoring layer**, not
  Haskell. Decision made after writing both versions side-by-side and
  consulting Codex and Gemini. Haskell has nicer authoring syntax but
  dies at the HOAS-serialization boundary and can't own the mutation
  engine, which is Python-native by necessity. The surface layer
  (`src/ir/surface.py`) brings Python ergonomics close enough to the
  Haskell aesthetic.

- The Haskell reference implementation at `src/ir_haskell/ProtocolIR.hs`
  stays as documentation of the target aesthetic, not as a source
  language.

### Replication ladder (locked)

Start simple, build complexity. The first replications validate the
language and harness before stacking complexity:
1. Cross-Context Review (CCR) — simplest; tests context/visibility
   annotations.
2. PoLL / judge-panel — tests the evaluation layer (judging
   methodology, not protocol IR).
3. ReConcile — first rich multi-model protocol; stress-tests the
   language.
4. RouteLLM or FrugalGPT — routing/cascade competitor family.
5. Debate or Vote — once the simpler harness pieces are stable.
6. ColMAD — collaborative vs adversarial framing test.


## What's been built

### Protocol IR (`src/ir/`)

- `types.py` — Q, P, R, F, S, D, A type universe with stage tags
  (Draft, Final, Plan), parameterized by target where meaningful.
  ContextMode and Visibility enums.
- `ast.py` — typed AST node classes. Currently: QueryVar, Gen,
  Review, Revise, Finalize, ParGen, ReviseRound, Rounds, ParScore,
  WeightedVote, Var, Let. All constructed as frozen dataclasses.
- `surface.py` — lowercase authoring API: `query()`, `gen()`,
  `review()`, `revise()`, `finalize()`, `par_gen()`, `rounds()`,
  `par_score()`, `weighted_vote()`, `bind()`. Bare enum constants
  (FRESH, PEERS_GROUPED, etc.).
- `describe.py` — one interpreter (pretty-printer) that walks the
  AST and renders indented prose.
- `__init__.py` — re-exports everything relevant.

### Protocols (`src/protocols/`)

- `ccr.py` — CCR, SR, SA (Cross-Context Review and same-session
  baselines from Song 2026).
- `reconcile.py` — ReConcile (Chen, Saha, Bansal 2024) and the
  zero-rounds ablation.

### Validation

- `mypy --strict` passes on all IR and protocol files.
- Deliberately-broken protocols produce the expected type errors at
  check time.
- `describe()` renders all protocols cleanly with Let-sharing
  preserved.

### Literature

- `docs/literature/protocol-literature-search-codex-2026-04-08.md` —
  merged literature search with ~170 papers across all protocol
  families.
- `docs/literature/paper-votes.md` — multi-model voting (Claude,
  Codex, Gemini) on which papers to read carefully. 37 papers with
  arXiv IDs fetched in full text.
- `data/papers/` — full text in LaTeX/HTML/PDF for 37 voted papers.

### Coordination infrastructure

- MCP channels to Codex (session `mcs-coord`) and Gemini
  (session `mcs-coord-gemini`) are working. Both have been briefed
  on the project and participate in joint design discussions.
- Claude evaluates Codex's suggestions critically per
  [codex_critical_eval memory](memory/codex_critical_eval.md); same
  principle should apply to Gemini.

### Project config

- `CLAUDE.md` is the shared reference (with `AGENTS.md`, `GEMINI.md`,
  `.codex` as symlinks). Contains project brief, workflow shape, and
  pointers to WORKFLOW.md for detail.
- `WORKFLOW.md` is the procedural reference.


## Where we are right now

Just finished a long design discussion about the protocol IR
language, culminating in:
1. Writing the surface layer (`src/ir/surface.py`).
2. Rewriting CCR and ReConcile against it.
3. Consulting Codex and Gemini on whether the surface layer closes
   the ergonomics gap.

Both models confirmed the surface layer is adequate and gave
concrete follow-up suggestions. Claude and Scott agreed on a small
set of immediate actions and a larger set of deferred work.


## Immediate next actions (not yet done)

From the Codex + Gemini synthesis, do these before the next
substantive design session:

1. **Make `name` parameter optional in `bind()`** — most calls
   shouldn't need it. Generate fresh names silently when omitted.
2. **Fix `surface.py` docstring** — the module docstring claims the
   Let binding is an Expr method, but the implementation is a free
   function `bind()`. Make the doc match the code.
3. **Add runtime type reification to AST nodes** — each Expr subclass
   should have a `result_type` class attribute (or equivalent) so the
   mutation engine can introspect types at runtime without relying on
   `typing.get_args()`. This is Gemini's concrete ask for preparing
   the mutation engine foundation.
4. **Document the Let alpha-equivalence issue** — Codex flagged that
   `var_name` in Let should be debug metadata only, not semantic
   identity. Add a comment in `ast.py` noting that alpha-equivalent
   Lets must compare as equal. Defer the actual hashing/equality
   implementation until serialization work.

### Deferred (identified, not scheduled)

These came up in the Codex/Gemini discussion but shouldn't be done
speculatively:

- **Scoped traversal visitor for Let bindings.** Gemini flagged that
  the mutation engine will need a visitor that tracks variable scope
  as it walks the tree. Wait until we actually write the mutation
  engine.
- **Explicit actor-role axis.** Codex flagged that if mutations start
  quantifying over "all reviewer steps" independent of node kind,
  we'll need explicit role metadata. Wait until a use case forces it.
- **Sharing recovery from Python object identity.** Codex sketched an
  authoring layer that could detect shared subexpressions by object
  identity and lower to explicit Lets automatically. Wait until
  `bind()` feels painful.
- **Micro-parser for a text DSL.** Gemini's option 4: write a small
  parser for a Haskell-like text syntax that produces the Python AST.
  Defer until the current surface layer feels inadequate.


## Next session starting point

**Read this file first**, then:

1. Do the four immediate actions listed above (small, ~1 hour total).
2. Move to the replication ladder. The next substantive piece is
   **building a minimal executor interpreter** that walks the typed
   AST and actually calls APIs. Start with CCR because it's simplest
   and the paper has a clear task set to compare against.
3. After the executor works end-to-end on CCR, start the
   experiment-spec layer — the thing that maps a protocol IR plus
   concrete models, prompts, task sets, and judge config into an
   actual experiment run.


## Open threads worth remembering

These came up in the long discussion and shouldn't be lost:

- **Scott's larger autoresearch ambitions.** Beyond parameter tuning,
  he wants structural search over protocol shapes — the typed AST
  design is oriented toward this. The mutation engine should operate
  on type-preserving subtree replacements, not just field tweaks.
- **Protocol/experiment-spec split is a key separation**. Things
  like model assignments, prompt templates, budgets, metrics, task
  sets, judge config are *not* in the protocol IR. The IR is about
  abstract structure. Experiment specs instantiate an IR into a
  runnable experiment. This was Codex's early push and we accepted
  it.
- **Gemini observed that mutation engines need runtime type
  reification.** Mypy only runs at edit time. When the mutation
  engine generates candidate ASTs, it needs to filter by type
  without relying on mypy. Immediate action #3 addresses this.
- **Scott noted the recursion prediction.** Applying collaborative
  protocols to their own sub-tasks probably doesn't help at Phase 1
  difficulty but would at higher complexity. Worth testing later.
- **Codex and Gemini both have MCP sessions in the repo** — use
  them for substantive design questions, not for routine work.
- **The `protocol-inventory.md` has things the current IR can't
  express cleanly yet** — blackboard protocols, dynamic topology,
  agentic trajectories. These are documented but not in the IR.
  Don't try to force them in; add nodes when a concrete use case
  demands them.


## Pending replication targets

The replication ladder (CCR → PoLL → ReConcile → RouteLLM/FrugalGPT
→ Debate or Vote → ColMAD) is the primary near-term driver. CCR is
already expressible in the IR; ReConcile is already expressible in
the IR. The gap is the **executor** — we can describe these protocols
but can't run them yet.

Papers are at `data/papers/` if needed.
