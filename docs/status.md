# Project Status

**Last updated:** 2026-04-14

The volatile top of the stack. Read at session start to know what's
happening and what to do next. Write at *task start*, not task end:
before starting any substantive unit of work, update the "Next up"
list to reflect what you're about to do.

For durable state, see `docs/design/system-architecture.md` and
`docs/decisions.md`. For ideas not currently being worked on, see
`docs/backlog.md`.


## Phase

Inspiration → Question transition, with system infrastructure being
built in parallel. Typed IR, surface authoring layer, and minimal
executor all exist; CCR and ReConcile run end-to-end against a
deterministic fake client. Formal research question committed
(capability-first, compute-matched). `experimental-design_draft.md`
currently under revision based on preliminary Codex/Gemini feedback:
Phase 1 narrowed to executable-scoring only (walk-before-run), dollar-
denominated compute, D' homogeneous-protocol control added, Variable
K (identity blinding) locked, condition B selector held constant.
Second-pass multi-model review will follow the edit.


## Next up

1. Edit `experimental-design_draft.md` to reflect the Phase 1 scope
   narrowing and matrix restructuring; send revised draft back to
   Codex and Gemini for second-pass review.
2. Build the experiment-spec layer — the piece between the IR and a
   real run. Prompts, model assignments, task slices, dollar budgets,
   metrics.
3. Express conditions A, B, C, D', E from the experimental design in
   `src/protocols/`. ReConcile already covers D; none of A/B/C/D'/E
   need new IR primitives.
4. Wire a real `ModelClient` (Anthropic + OpenAI adapters) with
   retry/backoff/rate-limit handling.


## Currently routed to

`docs/research/experimental-design_draft.md` — under revision
2026-04-14 (second pass), narrowing Phase 1 to executable-scoring
only and restructuring the condition matrix.


## Blockers

None.
