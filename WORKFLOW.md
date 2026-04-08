# Research Workflow

This document describes how work on this project is organized. The goal is
that anyone who clones the repo can follow the same process.


## Principles

1. **Write it down, then review it, before building on it.** Each phase
   produces a durable artifact. Get independent review before committing
   to a direction — especially on the research question and experimental
   design, where a wrong turn is expensive.

2. **Artifacts in the repo are the source of truth.** Conversations with
   AI models are ephemeral working sessions. Anything worth keeping lands
   in a file, written to be understood without the conversation that
   produced it.

3. **Multi-model review at key transitions.** When you're about to commit
   to a direction (finalizing the research question, approving an
   experimental design), get review from 2–3 models with different
   training lineages. The value comes from genuine independence, not from
   the number of reviewers.

4. **Record decisions with rationale.** Research involves choices that
   aren't visible in code — why this framing, why these models, why this
   task calibration. Write them down so they survive past the conversation
   where they were made.


## Phases

The project moves through these phases roughly in order, though earlier
phases may be revisited as later work reveals new information.

```
                                                    ┌─────────────────────────────────┐
                                                    │          Experiment Loop         │
                                                    │                                 │
Inspiration ── Literature ── Question ── Design ──▶ │ Pilot ── Implement ── Execute ──┤──▶ Analysis ── Write-up
                                           ▲        │   │                       │     │       │
                                           │        │   └── revise design ◀─────┘     │       │
                                           │        └─────────────────────────────────┘       │
                                           └──────────────────────────────────────────────────┘
                                                          (if results demand it)
```

| Phase | Produces | Location |
|-------|----------|----------|
| Inspiration | Extracted insights from exploratory conversations | `docs/research/inspiration.md` |
| Literature review | Synthesis of existing work, paper references | `docs/literature/` |
| Research question | Question, sub-questions, hypotheses | `docs/research/question.md` |
| Experimental design | Protocol, variables, baselines, metrics | `docs/research/experimental-design.md` |
| Pilot | Small-scale feasibility test | `data/pilot/` |
| Implementation | Experiment code (orchestration, prompts, evaluation) | `src/` |
| Execution | Raw results | `data/` |
| Analysis | Processed results, figures, statistical tests | `analysis/` |
| Write-up | Paper or report | `paper/` |

### Inspiration

The project began with exploratory conversations (not committed to the
repo but currently in a tmp directory on the filesystem) that covered
self-hosted AI stacks, multi-model collaboration literature,
experimental design ideas, and career considerations. The inspiration
document extracts the parts that matter for this research: key
findings, ideas that shaped the direction, and open threads worth
pursuing. It is a processed artifact, not a transcript.

### Commitment points and working phases

Not all phases need the same rigor. Literature review and implementation
are working phases — push forward, refine as you go. The research question
and experimental design are commitment points — get them reviewed before
proceeding.

### The experiment loop

Design, implementation, and execution are not a one-shot sequence. Expect
at least two passes:

1. **Pilot.** Implement a minimal version — one or two conditions, a
   handful of tasks — and run it. The goal is to validate feasibility:
   does the task calibration land in the right difficulty range? Does the
   judging pipeline produce sensible verdicts? Are the API costs and
   latency workable? Revise the experimental design based on what you
   learn before committing to a full run.

2. **Full run.** Implement the complete condition matrix, execute, and
   collect data. Even here, it may make sense to run conditions
   incrementally — start with the baselines and the most promising
   experimental condition, analyze, then decide whether the remaining
   conditions are worth running.

Analysis may also send you back. If results are ambiguous or surprising,
the right response may be to revise the design and run additional
conditions rather than to force a conclusion from inadequate data.


## Directory Structure

```
docs/
  literature/
    synthesis.md               # Thematic synthesis of existing work
    papers.md                  # Reference list with relevance notes
  research/
    inspiration.md             # Extracted insights from exploratory conversations
    question.md                # Research question, sub-questions, hypotheses
    experimental-design.md     # Protocol, variables, baselines, metrics
  reviews/                     # Multi-model review artifacts
  decisions.md                 # Decision log
src/                            # Experiment code
data/                           # Experimental results
  pilot/                        # Pilot run results
analysis/                       # Analysis code and outputs
paper/                          # Write-up
```


## Review Procedure

Reviews happen at the contributor's judgment, but are strongly recommended
before committing to the research question and experimental design.

### How to conduct a review

1. Open a model you haven't used to write the artifact (lineage diversity
   matters more than capability).
2. Share the artifact being reviewed. Also share any upstream artifacts it
   depends on — e.g., when reviewing the experimental design, include the
   research question.
3. Ask the model to review against specific criteria (see below).
4. Save the review to `docs/reviews/` with a descriptive filename, e.g.
   `research-question-gemini-2026-04-08.md`.

### Review criteria by artifact type

**Inspiration** (light review — mostly a check that nothing important was
lost or mischaracterized from the source conversations):
- Does it capture the key ideas that motivated the project?
- Is anything stated as settled that was actually left open?

**Research question:**
- Is the question well-scoped and answerable with the proposed methods?
- Are the sub-questions the right decomposition?
- Does the framing connect to existing literature and real-world relevance?
- Are there important aspects the question misses?

**Experimental design:**
- Do the baselines actually test the claims? (Especially: is there a
  compute-matched single-model baseline?)
- Are the independent variables cleanly isolated?
- Are the metrics appropriate for the task types?
- Are there confounds the design doesn't control for?
- Is the calibration approach sound?

**Literature synthesis:**
- Are there important papers or findings missing?
- Is the characterization of existing work accurate and fair?
- Are the identified gaps genuine?

### What to include in a review file

```markdown
# Review: [artifact name]

**Reviewer:** [model name and version, or person]
**Date:** [YYYY-MM-DD]
**Artifact reviewed:** [path to the file]

## Summary assessment
[1-2 sentences: overall quality and most important issue]

## Specific findings
[Numbered list of observations, concerns, or suggestions]

## Recommendation
[Proceed / Revise and re-review / Rethink approach]
```


## Decision Log

`docs/decisions.md` records significant choices — the kind where you
picked one path over another and the reasoning isn't obvious from the
artifacts themselves.

Format:

```markdown
## [YYYY-MM-DD] [Short title]

**Decision:** [What was decided]
**Alternatives considered:** [What else was on the table]
**Rationale:** [Why this choice]
**Status:** [Active / Superseded by ...]
```

Examples of things worth recording:
- Choosing to use API models rather than self-hosted for the study
- Choosing small models as subjects with frontier models as judges
- Specific framing choices for the research question
- Dropping or adding an experimental condition and why


## Updating COMMON.md

`COMMON.md` is the project brief that AI agents read at the start of a
session. Keep it current with:
- The research question (or a pointer to it once `question.md` exists)
- The current phase and immediate next step
- Pointers to key artifacts

It should be short — a few paragraphs at most. The detailed artifacts
live in their own files.
