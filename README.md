# Model Collaboration Study

## Background and Motivation

[Elsewhere](https://github.com/abstractionlair/review-diversity) I describe my usage of multiple models in software development. Separating writing and reviewing of artifacts, sometimes having multiple models review the same artifact or write tests, and seeing if the diversity of the models, i.e. different families, improves results. At the time I'm writing this I haven't done the careful evaluation of this, but from my informal experience, it has been helping. This made me wonder more generally what improvement, if any, we can gain by having multiple models collaborate. And, importantly, at the same cost. This project is an attempt to measure this properly.

There is no limit to the number of ways we could attempt to get models to collaborate and I wanted to be able to test many of them, not just a small pre-chosen set.
So I decided to create a DSL for representing different variations. Initially I'm using it to test some already known protocols.
If it works _really_ well I can imagine hill-climbing in the space of collaborative structures, with some kind of constraint(s) to avoid bloat.
(Who wants a one million line structure description or one million calls to each of two models followed by a search for the best answer.)
(Replace "one million" by whatever corresponds to insanely too big in whatever circumstances you find yourself in.)

Developed with a lot of help from Claude (and reviews along the way from other models). And the description of the details below is also mostly written by Claude.

## Updates

### 2026-07-24

Kicked off yesterday. I expected to just be able to have a note about that today with a description of the still-pending steps. But I think
the results will be in tonight. Mostly negative, but some interesting data and good indications of how to follow-up with improvements.


## Introduction

A pre-registered experiment asking: **at matched compute budget, when does a heterogeneous multi-model collaboration protocol outperform the best single model in the pool, and which structural properties drive the difference?**

The research question is committed in `docs/decisions.md` (2026-04-14) and the experimental design is promoted in `docs/research/experimental-design.md`. The compute-matched constraint is central: any multi-model result that does not beat a compute-matched single-model baseline is treated as a non-result. The Phase 1 design and its analysis plan were pre-registered before any data collection. Following the descriptive pilot (see *Pilot results* below), the confirmatory analysis plan is being re-registered for the adopted fractional scoring before the confirmatory run.

## What this is

The project tests whether structured collaboration among language models—debate, peer review, revision, and fusion—can produce a *macro-model* that is more capable than any of its constituent models at the same dollar cost. A collaborative pipeline is treated as itself a model: a function from context to response built from smaller input models.

The Phase 1 experiment is restricted to **verifiable tasks with executable scoring** (passing tests, BFCL-style function-call correctness, accepted patches). No LLM-as-judge apparatus is used in Phase 1; that is deferred to Phase 2.

The pre-registered confirmatory experiment has **not yet run**. A descriptive pilot of the full condition matrix completed 2026-07-24 — see *Current status → Pilot results* below; the repository contains the implementation, calibration, power analysis, and the pilot's data and findings.

## A typed language for collaboration protocols

The piece of this repository with the longest expected life is
not any single experiment: it is the **typed language for
model-collaboration protocols** in `src/ir/`, and the executor
that runs it. It has the classic two-layer shape: a small
**embedded DSL** for authoring (`surface.py` — what humans
write), which builds a **typed intermediate representation**
(IR, in the compiler sense — what tools manipulate). The
distinction matters: most agent-orchestration DSLs have no
manipulable typed substrate underneath, and the IR layer is
where this project's longer-term ambitions live. The premise: a
collaboration protocol — who drafts, who critiques, who revises,
how a final answer is committed — is a *program*, and it should
be written in a language whose type system catches malformed
protocols before any API dollar is spent.

- **Typed AST.** Protocols compose from nodes like `Gen`,
  `ParGen`, `Review`, `Revise`, `PeerReviseRound`,
  `ParPeerReview`, `FuseWithCritiques`, `WeightedVote`,
  `PickOne`, and `Let`, with phantom stage tags (`Draft`,
  `Final`) and parameterized judgment types (`Critique[T]`,
  `Score[T]`) enforced under `mypy --strict`. A pipeline that
  aggregates unscored drafts, or finalizes a critique, fails to
  type-check rather than failing at runtime.
- **Measurement policy lives in the AST.** Decisions that can
  silently shape results — tie-breaking, parse-failure recovery —
  are node-level fields (`TieBreakPolicy`, `ParseFailurePolicy`),
  not interpreter accidents. This principle was applied twice
  after independent model reviews caught executor-level fallbacks
  affecting measurement (`docs/decisions.md`, 2026-04-19 and
  2026-07-23).
- **Structural invariants by construction.** The executable
  evaluator can never act as a protocol's aggregation step
  (avoiding Pass@N contamination); participant identities are
  blinded in every critique; every internal call — generation,
  critique, revision, judging — is billed to the protocol's
  dollar budget.
- **A small surface layer** (`src/ir/surface.py`) keeps protocols
  readable: each of the six experimental conditions in
  `src/protocols/conditions.py` is a few lines. Published
  protocols (ReConcile; cross-context review) are already
  expressed in the same vocabulary, and
  `docs/research/protocol-inventory.md` catalogs 37+ protocol
  variants across 19 structural variables as the target space.
- **The executor** (`src/executor/`) is a minimal tree-walking
  interpreter over an injected `ModelClient`: a `FakeClient`
  makes the whole protocol layer hermetically testable (165 unit
  tests, no network), a `TracingClient` captures full
  request/response traces, and the real `ApiClient` speaks to
  four providers with retry classification, per-call cost
  accounting, and truncation/finish-reason telemetry.
- **Looking ahead**, the IR carries runtime type reification
  specifically so that *automated structural search* over
  protocol space — type-preserving mutation of protocol subtrees
  — is possible later, and macro-models compose recursively
  (a pool member can itself be a protocol subgraph; see
  `docs/backlog.md`). A reference Haskell implementation
  (`src/ir_haskell/`) documents the type discipline in a language
  built for it.

The IR and executor have now been exercised by eight independent
model reviews across two rounds and by a 688-execution pilot run;
the architecture write-up is `docs/design/system-architecture.md`.

## Design

### Collaboration structures under test

Phase 1 compares six macro-model conditions, each pinned to a single IR specification:

- **A.** Single-model, one pass (`Gen`).
- **B.** Single-model repeat-and-aggregate (`ParGen + PickOne`).
- **C.** Heterogeneous parallel generation + peer-LLM aggregation (`ParGen + PickOne`).
- **D.** Heterogeneous ReConcile-style peer review and revise (`ParGen + PeerRounds + WeightedVote`).
- **D'.** Homogeneous ReConcile-style, matching D exactly except the pool is one repeated model.
- **E.** Hierarchical synthesis (`ParGen + ParPeerReview + FuseWithCritiques`).

The D → D' comparison is the cleanest heterogeneity control. A → B isolates inference-time compute scaling within a single model. See `docs/research/experimental-design.md` § Macro-Model Conditions for the full specification.

### Protocol expression

All six conditions are typed IR programs (see *A typed language
for collaboration protocols* above); the split between the
abstract IR and
the concrete experiment-spec layer is documented in
`docs/design/system-architecture.md`.

### Scoring and budget matching

Final scoring is executable: tests pass, tool calls match reference schemas, or patches pass the test harness. The evaluator is never used as the macro-model's aggregation step; each macro-model must commit to a single response before scoring.

Budget tiers are denominated in dollars: $X, $2X, $4X, with $X anchored to the cost of Condition A on the best single subject model. All internal model calls (generation, critique, revision, aggregation, meta-synthesis) count toward the budget. Infrastructure failures are retried off-budget.

### Current status (July 2026)

The design phase is complete. The typed IR, executor, real API client, experiment-spec layer, and Phase 1 condition factories are implemented. Four rounds of cross-lineage system review concluded in April 2026 with a recommendation to proceed.

The July 2026 kickoff decisions (`docs/decisions.md`, 2026-07-04) resolved four blockers:

- LiveCodeBench pool will expand to reach a usable middle-difficulty sample size.
- BFCL is dropped from Phase 1; the uniform middle-band fallback is adopted phase-wide.
- LiveCodeBench scoring will use mean fraction of test cases passed.
- The Gemini subject is updated to `gemini-3-flash` (replacing `gemini-2.5-flash`), requiring a recalibration run.

Remaining pre-kickoff work: SWE-bench Verified adapter, run-manifest schema, and the expanded LiveCodeBench data pull.

### Pilot results (2026-07-24) — automated interim update

> *This section was written by Claude (the project's implementation
> assistant) as a quick, facts-only record that pilot results exist.
> A fuller write-up by Scott, with interpretation and context, is in
> progress. Every claim below is taken from
> `docs/research/pilot-findings.md` (rev. 2), whose contents were
> audited against the raw data by four independent frontier models
> (`docs/reviews/synthesis-round8-2026-07-24.md`).*

A pilot of the full Phase 1 condition matrix ran 2026-07-23/24:
all six macro-model conditions (A×3 subjects, B, C, D, D′, E) on
the LiveCodeBench test6 medium+hard pool, N=86 tasks, single
seed, executable scoring, $62.00 total API spend. It is a
descriptive machinery-validation run, not the pre-registered
test (N is ~5× too small, and the pool turned out not to be
middle-band — see below).

**Instrument events during the run.** A harness bug was found
and fixed mid-pilot: Gemini's thinking tokens count against
`max_output_tokens`, so at the original shared 4096-token cap
its answers were silently truncated and scored ~0, and thinking
tokens went unbilled. This invalidated the April 2026
calibration (which had concluded Gemini-class models were
unusable on this benchmark) and, combined with the
2.5-flash → 3-flash model swap, flipped the best-subject
ranking: `gemini-3-flash-preview` scores 0.797 mean-fraction on
this pool vs. ~0.53–0.55 for the other two subjects. Gemini
remained budget-bounded at 32,768 tokens for the whole run, and
that bound binds on roughly 30% of its hard-task calls. Two
review rounds ran alongside: four current-generation models
(Claude Fable 5 fresh-context, GPT-5.6 Sol, Grok 4.5, Kimi K3)
audited the plan and code (round 7), and later the conclusions
against the raw data (round 8). All eight reviews and both
syntheses are in `docs/reviews/`.

**Results** (mean-fraction / strict pass / $ per task):

| Condition | mean_frac | strict | $/task |
|---|---|---|---|
| A gemini-3-flash-preview | 0.797 | 0.70 | $0.077 |
| A claude-haiku-4-5 | 0.545 | 0.22 | $0.008 |
| A gpt-5.4-mini | 0.529 | 0.26 | $0.004 |
| B (gpt ×8 + pick) | 0.617 | 0.40 | $0.036 |
| C (3 drafts + pick) | 0.605 | 0.38 | $0.091 |
| D (heterogeneous ReConcile) | 0.816 | 0.69 | $0.301 |
| D′ (homogeneous ReConcile) | 0.588 | 0.35 | $0.039 |
| E (hierarchical synthesis) | 0.638 | 0.43 | $0.166 |

**Review-audited findings, stated at the strength the data
supports:**

- No collaboration condition demonstrated a win over the best
  single model. C and E score significantly below it while
  costing 1.2×/2.2× more. D is statistically indistinguishable
  from it (+0.019, 95% CI [−0.068, +0.109]) while spending
  3.9× — and no compute-matched single-model comparator at D's
  budget was run, so that comparison is unresolved rather than
  negative.
- D's apparent parity is concentrated entirely in the 26 tasks
  where Gemini's single attempt was cut by the 32k output
  budget (D−gemini = +0.228 there, −0.072 on the other 60
  tasks). On tasks where the best model was not cap-limited,
  the per-task best-of-pool exceeds the best model by +0.0004
  mean-fraction — the pool contains essentially no
  complementarity for selection to recover.
- C's task-visible judge selected at the 27th percentile of a
  random-pick baseline — at or below chance.
- B (8 samples + same-model pick) gained +0.094 over its own
  base model (nominal significance only; it does not survive
  multiplicity correction on the primary metric) and is the
  only condition that beats the best single model on dollars
  per solved task ($0.091 vs $0.110).
- An ex-post oracle router (cheapest model matching the best
  model's per-task score) reaches equivalent quality at 49% of
  the best model's cost — an upper bound; no deployable router
  was tested.

**Caveats carried by all of the above:** single seed and a
single generation sample per task at vendor-default
temperature; N=86 on one benchmark; the pool sits above the
design's pre-registered difficulty bands for the actual best
subject; budget-tier caps were not enforced; candidate
execution is not yet sandboxed. Raw data:
`data/mini_bench_runs/pilot-lcb-2026-07-24T20-46-16.json`.

## Repository layout

```
docs/
  research/           # Pre-registered experimental design, power analysis, protocol inventory
  design/             # System architecture (IR / executor / spec-layer split)
  decisions.md         # Decision log with rationale
  status.md            # Volatile current state
src/
  ir/                 # Typed protocol IR (core + surface authoring layer)
  protocols/          # CCR, ReConcile, and Phase 1 condition factories A–E
  executor/           # Tree-walking interpreter, real API client, FakeClient
  experiment/         # Spec layer, prompts, runner, benchmark adapters
analysis/             # Power analysis script and results
tests/                # 155 unit tests (no API keys required)
scripts/              # Drivers for HumanEval, BFCL, LiveCodeBench, calibration, smoke tests
```

## Running the tests

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Run the full suite:

```bash
.venv/bin/python -m pytest tests/
```

As of 2026-07-05, the suite reports **155 passed** with no API keys required. The tests cover the interpreter, parsers, IR, API-client behavior, and all benchmark adapters using mocked or hand-authored data.

## Notes

- API keys are not required for the test suite. They are only needed for the driver scripts (`scripts/run_*.py`, `scripts/smoke_test.py`), which read the standard provider API-key environment variables.
- BFCL is implemented as a benchmark adapter but is no longer in the Phase 1 matrix after the July 2026 decision. It remains useful for framework validation and follow-on work.

## Provenance

The research question — can a collaborative process involving multiple models reliably beat any single model at matched compute? — is mine, as are the methodological moves I consider load-bearing: the weaker-subjects/frontier-judges tiering, the compute-matched comparison constraint, the protocol notation the IR grew out of, and the reframe of collaboration protocols as typed structural mutations over runnable protocol graphs. Those were developed in long model conversations that I led. The build-out of the formal notation, the power and calibration derivations, and all of the code are model-written under my direction; my engagement is at the architecture level rather than line by line, and that level of review catches real things — a tie-break-policy design flaw got past every reviewer model before I flagged it. The alignment/oversight framing was a model's suggestion, and the credit for it belongs there. What makes the delegation defensible here is the machinery around it: a pre-registered design, a typed IR under `mypy --strict`, 155 tests that run without API keys, and four rounds of cross-lineage review before the decision to proceed.
