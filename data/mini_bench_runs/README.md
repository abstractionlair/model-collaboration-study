# Framework-validation runs

This directory holds results from runs of
`scripts/run_humaneval.py` and `scripts/run_bfcl.py`.

**These are NOT research results.** HumanEval is heavily
contaminated in training data; it is used here only to
validate that the framework works end-to-end. The Phase 1
matrix runs against SWE-bench Verified / LiveCodeBench / BFCL
per `docs/research/experimental-design.md`; HumanEval
deliberately stays out of it.

Each run writes a JSON file named
`humaneval-<ISO-timestamp>.json` with the full per-task
breakdown (tokens, dollars, telemetry, timing, aborted flag).

## 2026-04-21 — first framework-validation run

First end-to-end run of the framework against a real
benchmark. Goals were (a) exercise every Phase 1 IR node
family on real model output, (b) confirm every provider
completes calls under the new stack, (c) shake out bugs the
FakeClient-based unit tests couldn't catch.

**Configuration.**
- 10 HumanEval tasks (`HumanEval/0` through `HumanEval/9`).
- Available providers: anthropic, openai, xai (no Google
  generative API key available in the current vault).
- Subject models: `gpt-5.4-mini`, `claude-haiku-4-5` (Gemini
  Flash skipped due to missing key).
- Temperature: vendor defaults (`ApiClient.temperature=None`).
- Seed: 0.

**Results.**

| Condition | Pass | Aborts | Dollars | Calls | Avg elapsed |
|-----------|------|--------|---------|-------|-------------|
| A (gpt-5.4-mini) | 10/10 | 0 | $0.0079 | 10 | 1.2s |
| A (claude-haiku-4-5) | 10/10 | 0 | $0.0106 | 10 | 1.7s |
| D (gpt-mini + haiku, 1 round) | 10/10 | 0 | $0.0982 | 80 | 15.1s |
| E (gpt-mini + haiku, meta=gpt-mini) | 10/10 | 0 | $0.0798 | 50 | 13.7s |

**Total:** ~5.3 minutes wallclock, ~$0.20 USD. Call counts
match the architecture doc's predictions (A: 1/task; D at
N=2, 1 round: 2 gen + 2 review + 2 revise + 2 score = 8/task;
E at N=2, 1 meta: 2 gen + 2 review + 1 fuse = 5/task).

**Telemetry.** One `weighted_vote_ties` event in Condition D
across 10 tasks; seeded-random tie-break resolved it as
designed. No parse failures, no infra failures, no capability
failures.

**Bug surfaced and fixed during the run.** OpenAI's GPT-5
family rejects `max_tokens` as "unsupported parameter; use
`max_completion_tokens` instead." First two attempts on
Condition A with `gpt-5.4-mini` aborted with 400 Bad Request;
switched `_call_openai` to use `max_completion_tokens`,
re-ran, all ten passed. xAI adapter still uses `max_tokens`
because current Grok models accept it; revisit if/when they
break.

**What this validates.**
- All four IR aggregation nodes (`Gen`, `PeerReviseRound` via
  `reconcile`, `ParPeerReview`, `FuseWithCritiques`) run
  end-to-end on real model responses.
- Cyclic 1-peer assignment produces coherent peer reviews on
  real inputs; revisions actually converge on correct code.
- `FuseWithCritiques` produces a workable synthesis from
  drafts + aligned critiques.
- Temperature-as-None (vendor default) does not trigger the
  round-2 homogeneous mode-collapse Gemini flagged — the
  models produce usable outputs without explicit stochasticity
  pinning.
- Per-task cost attribution via `client.calls` slicing works.
- Runner correctly surfaces telemetry (the one tie was
  recorded).
- OpenAI + Anthropic adapters are production-viable after the
  `max_completion_tokens` fix.

**What this does NOT validate.**
- Google Gemini adapter (no API key in vault).
- Any condition at scale (10 tasks is plumbing-check size).
- Any performance differentiation between conditions —
  HumanEval is too easy (ceiling at ~100% for these models),
  so D and E don't have headroom to demonstrate
  collaboration-over-solo effects.
- Calibration-time cost modeling (`base_cost_x` not yet set).

**Next up.** Phase 1 benchmark adapters (SWE-bench Verified /
LiveCodeBench / BFCL) use the same `Benchmark` abstraction;
the runner is ready to drive them once the adapters land.

## 2026-04-21 — BFCL framework-validation run

First validation of the `Benchmark` abstraction on a
non-coding task shape. BFCL `simple_python` category: one
declared tool, one expected call, AST-matched against the
published `possible_answer` set. Proves the adapter
abstraction holds beyond code-shaped tasks (HumanEval) — in
particular that the query-formatting / response-parsing /
executable-scoring triangle works for structured-output
benchmarks too.

**Configuration.**
- 3 BFCL tasks (`simple_python_0` through `simple_python_2`).
- Available providers: anthropic, openai, google (all three
  subject-model providers live).
- Subject models: `gpt-5.4-mini`, `claude-haiku-4-5`,
  `gemini-2.5-flash`.
- Temperature: vendor defaults.
- Seed: 0.

**Results.**

| Condition | Pass | Aborts | Dollars | Calls |
|-----------|------|--------|---------|-------|
| A (gpt-5.4-mini) | 3/3 | 0 | $0.001 | 3 |
| A (claude-haiku-4-5) | 3/3 | 0 | $0.002 | 3 |
| A (gemini-2.5-flash) | 3/3 | 0 | $0.001 | 3 |
| D (all three, 1 round) | 3/3 | 0 | $0.024 | 36 |
| E (all three, meta=gpt-mini) | 3/3 | 0 | $0.023 | 21 |

**Total:** ~2.9 minutes wallclock, ~$0.05 USD, 66 API calls.

**Telemetry.** No parse failures, no ties, no infra failures,
no capability failures. All five conditions scored 100% —
expected, because `simple_python` is deliberately easy (the
benchmark purpose is calibration, not capability
differentiation).

**What this validates.**
- `BFCLBench` loads + subsets correctly against the real
  Gorilla `main` snapshot (400 tasks in the file).
- Query formatting (user prompt + tool JSON schema + output
  instructions) elicits conforming JSON from all three
  subject-model families.
- JSON extraction handles the shapes models actually emit —
  fenced ```json blocks, occasional prose before/after, extra
  keys beyond name/arguments.
- AST-based scoring (function-name + per-param type and value
  match against accepted-values list) produces
  consistent-with-upstream verdicts on real inputs.
- The `Benchmark` abstraction composes cleanly with D and E
  protocols — peer-review critique + meta-synthesis produce
  valid JSON-structured output when the final-pass model is
  asked to emit JSON. (This was the non-obvious integration
  risk: does a multi-round protocol preserve the output
  format discipline? Yes, for these models on this task.)

**What this does NOT validate.**
- Harder BFCL categories (multiple, parallel, live_*) — future
  adapter work.
- Any performance differentiation between conditions — all
  three subject models solve simple_python one-shot, so the
  multi-round conditions have no headroom.
- Scoring semantics beyond the happy path at scale — unit
  tests cover failure modes (wrong name, missing required,
  type mismatch, string normalisation), but we haven't yet
  seen real models produce interesting failures here.

## 2026-04-21 — BFCL widen-categories validation

Four new BFCL categories exercised end-to-end after extending
`BFCLBench` beyond `simple_python`: `multiple`, `parallel`,
`parallel_multiple`, `live_simple`. Goal was pipeline coverage,
not statistical differentiation — confirming the multi-call
extractor path, the no-order matcher, and the multi-tool query
templates all compose with Condition A (and, for `parallel`,
with D and E).

**Configuration.**
- Same subject-model pool as above (`gpt-5.4-mini`,
  `claude-haiku-4-5`, `gemini-2.5-flash`).
- Temperature: vendor defaults. Seed: 0.

**Condition A per category.**

| Category | Tasks | A-pass (combined) | $ |
|-----------|-------|-------------------|---|
| multiple | 3 | 9/9 | $0.005 |
| parallel | 3 | 9/9 | $0.005 |
| parallel_multiple | 10 | 30/30 | $0.021 |
| live_simple | 10 | 30/30 | $0.012 |

**Condition A + D + E on `parallel` (3 tasks).**

| Condition | Pass | $ |
|-----------|------|---|
| A (gpt-5.4-mini) | 3/3 | $0.002 |
| A (claude-haiku-4-5) | 3/3 | $0.003 |
| A (gemini-2.5-flash) | 3/3 | $0.001 |
| D (all three, 1 round) | 2/3 | $0.039 |
| E (all three, meta=gpt-mini) | 3/3 | $0.033 |

**What's notable.** Condition A hits 100% on every category at
these small N's, including the hardest one (`parallel_multiple`
at N=10). **This is direct empirical confirmation of Gemini's
round-5 finding:** frontier models one-shot BFCL so reliably that
the tool-use stratum has no headroom for collaborative protocols
to demonstrate capability lift at small N. Phase 1 kickoff needs
either larger N (power analysis item) or a harder within-BFCL
subset (e.g. the high-index `parallel_multiple` tasks, or
`live_parallel_multiple` once added) or both.

**One surprise.** D was 2/3 on `parallel`. The lone failure was
`parallel_2::calculate_resistance`. The schema declares
`resistivity` as a string enum (`'copper'` / `'aluminum'`). All
three A runs passed this task individually, each emitting the
string label. D's final revision emitted `resistivity: 2.82e-08`
— aluminum's real-world physics constant in ohm-meters. The
scorer correctly rejected it as wrong-type per upstream
semantics. The per-round trace isn't saved in the run log, so
the exact drift story is inferred: most plausibly, a peer
critique during D's revision cycle argued "use the actual
physical value, not just the label," and the final aggregated
answer locked that in — a plausible-sounding critique pushing
three initially-correct answers away from correct. Not a scorer
bug, not a system error — a genuine collaborative-output failure
where peer review inverted the collaboration-lifts-capability
hypothesis. n=1 on a small validation; could be fluke or the
first sign of a systematic pattern worth naming. Worth a
tracing-enabled re-run before treating as a phenomenon.

**What this validates.**
- Multi-call JSON extraction path works on real model output.
- No-order matching correctly pairs model calls to GT items
  irrespective of emission order (swap test: some real responses
  emitted calls in reverse of the question order; all scored
  correctly).
- Multi-tool query templates elicit the right tool-picking
  behavior from all three subject model families (no
  hallucinated tool names in 39 attempts across `multiple` and
  `parallel_multiple`).
- `live_simple` (real-user queries with more varied phrasing
  than curated `simple_python`) still has the 100% ceiling at
  N=10 — the distribution shift alone doesn't break it.
- D and E conditions compose with multi-call output: peer review
  and meta-fusion can produce valid JSON arrays, not just single
  JSON objects.

**What this does NOT validate.**
- Whether the 100% ceiling holds at Phase 1's operational N or
  breaks — that's the power-analysis question.
- `live_multiple` / `live_parallel` / `live_parallel_multiple` /
  `multi_turn_*` — not ported in this session.
