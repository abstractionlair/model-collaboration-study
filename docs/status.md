# Project Status

**Last updated:** 2026-04-16

The volatile top of the stack. Read at session start to know what's
happening and what to do next. Write at *task start*, not task end:
before starting any substantive unit of work, update the "Next up"
list to reflect what you're about to do.

For durable state, see `docs/design/system-architecture.md` and
`docs/decisions.md`. For ideas not currently being worked on, see
`docs/backlog.md`.


## Phase

Design phase **complete**. Experimental design promoted from draft
to `docs/research/experimental-design.md` on 2026-04-14 after four
rounds of Codex and Gemini review (both signed off). Phase 1 is
scoped to executable scoring only, compute is denominated in
dollars (as caps), the condition matrix is A/B/C/D/D'/E framed as
macro-models composed from typed IR building blocks, and the
statistical plan pre-registers a Protocol × Stratum interaction
test with an automatic fallback to the middle band if power is
thin. System infrastructure (typed IR, executor) already exists
from the parallel track. Next: experiment-spec layer and real
`ModelClient` adapters.


## Next up

1. ~~Build the experiment-spec layer.~~ Done — `src/experiment/`.
2. ~~Express macro-models A–E.~~ Done. All 12 condition-tier pairs
   build, type-check, and run through the executor. `Fuse` node
   added to the IR for Condition E.
3. Wire a real `ModelClient` (Anthropic + OpenAI adapters) with
   retry/backoff/rate-limit handling. Infrastructure failures must
   be separated from capability failures per the design doc.
4. Integrate `PromptTemplates` from the spec layer into the
   executor (replace hardcoded placeholder strings).
5. Pre-kickoff: run the power analysis gate that the experimental
   design specifies, to decide whether the full three-stratum
   interaction test is feasible or the middle-band-only fallback
   applies.


## Currently routed to

`src/experiment/spec.py` — building the experiment-spec layer
(Layer 3). Expressing Phase 1 macro-model conditions A–E in the
IR and wiring them into a concrete experiment spec.


## Blockers

None.
