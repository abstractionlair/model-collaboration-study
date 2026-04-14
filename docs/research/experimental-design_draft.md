# Experimental Design — Draft

> **Status: DRAFT, awaiting formal review.**
> Rewritten 2026-04-14 against the committed research question. The
> previous version of this file predated the motivation pivot from
> "oversight quality" to capability-enhancement. This version is
> still a draft: it has not yet been through the formal Design-phase
> multi-model review, and several sections explicitly flag open
> decisions.

---

## Research Question

"At matched compute budget, when does a heterogeneous multi-model
collaboration protocol outperform the best single model in the
pool, and which structural properties (heterogeneity, topology,
critique format, round count) drive the difference?"

(Committed in `docs/decisions.md` on 2026-04-14. The full rationale,
including the alternatives considered, lives there.)

The question commits the design to four starting structural axes —
**heterogeneity, topology, critique format, round count**. These
are the variables the experiment must isolate. Other axes from the
protocol inventory may be added later if Phase 1 results suggest
they are load-bearing, but these four are the floor.

The compute-matched constraint is load-bearing: any multi-model
result that fails to beat a compute-matched single-model baseline
is not a real win, only a more expensive way of spending inference.
This is what the Compute Budget Structure section below
operationalizes.


## Independent Variables

The experimental commitment is a subset of the 19 structural
variables catalogued in `docs/research/protocol-inventory.md`. The
inventory is the catalog of *possible* knobs; the IVs below are
the *commitment to vary* a chosen subset.

The four axes named in the research question (mapped to inventory
labels in parentheses):

- **Model heterogeneity** (inventory: A, lineage diversity) —
  cross-family pools versus same-family ensembles.
- **Topology** (inventory: P) — parallel generation only, blind
  peer review, hierarchical review, dense all-to-all.
- **Critique format** (inventory: C) — free-form explanation,
  structured flags with rationale, flag-only.
- **Round count** (inventory: D) — 0, 1, or n review/revision
  passes.

Additional axes the experiment commits to varying or measuring,
even though not named in the research question:

- **Selection rule** (inventory: F) — majority vote, single judge,
  judge panel, verifier-aided selection.
- **Judge information regime** (inventory: G) — final answers
  only, process traces, reference-guided judging.
- **Capability gap** (inventory: H) — weaker reviewers checking
  stronger writers, peers checking peers, stronger reviewers
  checking weaker writers.
- **Task type** (inventory: I) — verifiable coding/tool tasks
  versus open-ended helpfulness/reasoning.
- **Interaction framing** (inventory: B) — collaborative review
  versus adversarial debate. Treated as a higher-cost ablation,
  not a primary axis.

Inventory variables E (session context), J (confidence weighting),
K (identity blinding), L (judgment format pairwise vs pointwise),
M (ensemble granularity), N (communication content), O (selection
vs fusion), Q (trigger policy), R (allocation policy), and
S (deliverable type) are not on the primary IV list. Some (E, K, L)
are still controlled in the experiment as fixed defaults — see
Common Interface Constraints and Judge Design below. Others
(J, N, O, Q, R, S) are deferred until Phase 1 results suggest they
matter. Token-level granularity (M) is not feasible against API
models in Phase 1 and is excluded.


## Protocol Conditions

These are the conditions to compare in the Phase 1 matrix. Listed
in order of complexity. Conditions A and B are the single-model
baselines that the compute-matched constraint requires — they are
not heterogeneous protocols, but the research question is unanswerable
without them.

- **A. Single-model baseline.** Best single subject model, one pass.
  This is the "what does one model alone get you" reference point.

- **B. Single-model compute baseline.** Same best subject model,
  best-of-N or self-consistency style. Critical: without this,
  multi-model methods may only "win" by spending more inference-time
  compute, which would be a confound rather than a result.

- **C. Heterogeneous generation + selection.** N different subject
  models answer independently; a judge selects the best answer; no
  critique or revision step. Tests whether lineage diversity alone
  produces a real gain over compute-matched single-model.

- **D. Heterogeneous generation + blind critique + revision +
  selection.** N models answer independently; each answer reviewed
  by 1–2 other models; reviews are blind (reviewers don't know
  model identity); writers revise once from structured feedback;
  final judge selects winner. This is roughly the ReConcile shape
  in `src/protocols/reconcile.py`, with one round.

- **E. Hierarchical variant.** Writers produce drafts; reviewers
  critique; a separate meta-reviewer synthesizes critiques; writers
  revise once; final judge selects. Often cheaper and cleaner than
  all-to-all cross-talk.

Additional conditions to consider, not yet committed to the matrix:

- **Adversarial debate.** Two-round debate between diverse models,
  then judge.
- **Collaborative vs adversarial framing.** Same models, same
  topology, framing-only ablation.
- **Lineage diversity comparison.** Cross-family pool (Claude + GPT
  + Gemini) versus same-family ensemble (e.g., three Qwen variants
  or three GPT sizes). Isolates the heterogeneity axis.
- **Critique format comparison.** Full explanation vs structured
  flags only ("flag don't explain"). Isolates critique format.
- **Judge information comparison.** Final answers only vs final
  answers + process traces vs reference-guided judging.
- **Selection rule comparison.** Vote vs single judge vs small
  judge panel.

**Mapping to existing IR protocols.** The IR currently expresses
CCR (Cross-Context Review) and ReConcile in `src/protocols/`. CCR
is a same-session-vs-fresh-context ablation rather than a multi-model
condition, so it does not map to A–E directly — it would be a
sub-experiment within the conditions that include a review step.
ReConcile is roughly condition D with one round. Conditions A, B,
C, and E need to be expressed in the IR before the matrix can be
run. None of them require new IR primitives.

**Default starting assumptions** for conditions that are not the
primary subject of an ablation:

- Prefer **blind independent review** to conversational all-to-all
  exchange.
- Prefer **at most one revision pass** unless extra rounds are
  being tested explicitly.
- Prefer **fresh-context revision** over same-session continuation.
  The IR exposes this as the `ContextMode` annotation, so it can
  be flipped per-step without restructuring.


## Candidate Model Pool

### Phase 1 (API-based method validation)

**Subjects.** Small, fast, cheap, genuinely different training
lineages. All positioned by their vendors for high-volume or
subagent-style work:

- GPT-5.4 mini (OpenAI)
- Claude Haiku 4.5 (Anthropic)
- Gemini 2.5 Flash (Google)

**Judges.** Frontier models from different families. Use cross-family
judging (the leave-one-family-out rule: OpenAI doesn't judge GPT
outputs, Anthropic doesn't judge Claude outputs, etc.) to mitigate
self-preference bias. See `judge-design-notes_draft.md` for the
full judge protocol.

**Pricing anchors** (per 1M tokens in/out, captured during the
exploratory phase — verify before kickoff):

- GPT-5.4 mini: $0.75 / $4.50
- Claude Haiku 4.5: $1.00 / $5.00
- Gemini 2.5 Flash: $0.30 / $2.50

Low enough to run the full ablation matrix without exotic funding.

### Later phases

- **Phase 2:** Self-hosted open models for transfer testing (e.g.,
  gpt-oss-120b, Qwen3-Coder-Next, Gemma 4 26B A4B). Tests whether
  Phase 1 results survive when the substrate changes from frontier
  APIs to open-weight serving.
- **Phase 3:** Frontier models as subjects with human review as
  ground truth on a subset.

The Phase 2/3 ladder is described in more detail under "Phased
Execution" below and in `human-validation-notes_draft.md`.


## Task Suite

Four buckets plus a private set:

- **Software engineering / repo tasks:** SWE-bench Verified or Lite.
  Docker-based reproducible evaluation. Requires x86_64 machine
  with at least 120 GB storage, 16 GB RAM, 8 CPU cores.
- **Competitive / isolated coding:** LiveCodeBench — designed to
  avoid contamination; covers code generation, self-repair, code
  execution, test-output prediction.
- **Tool use / function calling:** BFCL — executable rather than
  string-match based; supports evaluation of locally hosted models
  through OpenAI-compatible endpoints.
- **General chat / helpfulness:** AlpacaEval 2.0 (cheap automatic
  screen, ~0.98 Spearman correlation with Chatbot Arena, under $10
  to run) and Arena-Hard-Auto (stronger open-ended proxy).
- **Private set:** 50–100 prompts/tasks from real workflows. Acts
  as a contamination-resistant holdout.

### Task difficulty calibration

Calibrate task difficulty so the best single subject model succeeds
~40–60% one-shot. This places tasks in a regime where (a)
improvement is measurable rather than ceiling-bound and (b) the
frontier judge is comfortably "over-qualified" relative to the task
— the conditions under which LLM-as-judge is most reliable.

Better still, use difficulty bands rather than a single target:

- 30–40% one-shot success (harder for subjects)
- 45–55% one-shot success (middle zone)
- 60–70% one-shot success (easier for subjects)

This lets the study see whether multi-model collaboration helps
mainly near the decision boundary or more broadly.

The judge-side calibration check (verify that the frontier judge
can solve or correctly assess these items at very high rate on a
labeled slice) lives in `judge-design-notes_draft.md`.


## Compute Budget Structure

This section is load-bearing per the research question. Compare
all conditions at matched compute budgets to ensure that any
heterogeneous-protocol gain is not just an artifact of spending
more tokens.

Three budget tiers:

- **1× baseline compute** — one call from the best single subject
  model, one pass.
- **2× baseline compute** — twice the token budget of 1×.
- **4× baseline compute** — four times the token budget of 1×.

**The Best-of-N Discipline.** No multi-model result is considered
valid unless it outperforms a compute-matched single-model
best-of-N (or self-consistency) baseline at the same budget tier.
This is what condition B above is for. A heterogeneous protocol
spending 4× compute is compared to single-model best-of-4, not
single-model best-of-1.

The reason this matters: many multi-model results in the literature
report wins against a 1× single-model baseline without controlling
for the fact that the multi-model pipeline is consuming several
times more tokens. Those "wins" often vanish when compared at
matched compute. The whole research question depends on this
control being clean.


## Common Interface Constraints

For fair comparison, force all candidate subject models onto a
common denominator. Otherwise the experiment ends up testing
vendor-specific feature stacks rather than the protocol structure:

- Text in / text out only.
- No web search, file search, or code execution tools.
- Same max output length.
- Same temperature policy.
- Same context budget as far as feasible.
- Same critique rubric across reviewers.
- Pin model versions wherever possible (OpenAI supports snapshots
  for GPT-5.4 mini; Google advises specific stable models rather
  than preview aliases).

These constraints apply to the *subject* models. The judge model
is allowed richer affordances where the judge protocol calls for
them (e.g. execution-aided judging on coding tasks).


## Critique Rubric

Structured critique rather than free-form, with dimensions like:

- Correctness
- Completeness
- Unnecessary assumptions
- Tool-use correctness
- Code safety / likely test failures
- Confidence

The rubric format itself is one of the things the experiment varies
(critique format axis: free-form vs structured flags vs flag-only).
The structured rubric above is the *default* when not being
explicitly ablated.


## Metrics

At each compute budget tier:

- Quality / success rate (per task bucket and overall)
- Wall-clock latency
- Total tokens generated
- API cost (or GPU-seconds for self-hosted phases)
- Cost per solved task
- Variance across seeds
- Throughput / items per hour for batch evaluation
- Any degradation in interactive usability from added protocol depth

Cost per solved task is the headline efficiency metric and the one
that connects most directly to the compute-matched constraint.


## Judge Design

Judge design is treated in detail in
`docs/research/judge-design-notes_draft.md`. The minimum needed in
this document:

- **Executable scoring first.** For coding and tool-use tasks, use
  tests passing, BFCL executability, patch acceptance. LLM judge
  only where execution is unavailable.
- **Pairwise comparison** for winner selection; rubric scores for
  diagnostics.
- **Reference-guided judging** for open-ended tasks.
- **Cross-family judging** (leave-one-family-out) to mitigate
  self-preference bias.
- **Blinded model identities** in all judging.
- **Randomized answer order**; judge both orders when feasible.
- **Human audit** on ~5–10% of items, especially close calls and
  surprising wins.
- **Escalation triggers** recorded explicitly: low judge
  confidence, small pairwise margins, judge disagreement,
  execution-vs-judge conflict, headline-changing results.

Judge design should be treated as part of the experimental object,
not just fixed infrastructure: at minimum, record which judgments
were reference-free vs reference-guided, final-answer-only vs
process-aware, and single-judge vs panel.


## Phased Execution

1. **Phase 1: Method validation.** API models, automated judging,
   full protocol matrix. Establishes which protocol design choices
   matter.
2. **Phase 2: Transfer testing.** Test the top 2–3 conditions with
   self-hosted open models to check whether Phase 1 results
   transfer outside the frontier-API substrate.
3. **Phase 3: Frontier + human validation.** Run best conditions
   with frontier models as subjects, with human review as ground
   truth on a subset. Phase 3 is where independent annotation
   becomes load-bearing; see
   `docs/research/human-validation-notes_draft.md` for the staged
   strategy and resource estimates.

A practical refinement from the exploratory conversations:

- An automated API-first study may be publishable as a preliminary
  result.
- That artifact can then justify institutional support or paid
  annotation for stronger human validation.
- The staged path matters because independent access to annotators
  is a real bottleneck.


## Open questions, not yet resolved

These need decisions before the matrix is finalized:

- **Exact size of the Phase 1 matrix.** How many task instances per
  bucket per condition per budget tier? Driven by API cost budget
  and statistical-power considerations.
- **Number of seeds per condition.** Variance metric needs at
  least 3; ideally 5+.
- **Whether to include the adversarial-debate condition in Phase 1
  or defer it.** Adds a meaningful axis but also significantly
  more compute and protocol-implementation work.
- **How to handle the "convincing samples" / few-shot persuasion
  prompts** that appear in the ReConcile paper. These are
  experiment-spec-layer concerns (prompt templates), not protocol
  IR concerns, but they affect comparability of replications.
- **Concrete cost ceiling for Phase 1.** Should be set against the
  pricing anchors above before kickoff.


## Validation status

This document has not yet been through the multi-model independent
review that the workflow requires for design artifacts. Before
promotion to `experimental-design.md`, it needs:

- Independent review from 2–3 models with different training
  lineages.
- Cross-check against the protocol inventory to make sure no
  load-bearing axis was dropped.
- Cost estimate for the full Phase 1 matrix at the stated pricing.
- Sign-off that the IR is expressive enough to encode all five
  Phase 1 conditions.
