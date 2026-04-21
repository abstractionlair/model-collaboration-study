# Framework-validation runs against HumanEval

This directory holds results from runs of `scripts/run_humaneval.py`.

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
