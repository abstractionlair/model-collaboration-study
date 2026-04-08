# Model Collaboration Study

## Research Question (tentative)

"When multiple AI models are used to oversee each other's outputs,
which properties of the multi-model protocol determine whether
oversight quality improves, degrades, or is wasted compute?"

## Current Phase

**Inspiration** — extracting useful content from the exploratory
conversations that started the project into `docs/research/inspiration.md`.


## Model Guidance

### All models

Your honest assessment is valued. There is no penalty for pointing
out problems — accurate feedback, including criticism, is genuinely
helpful. At the same time, you don't need to force yourself to find
faults. If something is good, say so. If something is wrong, describe
it. Your authentic judgment is what matters.

Overlooking a real problem is as unhelpful as inventing a false one.

### Claude Code

No additional instructions at this time.

### Gemini

No additional instructions at this time.

### Codex / OpenAI agents

No additional instructions at this time.


## How This Project Works

### Principles

The project is artifact-driven: each phase produces a document, and
conversations with AI models are ephemeral working sessions — anything
worth keeping lands in a file. At key commitment points (especially
the research question and experimental design), artifacts get
independent review from 2–3 models with different training lineages.
Significant choices are recorded with rationale in a decision log so
they survive past the conversation where they were made.

### Workflow shape

The project moves through phases roughly in order:

```
Inspiration ── Literature ── Question ── Design ──▶ Experiment Loop ──▶ Analysis ── Write-up
```

- **Inspiration** captures motivating ideas from exploratory
  conversations without overcommitting to specific claims or design.
- **Literature** synthesizes existing work.
- **Question** and **Design** are commitment points — get them
  reviewed before proceeding.
- The **Experiment Loop** (pilot → implement → execute → possibly
  revise design) expects at least two passes. The pilot validates
  feasibility before a full run.
- **Analysis** may send you back to redesign if results are ambiguous.

Each phase produces an artifact in a known location. See
[WORKFLOW.md](WORKFLOW.md) for the full phase table, directory
structure, review procedures, and templates.

### Key artifacts

- `docs/research/inspiration.md` — extracted insights (current phase)
- `docs/research/question.md` — research question (not yet written)
- `docs/research/experimental-design.md` — protocol and variables (not yet written)
- `docs/literature/` — literature synthesis (to be populated)
- `docs/reviews/` — multi-model review artifacts
- `docs/decisions.md` — decision log

### When to consult WORKFLOW.md

Read [WORKFLOW.md](WORKFLOW.md) when you need:
- The directory structure for where files belong
- Review criteria for a specific artifact type
- The template for review files or decision log entries
- Detail on the experiment loop (pilot vs full run)
- The step-by-step procedure for conducting a review
