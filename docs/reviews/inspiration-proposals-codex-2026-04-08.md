# Review: inspiration.md proposals

**Reviewer:** OpenAI Codex (GPT-5)
**Date:** 2026-04-08
**Artifact reviewed:** `docs/research/inspiration_claude.md`, `docs/research/inspiration_gemini.md`, `docs/research/inspiration_gpt.md`

## Summary assessment

`inspiration_gpt.md` is the strongest candidate for the canonical
`docs/research/inspiration.md`: it is the best match for the
`WORKFLOW.md` definition of the phase artifact and the best reflection of
the committed Claude/GPT source conversations. `inspiration_claude.md`
contains useful material but overcommits to literature and design
choices that still read as exploratory; `inspiration_gemini.md` reads as
a model-specific memo rather than the shared project artifact.

## Specific findings

1. `docs/research/inspiration_gemini.md` is not in the right artifact
   shape for this phase. The title and framing are explicitly
   model-specific ("Gemini Perspective") rather than an extracted,
   source-of-truth project artifact, which conflicts with the workflow's
   goal for `docs/research/inspiration.md` as a repo-level synthesis.
   If kept, it should be treated as supplementary review input, not the
   base draft.

2. `docs/research/inspiration_gemini.md` appears to rely on a source
   that is not committed in the repo. I could validate the Claude and GPT
   drafts against `docs/initial-conversations/claude.md` and
   `docs/initial-conversations/gpt.md`, but there is no corresponding
   Gemini transcript present. That makes it weaker as the canonical
   artifact under the project's "artifacts in the repo are the source of
   truth" principle.

3. `docs/research/inspiration_claude.md` collapses multiple workflow
   phases into one document. The sections on a fixed research question,
   sub-questions, candidate model pool, protocol matrix, task suite, and
   metrics move well beyond "extract useful content from exploratory
   conversations" and into the later Question and Design phases. That
   makes the draft less suitable as `inspiration.md`, because it
   hardens choices that should still feel provisional at this stage.

4. `docs/research/inspiration_claude.md` states several literature-level
   claims with more certainty and numerical precision than is healthy for
   an inspiration document. The "reliability hierarchy" and detailed
   effect-size bullets read closer to literature synthesis than
   exploratory motivation, and some numbers are not stable across the
   committed source conversations. In the canonical inspiration artifact,
   these should be softened into directional takeaways unless they are
   directly cited.

5. `docs/research/inspiration_gpt.md` is the best-balanced proposal and
   I did not find a material mischaracterization relative to the
   available source conversations. It preserves the main motivations that
   recur in the transcripts: compute-matched baselines, diversity over
   multiplicity, caution about extra rounds, judging as part of the
   protocol, staged API-first evaluation, and transfer/human-validation
   caveats.

6. `docs/research/inspiration_gemini.md` is also too compressed to stand
   alone as the main artifact. It captures a clean thesis, but it drops
   several recurring themes that appear in both committed source
   conversations and the stronger GPT draft: judge design as a central
   variable, API-first method validation before transfer to self-hosted
   models, and the staged path from automated evaluation to later human
   validation.

## Recommendation

Revise and re-review.

Use `docs/research/inspiration_gpt.md` as the base for
`docs/research/inspiration.md`. Pull over a small amount of high-value
material from `docs/research/inspiration_claude.md`, especially the
"flag don't explain" and agentic-oversight threads, but remove or soften
the literature-heavy ranking language and protocol-specific design
details. Keep `docs/research/inspiration_gemini.md` as optional review
input rather than the canonical draft.
