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

1. Fourth editing pass on `experimental-design_draft.md` to adopt
   the macro-model framing: each condition is a fully-specified
   macro-model (context → response mapping) composed from typed
   IR building blocks. Selectors drop to "an aggregation building
   block that some macro-models contain." Also fold in Codex's
   remaining round-three points: pin each condition to a single
   concrete specification (no `or` branches), separate
   infrastructure failures from capability failures, clarify
   budget tiers as caps.
2. Build the experiment-spec layer — the piece between the IR and a
   real run. Prompts, model assignments, task slices, dollar budgets,
   metrics.
3. Express conditions A, B, C, D', E from the experimental design in
   `src/protocols/` as typed IR terms. ReConcile already covers D;
   none of A/B/C/D'/E need new IR primitives.
4. Wire a real `ModelClient` (Anthropic + OpenAI adapters) with
   retry/backoff/rate-limit handling.


## Currently routed to

`docs/research/experimental-design_draft.md` — fourth pass in
progress 2026-04-14. Adopting the macro-model framing: each
condition is a function from context to response, built from
typed IR building blocks. The building-block layer is shared
infrastructure for replicating papers and for future automated
search; individual macro-models are the experimental units.


## Blockers

None.
