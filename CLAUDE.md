# Model Collaboration Study

## Motivating Question

"Can we systematically and reliably enable more capabilities in a
collaborative process involving multiple models than any of the
models exhibit themselves?"

The framing that decides which literature is relevant and which
protocol families are interesting. Capability-enhancement-first;
alignment / oversight applications are a secondary downstream
payoff (particularly the scenario where earlier-generation aligned
models help steer newer frontier models).


## Research Question

"At matched compute budget, when does a heterogeneous multi-model
collaboration protocol outperform the best single model in the
pool, and which structural properties (heterogeneity, topology,
critique format, round count) drive the difference?"

The compute-matched constraint is load-bearing: any multi-model
result that fails to beat a compute-matched single-model baseline
is not a real win. The named structural properties are the
*starting* axes for the experimental design; additional axes from
the protocol inventory may be added during the formal Design phase.


## Session-start read path

CLAUDE.md is auto-loaded into the system prompt and stays pinned
for the whole CLI invocation. Everything below lives in conversation
context, which is volatile across compaction.

**Warm session** (normal start or continuation):

1. `docs/status.md` — volatile state, next up, blockers, routed
   pointer. Read first.
2. The one file `docs/status.md` names in "Currently routed to,"
   if any.

**Cold session** (first time in the repo, long gap, or after a
compaction event):

1. `docs/status.md`
2. `docs/design/system-architecture.md` — the permanent home for
   what's been built and why.
3. `docs/decisions.md` — locked decisions and rationale.

**Post-compaction:** if a system reminder indicates the conversation
has been compacted, re-read `docs/status.md` before continuing.
CLAUDE.md itself is pinned and does not need re-reading.


## Working norms

### Write to `docs/status.md` at task start, not task end

Before starting any substantive unit of work, update `status.md`
to reflect what you're about to do. Task-start has a cleaner
trigger than task-end (you have to decide the next task anyway)
and a more graceful failure mode (skipping one task-start loses
one task's worth of currency, not many).

"Substantive unit of work" = anything whose commit will touch
`src/`, `docs/research/`, `docs/design/`, `docs/decisions.md`,
`WORKFLOW.md`, or `CLAUDE.md`. Not every edit — work units that
map to commits.

### The commit-msg hook

A commit-msg hook at `scripts/hooks/commit-msg` enforces the
above. If a commit stages substantive files without also staging
`docs/status.md`, the hook rejects the commit. Two valid
responses:

1. **Update `docs/status.md`**, stage it, re-commit. Preferred.
2. **Add `[skip-status] <one-line reason>` to the commit message**
   to bypass. Use only for genuinely trivial commits. Bypasses
   are visible in `git log`.

Install the hook after cloning with `scripts/install-hooks.sh`.

### Honest assessment

Your honest assessment is valued, including criticism. There is
no penalty for pointing out problems. You also don't need to
invent faults. Overlooking a real problem is as unhelpful as
inventing a false one. Applies to all models working in this
repo.


## How this project works

Artifact-driven: each phase produces a document, and conversations
with AI models are ephemeral working sessions — anything worth
keeping lands in a file. At key commitment points, artifacts get
independent review from 2–3 models with different training
lineages. Significant choices land in `docs/decisions.md` with
rationale.

The project moves through phases roughly in order:

```
Inspiration ── Literature ── Question ── Design ──▶ Experiment Loop ──▶ Analysis ── Write-up
```

A parallel **system-infrastructure track** runs alongside these
phases (IR, executor, experiment-spec layer, model clients). Both
Codex and Gemini independently flagged this as worth naming rather
than treating as an exception.

See `WORKFLOW.md` for the full phase table, review procedures,
and templates.


## File map

Single source of truth for what exists and what each file is for.
Update when a file is added or repurposed.

### Session-start

- `CLAUDE.md` — this file. Project brief, research question,
  working norms, file map. Pinned in system prompt.
- `docs/status.md` — volatile current state, next up, routed
  pointer.

### Durable reference

- `docs/design/system-architecture.md` — IR, executor, planned
  experiment-spec layer. Cold-start reading.
- `docs/decisions.md` — decision log. Cold-start reading.
- `WORKFLOW.md` — procedures, review templates, decision log
  template.
- `docs/backlog.md` — durable ideas and future directions not
  currently scheduled.

### Research artifacts

- `docs/research/inspiration.md` — extracted insights.
- `docs/research/protocol-inventory.md` — semi-formal protocol
  notation, 37+ variants, 19 structural variables.
- `docs/research/experimental-design.md` — promoted 2026-04-14
  after four rounds of Codex + Gemini review. Macro-model
  framing, Phase 1 scoped to executable scoring, pre-registered
  Protocol × Stratum interaction as primary statistical test
  with a pre-declared middle-band fallback.
- `docs/research/judge-design-notes_draft.md` — judge protocol
  detail, feeds the experimental design.
- `docs/research/human-validation-notes_draft.md` — staged human
  validation strategy (Phase 3).

### Literature, reviews, discussions

- `docs/literature/` — paper search, votes, full text for voted
  papers.
- `docs/reviews/` — multi-model review artifacts.
- `docs/discussions/` — joint design discussions with Codex /
  Gemini.

### Code

- `src/ir/` — typed protocol IR (core + surface authoring layer).
- `src/protocols/` — protocols expressed in the IR (CCR, ReConcile).
- `src/executor/` — minimal tree-walking interpreter over an
  injected `ModelClient`.
- `src/ir_haskell/` — reference Haskell implementation (aesthetic
  documentation, not a source language).

### Scripts and hooks

- `scripts/hooks/commit-msg` — status-discipline hook.
- `scripts/install-hooks.sh` — installs the repo's hooks.
