# DSL Design Discussion — Context for Codex

**Status:** Working discussion between Scott and Claude. Seeking Codex's
open-ended input.

This document captures the arc of a discussion about what kind of
language/representation we should use to describe multi-model
collaboration protocols, and why. It includes options we considered,
discarded, and landed on tentatively. Codex is being asked for
open-ended opinions and suggestions — including "you're missing X" or
"I'd approach this differently."


## The starting point

We have `docs/research/protocol-inventory.md`, which contains a
semi-formal description of ~37 multi-model collaboration protocols
using typed primitives (M_gen, M_review_R, M_edit, M_fuse, M_select,
etc.), a type universe (Q, P, R, F, S, D, A), and composition
operators (sequential, parallel, conditional). Codex wrote a large
portion of the current state of this file.

We were discussing whether the notation was sufficient and what we'd
need from it going forward.


## Motivation clarified

Scott's project motivation is capability-enhancement-first:
"Can we systematically and reliably enable more capabilities in a
collaborative process involving multiple models than any of the models
exhibit themselves?" Alignment/oversight is a secondary application.

Scott also wants to enable an autoresearch-like workflow eventually
(following Karpathy's sense) where an automated process proposes and
runs experimental variants of protocols. He hinted at larger ambitions
than simple parameter sweeps — he wants meaningful structural search,
not just hyperparameter tuning.

He also mentioned wanting to replicate a few known papers as an early
test that the language and harness work correctly. The agreed replication
ladder is: Cross-Context Review first, then a judge-panel paper (PoLL),
then ReConcile, then RouteLLM/FrugalGPT, then Debate or Vote, then
ColMAD.


## Design questions we worked through

### Q1: Does the capability-first framing change the notation?

**Resolved:** No, not substantially. The notation describes pipeline
structure, which is useful regardless of whether the goal is catching
errors or enhancing capabilities. The typed artifacts and composition
operators work for both. What changes is which protocols we prioritize
testing, not how we describe them.

### Q2: What's the status of the current notation?

**Resolved:** The current `protocol-inventory.md` is the shared
reference. Claude wrote the original small sketch; Codex expanded it
significantly. Both treat the current file as baseline. Scott hadn't
explicitly confirmed this but it's been the working assumption.

### Q3: Should the notation have per-step metadata fields (actor,
inputs, output type, context mode, visibility/blindness)?

**Partially resolved:** Codex proposed a two-layer split — prose
inventory as a description language (compact, readable, annotations
only where they matter) and a later execution schema (explicit, typed,
machine-checkable fields per step). This split was initially compelling
but then got reframed (see below).

### Q4: What's the right representation for the execution/machine-
checkable layer?

**This is the main unresolved question.** We considered several
options.


## Options we considered

### Option A: Real Haskell

Write actual Haskell using tagless final or free monads. Type checker
does linting for free. Multiple interpreters from one source (describe,
execute, cost-estimate, lint, visualize). Most rigorous.

Rejected because: the empirical side of the project (API calls, judges,
statistics, plots) pulls toward Python. Running API calls from Haskell
is possible but awkward. Tooling overhead is high if the only runtime
job is orchestrating a handful of protocols.

### Option B: Haskell-inspired text DSL parsed in Python

Define a text format that looks like Haskell but isn't actual Haskell.
Parser in Python. Readable for humans, no GHC dependency, but we have
to implement the parser and type checker ourselves.

Set aside because: the DSL-as-parser approach duplicated work the host
language could do for free, and it wasn't clear the aesthetic gain was
worth the parser complexity.

### Option C: Python with types as the DSL

Skip the separate language entirely. Protocols as Python functions
with type hints. Use mypy for static checking. Multiple interpreters
via standard Python (strategy pattern, ABCs). Stays in one language.

This was Claude's tentative recommendation. Pragmatic. Less elegant
than Haskell but much less infrastructure.

Scott's reaction: "I like the look of your Haskell example earlier a
lot more than this Python one." So pure aesthetic preference leans
Haskell.

### Option D: YAML configurations over a small library of protocol shapes

Claude's earlier proposal for the autoresearch angle: define a small
set of protocol shapes (reconcile, debate, hierarchical_review, etc.)
in code, parameterize each with a YAML schema, and have autoresearch
mutate YAML configs within each schema.

Pros: mutations are safe by construction (schema bounds the space).
Cons: limits mutation to parameter tuning within a fixed set of protocol
shapes. Structural innovation (new protocol topologies) requires human
design.


## The key reframe — typed structural mutation

Scott pushed back on the split between "parameter tuning is safe,
structural changes are dangerous." His claim: if the type system is
rich enough, structural changes can also be safe. Quoting him:

> I have larger ambitions for the autoresearch but I also have an
> intuition that we can make structural changes safer via type safety.
> At a super high level, we have types like CandidateResponse,
> Response (which include CandidateResponse), Query, AdviceOnQuery,
> FeedbackOnResponse, ... and methods with signatures like
> (Response, FeedbackOnResponse) -> CandidateResponse, or
> (Query, AdviceOnQuery) -> CandidateResponse, maybe some query
> modifiers, ... Then, in Haskell spirit, the idea is that if the
> types work ("it compiles") it is highly likely to run.

This is the typed-genetic-programming / program-synthesis intuition:
a type-preserving subtree replacement stays runnable.

Claude sketched how a rich type universe would enable this:

**Types that encode stage and role:**
- Query (the original task)
- Advice / Plan (pre-response guidance)
- Draft (in-progress response, candidate for revision)
- Response (finalized)
- Critique (feedback on Draft or Response)
- Flag (structured subtype of Critique — location + label, no rationale)
- Score (numeric quality signal)
- Decision (verdict or selection)
- Transcript (accumulated interaction record)

**Combinators with these types:**
```
gen         :: Model -> Query -> Draft
genAdvised  :: Model -> Query -> Advice -> Draft
planFirst   :: Model -> Query -> Plan
decompose   :: Model -> Query -> [Query]
review      :: Model -> Draft -> Critique
flagOnly    :: Model -> Draft -> Flag
revise      :: Model -> Draft -> Critique -> Draft
finalize    :: Draft -> Response
select      :: [Draft] -> Draft
fuse        :: Model -> [Draft] -> Draft
vote        :: [(Draft, Score)] -> Draft
score       :: Model -> Draft -> Score
judge       :: Model -> Draft -> Decision
metaReview  :: Model -> [Critique] -> Critique
```

**Example mutations that are type-safe and genuinely structural:**

- Swap `review` for `flagOnly` (both produce Critique via Flag ⊂ Critique).
- Swap `vote` for `select (map fst ...)` (both produce Draft).
- Insert `metaReview` between per-model reviews and revision (type-preserves
  because metaReview takes [Critique] and produces Critique, which is
  what the downstream step already consumed).
- Replace `gen q` with `let a = planFirst m q in genAdvised m q a`
  (both produce Draft, downstream unaffected).
- Wrap `review` in a meta-layer: `\m d -> metaReview [review m1 d, ...]`
  (type-preserves if metaReview accepts [Critique]).

Each of these is a real structural change. None requires human design
of a new protocol shape from scratch. All are provably type-correct.

**ReConcile in this style:**
```
reconcile models rounds q =
  let initial   = parMap (gen q) models
      roundStep = \drafts ->
        parMap (\(m, d) ->
          let c = review m d
          in  revise m d c) (zip models drafts)
      refined   = iterateN rounds roundStep initial
      scored    = parMap (\(m, d) -> (d, score m d)) (zip models refined)
  in  vote scored
```


## What Claude tentatively recommends (but is uncertain about)

Start with a Python-implemented typed AST:
- Define `Expr[T]` as a generic class
- Each combinator constructs a subclass with the right type parameter
- Use dataclasses for AST nodes
- Mypy gives static type checking during development
- Runtime checks catch anything that slips through
- Mutations operate on AST nodes by type
- Execution is an interpreter that walks the tree and calls APIs

Scale: maybe 500 lines of Python for a first version. Can port to
Haskell later if we outgrow it, because the types would already be
worked out.


## Questions we've raised but not answered

1. **Nominal vs structural subtyping.** Is `Flag ⊂ Critique` enforced by
   declaration (nominal, like Haskell type classes) or by shape (tagged
   union, like Rust enums)? Claude leans nominal for cleanness, but
   nominal loses some flexibility.

2. **Extensibility of the type universe.** If we define 10 types now,
   does adding an 11th later require rewrites? Probably not, but
   depends on implementation choices we haven't made.

3. **Real Haskell vs Python typed AST.** We've set aside real Haskell
   because of runtime interop, but if we're doing typed ASTs seriously,
   Haskell's GADTs and the `Expr :: * -> *` pattern are genuinely
   better than anything Python offers. Is that worth reopening?

4. **How to handle context threading.** Protocols often involve
   accumulated context (transcripts, prior responses). In the typed
   AST, is context a parameter of primitives, a Reader-like
   environment, or an explicit State type? Different choices give
   different ergonomics.

5. **Granularity of combinators.** Is `review` one combinator, or is
   it parameterized over critique format (free-form vs flag vs
   structured)? If the former, the library grows; if the latter,
   types get more complex.

6. **Relationship to the prose inventory.** Does the rich typed DSL
   replace the inventory, coexist with it, or get generated from
   it / generate it? The inventory currently has protocols we
   wouldn't express cleanly in the typed AST (blackboard protocols,
   adaptive topology, some agentic patterns).

7. **Replication target question.** We agreed on a replication ladder
   (CCR → PoLL → ReConcile → ...). Does the typed AST approach let us
   express all of these? CCR is the simplest; if we can't express CCR
   cleanly, the approach has problems.


## What Codex is being asked

Open-ended. Give opinions, suggestions, concerns, alternative framings.

Particular questions we'd value input on:

- **The overall direction.** Is typed structural mutation the right
  ambition? Are we over-engineering? Is there a simpler approach that
  achieves the same practical goal (safe autoresearch over meaningful
  structural variations) that we're missing?

- **The type universe.** Is the stage/role-based type set (Query,
  Advice, Draft, Response, Critique, Flag, Score, Decision, Transcript)
  the right granularity? Too fine? Too coarse? Missing a type?

- **Haskell vs Python.** Given the typed-AST framing specifically —
  where types are doing real work and the whole point is that type
  correctness implies near-certain runnability — is there a stronger
  case for real Haskell than we gave it credit for? Or is Python
  typed AST adequate?

- **Relationship to the existing protocol-inventory.md.** Should the
  rich typed DSL replace, augment, or be generated from the current
  prose inventory?

- **The replication ladder under this approach.** Will CCR, PoLL, and
  ReConcile fit cleanly into the typed AST? Is there a problem we're
  not seeing?

- **Anything else we're missing.** We've been going back and forth for
  a while; an outside perspective that isn't following our conversation
  tree may spot things we've optimized away.
