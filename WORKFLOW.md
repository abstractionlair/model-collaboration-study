# Workflow Reference

Detailed procedures and templates for the project workflow. For the
overall shape, principles, and current phase, see
[CLAUDE.md](CLAUDE.md).


## Phases

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


## The Experiment Loop

Design, implementation, and execution are not a one-shot sequence.
Expect at least two passes:

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


## Review Procedure

### How to conduct a review

1. Open a model you haven't used to write the artifact (lineage diversity
   matters more than capability).
2. Share the artifact being reviewed. Also share any upstream artifacts it
   depends on — e.g., when reviewing the experimental design, include the
   research question.
3. Ask the model to review against the criteria below for that artifact
   type.
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

### Review file template

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

### Decision entry template

```markdown
## [YYYY-MM-DD] [Short title]

**Decision:** [What was decided]
**Alternatives considered:** [What else was on the table]
**Rationale:** [Why this choice]
**Status:** [Active / Superseded by ...]
```

### Examples of things worth recording

- Choosing to use API models rather than self-hosted for the study
- Choosing small models as subjects with frontier models as judges
- Specific framing choices for the research question
- Dropping or adding an experimental condition and why
