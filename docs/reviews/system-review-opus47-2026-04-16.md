# Review: Phase 1 system implementation

**Reviewer:** Claude Opus 4.7 (1M context), fresh-context independent reviewer
**Date:** 2026-04-16
**Artifact reviewed:** the system as of commit `16e1f78`, primarily
`src/ir/`, `src/executor/`, `src/experiment/`, `src/protocols/`, and
`scripts/smoke_test.py`. Checked against `docs/research/experimental-design.md`,
`docs/decisions.md`, and `docs/design/system-architecture.md`.

## Summary assessment

The system is a credible Phase-1-shaped scaffold. The IR is clean,
the layering between IR / executor / experiment-spec is real and not
just decorative, and the executor is small enough that the
selector-as-oracle discipline is auditable end-to-end (and is, in
fact, clean). The work is honest in its own self-criticism — most
of the load-bearing concerns are flagged in code comments before
they are flagged in this review. The two largest concerns are
**design-implementation divergences in conditions B/C and E that
look like silent reinterpretations of what the design specifies**,
and a **handful of implementation bugs and silent failure modes
that will degrade Phase 1 measurement quality if launched as-is**.

## Specific findings

Findings are grouped by severity. Numbering is continuous.

### Faithfulness to the locked design

**1. Conditions B and C use pointwise scoring; design specifies
comparative selection.** The design (Macro-Model Conditions, B and
C) describes the aggregation block as "chooses among the N
candidates." The implementation (`src/protocols/conditions.py:55-79`
and `:86-108`) uses `ParScore + WeightedVote`, which scores each
draft *independently in isolation* and then takes the argmax. The
judge never sees multiple candidates side-by-side. These are
materially different aggregation rules with different failure modes
— pointwise scoring lacks a comparative anchor, and at temperature 0
will tend to either cluster scores tightly or default to the
parser's 0.5 fallback (see #5 below), in either case collapsing
WeightedVote to "first draft wins by position" (see #6).

The author flagged this in the docstring of `condition_b` and
called comparative selection "a follow-on ablation on the
aggregation axis." That acknowledgment is honest, but the design is
silent about pointwise vs. comparative — there is no decision-log
entry, no design-doc paragraph saying "B and C are operationalized
as pointwise scoring," and no decision committing comparative
selection to a follow-on. Either the design should explicitly
adopt pointwise scoring as the operationalization (and acknowledge
the difference from "chooses among"), or the IR should grow a
comparative-selection node like `PickOne(model, drafts) ->
Answer[Draft]` that implements the design's wording faithfully.
Pick a path and write it down; this is currently a quiet
substitution.

**2. Condition E is structurally a third option the design
considered and rejected.** The design specifies `ParGen → reviewers
critique → meta-reviewer synthesizes the critiques and writes the
final response directly`, and explicitly contrasts this with the
"writers revise, then aggregate" alternative, choosing the former
because it is "cleaner (fewer moving parts, no implicit aggregation
rule)." The implementation
(`src/protocols/conditions.py:143-165`) is `ParGen → ReviseRound →
Fuse(meta over revised drafts)` — the meta-reviewer sees the
post-revision *drafts*, not the raw critiques. This is neither the
"meta does all the work" version nor the "writers revise then
aggregate" version: it is a third macro-model where writers
self-revise from their own critiques and the meta-reviewer
integrates the revised drafts. Compute cost is also higher than the
design's E (3N+1 calls instead of ~2N+1).

Probable reason: the IR has no node that lets `Fuse` consume both
drafts and critiques, so the design's stated E is not currently
expressible. The fix is one of (a) add `FuseWithCritiques(model,
drafts, critiques, query) -> Answer[Draft]` and rewrite
`condition_e` to match the design, (b) update the design to adopt
the implemented variant and note that the original E is the
follow-on, or (c) restructure as `ParGen → ParReview → Fuse(meta
over critiques + drafts)` once the IR supports it. As with #1, the
choice itself matters less than recording it; right now the
implementation differs from the design without a decision entry to
explain the change.

### Implementation bugs and silent failure modes

**3. `google.genai.errors.ClientError` covers *all* 4xx and is
treated as infrastructure failure.** In
`src/executor/api_client.py:87-90`, `_GOOGLE_INFRA` includes
`ClientError`. The Google SDK raises `ClientError` for every 4xx
status (verified by inspecting the SDK source: `if 400 <=
status_code < 500: raise ClientError(...)`). That includes 400 Bad
Request (malformed payload — usually a prompt-template bug), 401
Unauthorized, 403 Forbidden, 404 Not Found (model name typo).
These are not retryable failures and will burn the full retry
budget with exponential backoff before re-raising, while
incrementing `CallRecord.retries`. When the experiment runner is
eventually wired to "infra retries don't count toward the dollar
budget" (per the design's failure-handling policy), a malformed
prompt's 400s will mistakenly not count, biasing measurements.

Anthropic and OpenAI use specific exception types (`RateLimitError`,
`APITimeoutError`, `InternalServerError`, `APIConnectionError`)
which are precise. Google needs a custom predicate — inspect
`e.code` and treat only 408 / 429 / 5xx as infra-retryable.

**4. Score parser silently extracts the wrong number on common
output formats.** `_parse_score` in
`src/executor/interpreter.py:273-280` takes the *first* float in
the response and clips to `[0, 1]`. Verified behavior:

| Response                              | Parser output |
|---------------------------------------|---------------|
| `"Confidence: 0.85"`                  | `0.85` ✓     |
| `"0.7"`                               | `0.7` ✓      |
| `"I rate this 7 out of 10"`           | `1.0` ✗ (clipped from 7) |
| `"On a scale 1 to 10, this is 8"`     | `1.0` ✗ (clipped from 1) |
| `"I think this is pretty good"`       | `0.5` ✗ (silent fallback) |
| `"Score: 0.8 (high confidence)"`      | `0.8` ✓      |
| `"High"`                              | `0.5` ✗ (silent fallback) |

Two distinct bugs:
- "X out of 10" formats parse the first number, not the
  intended score.
- Non-numeric responses fall back to 0.5 with no telemetry,
  collapsing genuine signal into the median value.

The smoke test's score check rejects "7 out of 10" (because 7 ∉
[0,1]) but accepts "I think this is pretty good" (no float at all
fails the smoke check too) — so the smoke test catches the
overflow case but the parser still does the wrong thing on the
underflow case, and there is no parse-failure counter exposed
anywhere. Recommend (a) extracting the *last* float in [0,1] (or
using a regex anchored to a label), (b) raising or recording a
parse-failure event rather than defaulting to 0.5 silently.

**5. WeightedVote tie-breaking is positional and silent.** Verified
behavior: when all scores tie (or all fall back to 0.5 from #4),
`max(range(len(answers)), key=lambda i: scores[i].value)` returns
index 0, so draft 0 always wins. In Condition C with subject pool
`[gpt-5.4-mini, claude-haiku-4-5, gemini-2.5-flash]`, this would
systematically bias selection toward gpt-5.4-mini whenever
parsing/judging fails. The design has tie-breaking policy at the
condition-comparison level (dollars-per-solved-task) but is silent
on internal ties. Recommend either a pre-declared random
tie-breaking with a recorded seed, or a pre-declared model
preference order — and explicit telemetry whenever a tie occurs.

**6. Empty model responses propagate silently.** The OpenAI/xAI
adapters (`api_client.py:237`, `:263`) coerce `response.choices[0].
message.content or ""` to empty string. Google does the same with
`response.text or ""`. The design specifies that "zero-length
output... is treated as a capability failure" — but the executor
threads "" through to ParGen drafts, ParScore parses 0.5 from it,
and the protocol completes "successfully" with garbage. There is
no boundary in the executor that distinguishes a real response from
an empty response. The runner (when built) will need a hook;
flagging it now because the building blocks currently swallow this
distinction.

### Phase 1 readiness gaps

**7. `_best_model()` returns Haiku as a placeholder.**
`src/experiment/phase1.py:72-79`. The "conservative default"
rationale is reasonable in isolation, but the function silently
becomes the actual best-model choice for Conditions A, B, C
(judge), D' (pool), and E (meta-reviewer) anywhere
`build_phase1_conditions()` is called. If real calibration shows a
different model is best, every baseline and every comparison is
miscalibrated. The compute-matched constraint — load-bearing for
the entire research question — fails. Recommend either raising
`NotImplementedError("calibrate _best_model() before building
Phase 1 spec")` or making `best_model: str` an explicit required
argument to `build_phase1_spec`.

**8. `_n_samples_for_b()` is hand-picked at 1/3/6 with no cost
calibration.** Same file, lines 82-90. The comment ("at $X, one gen
+ one score ≈ 1.5× the cost of A") admits the math is rough. At
$X tier, B does 1 gen + 1 score = 2 calls vs. A's 1 call — likely
already over the $X cap before any token-level accounting. The
design specifies the tiers as caps, so violating them invalidates
the matched-budget comparison. Until calibration produces real
N-per-tier numbers, `_n_samples_for_b` should fail loudly when
called pre-calibration, same pattern as #7.

**9. `PHASE1_PRICING` is unverified and ungated.** Same file, lines
46-54. The design states "verify before kickoff" but nothing in
code blocks `build_phase1_spec()` from being called against stale
prices. Recommend either a `verified_date: str` field on
`PricingTable` with a max-age assertion, or making the
`PricingTable` a required constructor argument with no default.

**10. ParGen / Rounds / ParScore are sequential despite the "Par"
prefix.** `interpreter.py:215-227, 235-241, 243-253` are all
plain `for` loops. For smoke tests this is fine, but for a real
Phase 1 run the wallclock cost compounds: e.g., D at 3 subjects ×
1 round is 12 sequential API calls per task instance. The
architecture doc lists this as a Phase 1 metric ("throughput / items
per hour") and the IR's bundled Par-* nodes were designed
specifically so the executor could parallelize them. Recommend
async or threaded execution within Par-* steps before any real
benchmark run; flag now so the gap is tracked.

**11. `temperature=0` plus `seeds=5` will produce zero variance.**
`api_client.py:115` sets `temperature: float = 0.0` as default;
`spec.py:196` sets `seeds: int = 5`. With temp=0 and no other
source of randomness in the prompt, all five seeds will yield
nearly-identical outputs — Anthropic, OpenAI, and Google are all
near-deterministic at temp=0 with no seed parameter. The
"Variance across seeds" metric in the design becomes degenerate.
Either set a small temperature for gen calls (and record the
variance contribution honestly), or vary something explicit per
seed (a nonce in the prompt template). Currently the seeds field
is decorative.

### Honesty / scope correctness

**12. The smoke-test "PASS" verdict overclaims.** `smoke_test.py`
checks: (a) no exceptions, (b) response non-empty and contains
"def" or "fizzbuzz", (c) review responses contain at least one
evaluative word from a hand-picked list, (d) score responses
contain a parseable float in [0,1]. It does **not** check that
revise actually changed the draft, that Fuse actually synthesized
versus picked one verbatim, that the score parser extracted the
right number, or that the meta-reviewer's output materially
differs from any single input draft. The status.md claim
"Intermediate steps (review, revise, fuse) verified to attempt
what was asked" is too strong. A more honest scoping:
"Intermediate steps complete without exceptions and review
responses contain evaluative language; substantive verification of
revise/fuse semantics is not yet done."

This is small but worth correcting before the claim hardens into
project lore.

### Type system and process gaps

**13. No FakeClient unit tests exist.**
`docs/design/system-architecture.md:406-408` claims "The executor
has been smoke-tested end-to-end with a deterministic FakeClient
against CCR (3 calls), SA (3 calls), ReConcile (12 calls...) and
all six Phase 1 condition factories (A: 1 call, B(N=3): 6 calls,
C: 6 calls, D: 12 calls, D': 12 calls, E: 10 calls)." I cannot
find any test file that runs these — `find` returns only
`scripts/smoke_test.py`, and that script uses real APIs and
doesn't assert call counts. The behaviors that *should* be tested
with FakeClient — identity memoization in CCR (3 calls not 4),
ParGen/ParScore alignment, Rounds(N) call-count math, Fuse
visibility, WeightedVote selection rule, ContextMode and
Visibility prompt routing — are exactly the behaviors that will
silently regress under future refactors. This is a real gap;
either the doc is overclaiming or the tests existed in a
non-committed state and were lost.

**14. `mypy --strict` passes on the load-bearing 19 files but the
broader `src/` has 11 errors in `src/fetch_papers.py`.** Checking
`mypy --strict src/` (not just the four named subdirs) fails. The
status.md and architecture doc both phrase the strictness claim in
a way that is technically correct (the 19 IR/executor/experiment/
protocols files do pass) but a casual reader could assume "all of
`src/`." Worth a one-line clarification in status.md.

**15. `TracingClient.step_type` reverse-engineers prompt text to
classify calls.** `tracing.py:35-51` matches lowercased prompt
substrings ("write your own response and peer drafts" → fuse,
"confidence... 0.0-1.0" → score, etc.). The classifier is tightly
coupled to `DEFAULT_PROMPTS`. A custom `PromptTemplates` (which is
a Phase-1-IV — the critique-format ablation) will silently
misclassify steps, and the smoke test's intermediate-step checks
depend on this classification. Better to plumb step type through
the executor as explicit metadata, but that requires extending the
`ModelClient` protocol. At minimum, add a docstring warning that
the classifier assumes default prompts.

### Audits that came back clean

- **Selector-as-oracle discipline.** The executor never sees
  ground truth. `client.complete(model, system, user)` takes only
  prompt strings; no benchmark runner is yet built that could
  inject test-case oracles into a prompt. The default prompt
  templates have no oracle-shaped fields. The discipline holds in
  the current code; it will need to be re-audited at the
  benchmark-adapter boundary (when SWE-bench-style tasks are
  passed in, the adapter must not include hidden test cases in the
  query text).
- **Identity-based memoization.** Verified by tracing through CCR
  (`d` shared between review and revise) and ReConcile (`r` shared
  between WeightedVote and ParScore in the Let body). Cache is per-
  Interpreter, keyed on `id(expr)`, safe given the IR's
  immutability and the fresh `Var` names produced by `Let.make`.
- **`mypy --strict` on the load-bearing dirs.** Verified to pass
  on `src/ir`, `src/executor`, `src/experiment`, `src/protocols`
  (19 files). The `Any` pattern on `result_type` is intentional
  and isolated to the runtime-reflection layer; the lone
  `# type: ignore[misc]` in `Var.result_type` is the documented
  cost of shadowing a `ClassVar` with an instance field.
- **Anthropic and OpenAI infrastructure-error classification.**
  Both adapters use precise SDK exception types
  (`RateLimitError`, `APITimeoutError`, `APIConnectionError`,
  `InternalServerError`). Only the Google classification is loose
  (#3).

## Recommendation

**Revise and re-review.**

None of the findings call for architectural rework. The system
shape is right. But the bugs in #3, #4, #5 will degrade the
quality of Phase 1 measurements; the placeholders in #7, #8, #9
risk a Phase 1 launch with miscalibrated baselines that quietly
violates the load-bearing matched-budget constraint; and the
faithfulness gaps in #1 and #2 should be resolved by an explicit
design or implementation decision (entered in `decisions.md`)
rather than left as silent reinterpretations.

A reasonable next-round scope:

1. Decide and document #1 (B/C aggregation) and #2 (E
   composition). Either fix the code to match the design or update
   the design to match the code, with a `decisions.md` entry in
   either case.
2. Fix #3 (Google error classification), #4 (score parser), #5
   (tie-breaking), and #6 (empty-response handling). These are
   small, local changes.
3. Gate #7, #8, #9 against pre-calibration use — either
   `NotImplementedError` or required arguments.
4. Address #11 (temperature/seeds) and #12 (status.md scope
   correction) before the claims propagate.
5. Track #10 (real parallelism), #13 (FakeClient unit tests), #14
   (mypy scope clarification), and #15 (TracingClient coupling)
   as known follow-ups; they don't block the next review but
   should not be lost.

Then, in parallel with #6 above (the original next-up list in
status.md), invite Codex and Gemini to review against this
document. Same-family Opus review — even fresh-context — converges
on similar concerns to the prior Opus instance more than
different-lineage reviews would. Codex and Gemini are particularly
well-positioned to weigh in on #1 and #2 since they signed off on
the design wording in the fourth round.
