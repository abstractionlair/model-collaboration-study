# BFCL adapter review — Gemini 3.1 Pro

**Reviewer:** Gemini 3.1 Pro (preview), MCP session
`mcs-bfcl-review-gemini`, session
`835aebea-a9cb-4ac1-84bf-c854cef119ee`.

**Subject:** `src/experiment/benchmarks/bfcl.py` and surrounding
files at commit `2860c2d`.

**Verdict:** Proceed.


## Full review text

> The port of the AST scorer is rigorously faithful. Using
> `type(value) is expected` correctly handles Python's
> `bool`/`int` subclass overlap, mirroring BFCL's strict type
> checks exactly. The string normalisation (stripping
> punctuation, lowercasing) and type auto-promotion logic match
> upstream semantics. Skipping the `is_variable` branch is the
> right call here since the query template forces models to
> emit concrete JSON rather than symbolic AST references,
> making variable resolution irrelevant.
>
> There are a couple of edge cases the tests don't cover.
> First, the JSON extractor grabs the first block that
> successfully parses as a tool call. If a model's
> chain-of-thought includes a hypothetical JSON block before
> its actual answer (e.g., reciting the schema to plan its
> response), the extractor will evaluate the thought block and
> likely fail. You might want to evaluate the last valid block
> instead, or rely on prompt templates to enforce strict
> extraction tags. Second, `_value_matches_dict` normalises
> dictionary values but leaves dictionary keys un-normalised.
> If upstream BFCL normalises keys, you might inadvertently
> reject valid variations here, though this is rare in the
> simple category.
>
> The `Benchmark` protocol is a clean boundary but has two
> structural implications for the upcoming adapters. First,
> `score` is synchronous. That is fine for AST matching, but
> SWE-bench requires spinning up Docker containers and
> executing test suites. A synchronous call will block the
> runner thread for minutes per task, meaning the runner will
> need a thread pool to avoid massive wall-clock times. Second,
> exposing only `query_text` in the `Task` object locks us into
> prompted text-to-JSON generation. If Phase 1 meant to
> evaluate native vendor tool-calling APIs, the interface would
> need to expose the tool schema separately. Assuming prompted
> JSON is the intended Phase 1 constraint, the shape is
> correct.
>
> Using only the `simple_python` category for the Phase 1 run
> is a major statistical risk. As your validation run
> demonstrated, frontier models one-shot these tasks
> effortlessly. If the single-model baseline scores 100%, the
> multi-round conditions have zero headroom to demonstrate
> collaboration benefits. A 100% ceiling guarantees a null
> result for the tool-use stratum, automatically triggering the
> pre-declared utility curve fallback. You will need to land
> the multiple and parallel category scorers before the actual
> Phase 1 kickoff to push the baseline error rate down to a
> measurable range.
>
> The 15/15 validation result means the task is trivially
> easy, not that the scorer is too permissive. The AST checks
> are appropriately strict. The high pass rate is partially
> due to the robust JSON extractor, which rightly forgives
> stringified arguments and extra keys like "reasoning". This
> is exactly what we want: measuring semantic tool-use
> capability rather than formatting pedantry. The validation
> proves the abstraction holds perfectly; the difficulty
> ceiling is a test-matrix problem, not an architectural one.
>
> Recommendation: **Proceed**.


## How findings were handled

1. **Scorer faithfulness** — Gemini signed off; no changes.
2. **First-vs-last JSON block extraction** — non-blocking
   observation; not addressed. If real Phase 1 traces show
   chain-of-thought JSON poisoning, revisit.
3. **Dict key normalisation** — Gemini speculated "if upstream
   BFCL normalises keys"; confirmed it does not (upstream's
   `dict_checker` uses plain `in` on keys). No change needed;
   our port matches upstream.
4. **Sync `score()`** — flagged as forward concern for
   SWE-bench. Tracked as future work; not a BFCL-adapter
   blocker.
5. **No `tool_schema` field on Task** — intentional for
   prompted-JSON approach. Tracked; would require revisiting
   if Phase 1 were to evaluate native tool-calling.
6. **100%-ceiling statistical risk** — **primary strategic
   finding.** Tracked in `status.md`; widening BFCL categories
   (multiple / parallel / live_*) is explicitly named as
   pre-kickoff work before Phase 1.
