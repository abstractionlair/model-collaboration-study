# Model Collaboration Study

A pre-registered experiment asking: **at matched compute budget, when does a heterogeneous multi-model collaboration protocol outperform the best single model in the pool, and which structural properties drive the difference?**

The research question is committed in `docs/decisions.md` (2026-04-14) and the experimental design is promoted in `docs/research/experimental-design.md`. The compute-matched constraint is central: any multi-model result that does not beat a compute-matched single-model baseline is treated as a non-result. The study is pre-registered: the design, power analysis, and analysis plan were fixed before data collection.

## What this is

The project tests whether structured collaboration among language models—debate, peer review, revision, and fusion—can produce a *macro-model* that is more capable than any of its constituent models at the same dollar cost. A collaborative pipeline is treated as itself a model: a function from context to response built from smaller input models.

The Phase 1 experiment is restricted to **verifiable tasks with executable scoring** (passing tests, BFCL-style function-call correctness, accepted patches). No LLM-as-judge apparatus is used in Phase 1; that is deferred to Phase 2.

The experiment has **not yet run**. The current repository contains the implementation, calibration, and power analysis, but contains no experimental results.

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

### Typed protocol IR

Protocols are expressed as a typed Python AST in `src/ir/` with a surface authoring layer in `src/ir/surface.py`. Nodes include `Gen`, `Review`, `Revise`, `ParGen`, `SelfReviseRound`, `PeerReviseRound`, `ParPeerReview`, `FuseWithCritiques`, `WeightedVote`, `PickOne`, and `Let`. Stage tags (`Draft`, `Final`) and parameterized judgment types (`Critique[T]`, `Score[T]`) are enforced by `mypy --strict`.

The split between the abstract IR and the concrete experiment spec is documented in `docs/design/system-architecture.md`.

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
