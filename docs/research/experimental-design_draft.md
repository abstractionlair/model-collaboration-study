# Experimental Design — Early Draft

> **Status: DRAFT — Incomplete and not reviewed.**
> This document is an early sketch drawn from exploratory conversations.
> It has not been reviewed, validated, or finalized. Many details will
> need to be revisited during the formal Design phase. Its purpose is to
> capture experimental-design specifics that emerged during exploration
> so they are not lost.

---

## Research Question

"When multiple AI models are used to oversee each other's outputs,
which properties of the multi-model protocol determine whether
oversight quality improves, degrades, or is wasted compute?"


## Independent Variables to Isolate

The exploratory conversations were more consistent about *which levers*
matter than about the final condition matrix. The main variables worth
isolating are:

- **Model heterogeneity** — cross-family pools versus same-family ensembles
- **Interaction framing** — collaborative review versus adversarial debate
- **Critique format** — structured flags versus free-form explanation
- **Topology** — parallel generation only, blind peer review, hierarchical review, dense all-to-all
- **Round count** — no review, one review/revision pass, multi-round interaction
- **Selection rule** — majority vote, single judge, judge panel, verifier/execution-aided selection
- **Judge information regime** — final answers only versus process traces versus reference-guided judging
- **Capability gap** — weaker reviewers checking stronger writers, peers checking peers, stronger reviewers checking weaker writers
- **Task type** — verifiable coding/tool tasks versus open-ended helpfulness/reasoning


## Protocol Conditions

The conversations identified these conditions to compare (in order of complexity):

- **A: Single-model baseline** — Best single model, one pass.
- **B: Single-model compute baseline** — Same best model, best-of-N or self-consistency style. Critical because without this, multi-model methods may only win by spending more inference-time compute.
- **C: Heterogeneous generation + selection** — N different models answer independently; a judge selects the best answer; no critique/revision.
- **D: Heterogeneous generation + blind critique + revision + selection** — N models answer independently; each answer reviewed by 1-2 other models; reviews are blind (reviewers don't know model identity); writers revise once from structured feedback; final judge selects winner.
- **E: Hierarchical variant** — Writers produce drafts; reviewers critique; a separate meta-reviewer synthesizes critiques; writers revise once; final judge selects. Often cheaper and cleaner than all-to-all cross-talk.

Additional conditions worth considering:

- Adversarial debate (two-round debate between diverse models, then judge)
- Collaborative vs. adversarial framing comparison using the same models
- Lineage diversity comparison: cross-family pool (Claude + GPT + Gemini) vs. same-family ensemble (e.g., three Qwen variants or three GPT sizes)
- Critique format comparison: full explanation vs. structured flags only ("flag don't explain")
- Judge-information comparison: final answers only vs. final answers + process traces vs. reference-guided judging
- Selection-rule comparison: vote vs. single judge vs. small judge panel

Default starting assumptions suggested by the conversations:

- Prefer **blind independent review** to conversational all-to-all exchange.
- Prefer **at most one revision pass** unless extra rounds are being tested explicitly.
- Prefer **fresh-context revision** over same-session continuation when technically feasible, since the exploratory literature notes pointed against repeated same-session review.


## Candidate Model Pool

### Phase 1 (API-based method validation)

- **Subjects:** GPT-5.4 mini, Claude Haiku 4.5, Gemini 2.5 Flash — small, fast, cheap, genuinely different training lineages. All positioned by their vendors for high-volume or subagent-style work.
- **Judges:** Frontier models from different families. Consider cross-family judging (OpenAI doesn't judge GPT outputs, Anthropic doesn't judge Claude outputs, etc.) to mitigate self-preference bias.
- Approximate API pricing noted in conversations: GPT-5.4 mini at $0.75/$4.50 per 1M tokens in/out; Claude Haiku 4.5 at $1/$5; Gemini 2.5 Flash at $0.30/$2.50. Low enough for large ablations.

### Later phases (if results warrant)

- Self-hosted open models for transfer testing (e.g., gpt-oss-120b, Qwen3-Coder-Next, Gemma 4 26B A4B)
- Frontier models as subjects with human review as ground truth


## Task Suite

Four buckets plus a private set:

- **Software engineering / repo tasks:** SWE-bench Verified or Lite. Docker-based reproducible evaluation. Requires x86_64 machine with at least 120 GB storage, 16 GB RAM, 8 CPU cores.
- **Competitive / isolated coding:** LiveCodeBench — designed to avoid contamination; covers code generation, self-repair, code execution, test-output prediction.
- **Tool use / function calling:** BFCL — executable rather than string-match based; supports evaluation of locally hosted models through OpenAI-compatible endpoints.
- **General chat / helpfulness:** AlpacaEval 2.0 (cheap automatic screen, 0.98 Spearman correlation with Chatbot Arena, under $10 to run) and Arena-Hard-Auto (stronger open-ended proxy).
- **Private set:** 50-100 prompts/tasks from real workflows.

Task difficulty should be calibrated so the best single subject model succeeds ~40-60% one-shot, placing tasks in a regime where improvement is possible and the frontier judge is "over-qualified."

Better still, use difficulty bands rather than a single target:

- 30-40% one-shot success
- 45-55% one-shot success
- 60-70% one-shot success

This allows the study to see whether multi-model oversight helps mainly
near the decision boundary or more broadly.


## Critique Rubric

The conversations suggested structured critique rather than free-form, using dimensions like:

- Correctness
- Completeness
- Unnecessary assumptions
- Tool-use correctness
- Code safety / likely test failures
- Confidence


## Metrics

At each compute budget level (1x, 2x, 4x baseline):

- Quality / success rate
- Wall-clock latency
- Total tokens generated
- GPU-seconds consumed (or API cost equivalent)
- Cost per solved task
- Variance across seeds
- Throughput / items per hour for batch evaluation
- Any degradation in interactive usability from added protocol depth


## Judge Design

- **Executable scoring first** — for coding and tool-use tasks, use tests passing, BFCL executability, patch acceptance. LLM judge only where execution is unavailable.
- **Pairwise comparison** — more stable than pointwise scoring; better aligned with head-to-head selection utility.
- **Rubric-based scoring** for diagnostics — dimensions like factual accuracy, completeness, source quality, tool efficiency (following Anthropic's production approach).
- **Reference-guided judging** — for open-ended tasks, have the frontier judge generate a reference answer, then judge pipeline output relative to that reference.
- **Blinded identities** — judge does not know which model produced which output.
- **Randomized answer order** — judge both orders when feasible to control position bias.
- **Cross-family judging** — consider leave-one-family-out rule to mitigate self-preference bias.
- **Human audit** — ~5-10% of items, especially close calls and surprising wins.
- **Escalation** — when judge is low-confidence or margin is small, send to second judge or human.

Judge design should also be treated as part of the experimental object,
not just fixed infrastructure. At minimum, record which judgments were:

- reference-free versus reference-guided
- final-answer-only versus process-aware
- single-judge versus panel or escalated review


## Compute Budget Structure: The "Best-of-N Discipline"

Compare all conditions at matched compute budgets to ensure results aren't just an artifact of spending more tokens:

- **1x baseline compute**
- **2x baseline compute**
- **4x baseline compute**

No multi-model result is considered valid unless it outperforms a compute-matched single-model baseline (Best-of-N).


## Common Interface Constraints

For fair comparison, force all candidate models onto a common denominator:

- Text in / text out only
- No web search, file search, or code execution tools
- Same max output length
- Same temperature policy
- Same context budget as far as feasible
- Same rubric for critique

Otherwise you end up testing vendor-specific feature stacks rather than the pipeline.


## Phased Execution

1. **Phase 1: Method validation** — API models, automated judging, full protocol matrix. Establishes which protocol design choices matter.
2. **Phase 2: Transfer testing** — Test top 2-3 conditions with self-hosted open models to check whether results transfer.
3. **Phase 3: Frontier + human validation** — Run best conditions with frontier models as subjects, human review as ground truth on a subset.

A practical refinement from the conversations:

- An automated API-first study may be publishable as a preliminary result.
- That artifact can then justify institutional support or paid annotation for stronger human validation.
- The staged path matters because independent access to annotators is a real bottleneck.

Pin model versions wherever possible (OpenAI supports snapshots for GPT-5.4 mini; Google advises using specific stable models rather than preview aliases).

---

Many of these details will need to be revisited and refined during the formal Design phase. This draft captures what emerged from exploratory conversations to avoid losing the specifics.
aptures what emerged from exploratory conversations to avoid losing the specifics.
