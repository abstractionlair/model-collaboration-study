# Experimental Design — Draft

> **Status: DRAFT, awaiting formal review.**
> Rewritten 2026-04-14 against the committed research question. The
> previous version of this file predated the motivation pivot from
> "oversight quality" to capability-enhancement.
>
> **Second-pass revision 2026-04-14** (same day) in response to
> preliminary feedback from Codex and Gemini: Phase 1 narrowed to
> executable-scoring only (walk-before-run), compute denominated in
> dollars, a homogeneous-protocol control (D') added to isolate the
> heterogeneity axis, Variable K (identity blinding) locked as a
> fixed default, and Condition B's selector held constant with the
> multi-model conditions.
>
> **Third-pass revision 2026-04-14** (same day) in response to
> second-pass feedback: the selector-as-oracle flaw Gemini
> identified is fixed (internal selectors are now part of each
> protocol's definition, non-oracle, counting toward the dollar
> budget); the statistical plan is switched to a pre-registered
> Protocol × Stratum interaction as the primary test (Gemini) to
> avoid the pooled-average trap; the "what the matrix isolates"
> claims are rewritten to be modest per Codex, with D' → D no
> longer claimed to fully separate lineage diversity from price
> arbitrage; tie-breaking, partial-credit, and hard-failure
> policies are specified for executable scoring. This version
> still has not been through the formal Design-phase review.

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


## Scope of Phase 1

Phase 1 is restricted to **verifiable tasks with executable
scoring** (tests passing, BFCL executability, patch acceptance).
No LLM-as-judge apparatus is used in Phase 1.

This is a walk-before-run decision, not a rejection of frontier
judges for open-ended tasks. Three reasons it matters:

1. **Fewer load-bearing assumptions at once.** LLM-as-judge
   reliability is an instrument assumption that must be defended.
   Running it simultaneously with the protocol experiment means
   any weird result can be attributed to judge unreliability, and
   the protocol effect never gets cleanly measured.
2. **Unarguable measurement.** "Protocol P solves 47% of
   SWE-bench Verified at $X cost; single-model baseline solves
   38% at the same cost" is basically unarguable. A similar
   claim filtered through a frontier-model judge invites an
   entire class of reviewer objections that the Phase 1 result
   should not have to defend.
3. **Phase 2 gets calibrated.** A Phase 1 executable result
   becomes a reference point for Phase 2's LLM-judged work:
   "does the frontier judge agree with the executable ground
   truth on the overlap set?" is a validation check that is
   only possible once Phase 1 exists.

Phase 2 adds open-ended tasks with LLM judging, informed by
what Phase 1 learned about structural properties and by having
a concrete protocol effect to calibrate the judge against. The
judge-design work is deferred, not abandoned; see
`docs/research/judge-design-notes_draft.md`.

**Important distinction.** The Phase 1 restriction is on *final
evaluation*, not on whether protocols may contain LLM-based
internal decisions. Protocols will naturally have peer-level
models doing critique, meta-review, revision selection, etc. —
those are the *subject under study*, not the instrument of
measurement. Final scoring of protocol outputs is executable;
internal protocol decisions are whatever the protocol defines.


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

- **Capability gap** (inventory: H) — weaker reviewers checking
  stronger writers, peers checking peers, stronger reviewers
  checking weaker writers. In Phase 1, capability gap is mostly
  flat (the three subject models are near each other in
  capability); real gap-varying comes in later phases.
- **Task type** (inventory: I) — Phase 1 is restricted to
  verifiable coding/tool tasks. Open-ended helpfulness/reasoning
  is deferred to Phase 2 along with the LLM-judge apparatus.
- **Interaction framing** (inventory: B) — collaborative review
  versus adversarial debate. Treated as a higher-cost ablation,
  deferred from Phase 1.

**Selection rule** (inventory: F) and **judge information
regime** (inventory: G) are not varied in Phase 1. With
executable scoring, the selection rule is fixed to "pick the
candidate that passes the executable check" (or the one that
passes the most tests, for partial-credit cases), and there is
no judge to vary the information regime of. These become IVs in
Phase 2 when LLM-judged open-ended tasks enter the suite.

Inventory variables E (session context), J (confidence weighting),
K (identity blinding), L (judgment format pairwise vs pointwise),
M (ensemble granularity), N (communication content), O (selection
vs fusion), Q (trigger policy), R (allocation policy), and
S (deliverable type) are not on the primary IV list.

**Variable K (identity blinding) is locked to blinded** as a fixed
default in Phase 1. Reason: heterogeneous-pool conditions have
models critiquing each other's outputs, and lineage-biased
sycophancy or antagonism would confound the critique format if
models knew which vendor produced which draft. All critiques are
presented as "here is a draft from a peer AI," never "here is a
draft from GPT-5.4 mini." Flagged by Gemini as non-deferrable.

E (session context) and L (judgment format pairwise vs pointwise)
are also controlled as fixed defaults — see Common Interface
Constraints below.

The deferred set (J, N, O, Q, R, S) is held until Phase 1 results
suggest they matter. Codex flagged **O (selection vs fusion)** as
the most plausibly load-bearing of the deferred set; worth
revisiting if Phase 1 results are ambiguous about why a protocol
condition won or lost. Token-level granularity (M) is not feasible
against API models in Phase 1 and is excluded.


## Protocol Conditions

These are the conditions to compare in the Phase 1 matrix. Listed
in order of complexity. Conditions A and B are the single-model
baselines that the compute-matched constraint requires — they are
not heterogeneous protocols, but the research question is unanswerable
without them. Condition D' is a homogeneous-protocol counterpart
to D, added to give a cleaner heterogeneity comparison inside a
fixed protocol family.

### Selectors are part of the protocol

Every protocol with more than one candidate answer must commit to
**exactly one final submission** before that submission is
scored. The mechanism that collapses multiple candidates into one
submission is the protocol's **internal selector**, and each
protocol defines its own. Two otherwise-identical pipelines that
differ in their selector are different pipelines.

**Internal selectors must be non-oracle.** They must not have
access to the final executable scoring mechanism at selection
time. If a protocol could run the tests on each candidate and
submit whichever passes, the entire experiment collapses into
Pass@N on the task suite — consensus-building protocols would
lose mechanically to independent-sampling protocols because
consensus suppresses output variance. Pass@N rewards variance,
so any protocol that reduces variance (which collaborative ones
typically do) is structurally disadvantaged. That comparison
would be measuring search-space coverage, not collaboration
effectiveness. Gemini flagged this in the second-pass review.

Legal internal selectors include:

- **Self-consistency / majority vote** on the final submission
  (feasible when answers are comparable token-for-token or via a
  canonicalization step).
- **Peer-LLM judgment** — a model from the subject pool (or
  another peer-level instance), blinded to identities, choosing
  among candidates without access to the executable ground
  truth.
- **Protocol-native aggregation** — e.g., ReConcile's
  confidence-weighted voting on revised answers.

Isolating comparisons (most importantly D → D') hold the
internal selector constant across the two conditions as part of
holding "protocol family" constant. Comparisons across different
protocol families (e.g., B vs. D, or D vs. E) will typically
involve different selectors, and that is fine: the selector is
part of what defines the protocol, and varying it is part of
what we are studying.

**Internal protocol calls count toward the dollar budget.**
Critiques, meta-reviews, revisions, and the internal selector's
own calls all spend budget. The final executable scoring step
does not count toward the protocol's budget (it is the
evaluator, not part of the pipeline).

### The matrix

Each condition specifies its internal selector alongside its
structural shape. Selectors are non-oracle and count toward the
dollar budget.

- **A. Single-model, one pass.** Best single subject model, one
  generation, submitted as-is. No internal selector needed —
  there is only one candidate. Reference point for "what does
  one model alone get you at $X."

- **B. Single-model, repeat-and-select.** Same best subject
  model, N independent samples at the tier's dollar budget.
  Internal selector: **self-consistency / majority vote** where
  the task permits canonicalization, else a **peer-LLM judge**
  from the subject pool (blinded, no test access). The key
  discipline is that this selector is not the executable scorer.
  Without this condition, multi-model "wins" could be confounded
  with inference-time compute spent by a single model.

- **C. Heterogeneous parallel generation + peer-LLM selection.**
  N different subject models answer independently; a peer-LLM
  from the subject pool (blinded, no test access) selects the
  submission. No critique or revision. Tests whether lineage
  diversity alone produces a real gain at matched dollars when
  combined with peer-LLM selection.

- **D. Heterogeneous ReConcile-style.** N different subject
  models answer independently; each draft reviewed by 1–2 other
  models (identities blinded — see Variable K); writers revise
  once from structured feedback; **protocol-native aggregation**
  (ReConcile-style confidence-weighted voting on the revised
  answers) selects the submission. Roughly the ReConcile shape
  in `src/protocols/reconcile.py`, though the mapping is loose
  — ReConcile's convincing-samples mechanism and exact
  aggregation details are not yet reflected in the IR version.

- **D'. Homogeneous ReConcile-style.** Same topology and same
  internal selector as D, but N instances of the *same* best
  single subject model play the writer and reviewer roles
  (identities still blinded; each instance presented as "a peer
  AI"). Gemini's proposed control. Holding selector constant
  with D is part of what makes the D → D' comparison clean.

- **E. Hierarchical variant.** Writers produce drafts; reviewers
  critique; a separate meta-reviewer synthesizes critiques;
  writers revise once. Internal selector: the meta-reviewer's
  aggregation logic itself, or a peer-LLM judge on the final
  revised submissions — defined as part of the protocol.
  Typically cheaper than all-to-all cross-talk. Usually run as
  heterogeneous; a homogeneous E' could be added as a follow-on
  if D → D' gives an interesting signal.

### What the matrix tests

The comparisons the design supports, stated modestly:

- **A → B:** protocol-free compute scaling within a single
  model. The cleanest isolating comparison in the matrix:
  controls for "is inference-time compute doing the work by
  itself?"
- **B → D':** the protocol-family comparison *with pool
  composition held constant*. Tests whether review/revise
  machinery helps *at all*, inside a single model. Not a pure
  isolation of "machinery" — B and D' also differ in their
  internal selectors (majority vote vs. ReConcile aggregation).
  The comparison is "does the D-family machinery beat the
  B-family baseline on the same pool?" not "does review/revise
  machinery in isolation help."
- **D' → D:** heterogeneous pool composition vs. homogeneous,
  with protocol family and internal selector held constant
  *under market prices*. This is the cleanest heterogeneity
  comparison the matrix supports. It does not, by itself,
  separate lineage diversity from price arbitrage — the
  heterogeneous pool includes cheaper models and therefore buys
  more tokens at matched dollars. See the Compute Budget
  Structure section for the arbitrage discussion and the
  proposed pinned-price follow-on.
- **C vs. D vs. E:** family-level comparisons of three
  heterogeneous protocol shapes at matched dollars. These are
  not isolating comparisons — each family differs in topology,
  selector, and round structure. They are screen-level
  comparisons: "which family is most worth isolating in
  follow-on work?"

This is an intentionally screened matrix, not an exhaustive
factorial. Phase 1 is a **screen of protocol families** (A, B,
C, D, E) **plus one surgical isolating control** (D' for
heterogeneity inside the D family). Finer-grain axis isolation
(critique format, round count) is reserved for follow-on
ablations on whichever family Phase 1 surfaces as most
promising. Codex flagged the earlier draft's ambiguity between
"screen" and "isolating experiment"; this is the resolution.

Additional conditions to consider, not committed to the primary
Phase 1 matrix:

- **Adversarial debate.** Two-round debate between diverse
  models, then selection. Deferred: adds an interaction-framing
  variable and a prompting-persona variable on top of the
  structural ones, and would blow up variance before the
  structural effects are characterized. Revisit after Phase 1.
- **Critique format comparison (free-form vs structured flags
  vs flag-only).** Follow-on ablation on the winning protocol
  family from Phase 1.
- **Round count comparison (0 / 1 / n passes).** Same.

**Mapping to existing IR protocols.** The IR currently expresses
CCR (Cross-Context Review) and ReConcile in `src/protocols/`.
CCR is a same-session-vs-fresh-context ablation rather than a
multi-model condition, so it does not map to the primary matrix
directly — it would be a sub-experiment within conditions that
include a review step. ReConcile is roughly condition D with one
round, though the mapping is loose (the ReConcile paper's
convincing-samples mechanism and aggregation details are not
yet reflected in the IR version). D' can be expressed by
instantiating the same ReConcile protocol with all slots filled
by the same model ID. Conditions A, B, C, D', and E all need to
be expressed in the IR before the matrix can be run. None
require new IR primitives.

**Default starting assumptions** for conditions that are not the
primary subject of an ablation:

- Prefer **blind independent review** to conversational
  all-to-all exchange.
- Prefer **at most one revision pass** unless extra rounds are
  being tested explicitly.
- Prefer **fresh-context revision** over same-session
  continuation. The IR exposes this as the `ContextMode`
  annotation, so it can be flipped per-step without
  restructuring.


## Candidate Model Pool

### Phase 1 (API-based method validation)

**Subjects.** Small, fast, cheap, genuinely different training
lineages. All positioned by their vendors for high-volume or
subagent-style work:

- GPT-5.4 mini (OpenAI)
- Claude Haiku 4.5 (Anthropic)
- Gemini 2.5 Flash (Google)

**Judges (Phase 1).** None. Final scoring is executable. Frontier
models only enter as judges in Phase 2, when open-ended tasks
join the suite. See `judge-design-notes_draft.md` for that
deferred planning.

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

Phase 1 is restricted to task families with executable scoring.
Three committed buckets plus an optional private set:

- **Software engineering / repo tasks:** SWE-bench Verified or
  Lite. Docker-based reproducible evaluation. Requires x86_64
  machine with at least 120 GB storage, 16 GB RAM, 8 CPU cores.
  Scoring: patch acceptance / tests passing.
- **Competitive / isolated coding:** LiveCodeBench — designed to
  avoid contamination; covers code generation, self-repair, code
  execution, test-output prediction. Scoring: test execution.
- **Tool use / function calling:** BFCL — executable rather than
  string-match based; supports evaluation of locally hosted
  models through OpenAI-compatible endpoints. Scoring:
  executability on the declared tool surface.
- **Private set (conditional):** 50–100 prompts/tasks from real
  workflows, each paired with an executable check (a test, a
  reference-output comparison, or a verifier function). Acts as
  a contamination-resistant holdout. Open question: is it
  feasible to construct 50–100 such items with executable checks
  in reasonable time? If not, drop from Phase 1 and defer to
  Phase 2.

**Dropped from Phase 1:** AlpacaEval 2.0 and Arena-Hard-Auto.
Both are LLM-judged by construction and would reintroduce the
judge-apparatus question Phase 1 is explicitly deferring. These
return in Phase 2 as part of the open-ended-helpfulness arm.

### Task difficulty strata

Calibrate task difficulty so the best single subject model
succeeds in a measurable regime — not near 0% (where nothing
helps) and not near 100% (where nothing can help). With
executable benchmarks the calibration lever is *selection*:
pick a subset where the best subject model lands in the target
band, rather than constructing buckets de novo.

Use three strata rather than a single target:

- **30–40%** one-shot success (harder for subjects)
- **45–55%** one-shot success (middle zone)
- **60–70%** one-shot success (easier for subjects)

The strata exist because the research question asks **when** —
not just whether — a protocol outperforms. "When" is a gating
question, and the strata are how it is operationalized.

### The strata hypothesis

Collaboration protocols are expected to exhibit a utility curve
across task difficulty (Gemini's framing):

- **Easy band (60–70%):** collaboration may slightly *degrade*
  performance. Reviewers "find" issues in already-correct drafts
  and introduce changes that make them worse.
- **Middle band (45–55%):** collaboration shines. The draft is
  often close but flawed; a reviewer who catches the flaw
  enables a substantive revision.
- **Hard band (30–40%):** collaboration fails or is neutral.
  Neither writer nor reviewer reliably knows the right answer,
  so review adds noise without adding signal ("the blind leading
  the blind").

If this hypothesis is right, the protocol effect *depends on*
difficulty. A pooled main-effect test averages a negative easy
effect, a positive middle effect, and a null hard effect into
approximately zero — the trap Gemini flagged.

### Statistical plan

**Primary pre-registered test:** the **Protocol × Stratum
interaction**. Specifically, "does the protocol's effect on
success rate differ systematically across the three strata in
the direction predicted by the strata hypothesis?" This directly
tests the "when" in the research question.

**Pre-specified stratified estimates:** protocol effect within
each stratum (easy, middle, hard), reported alongside the
interaction test. Because these are pre-specified (not
post-hoc), they are not fishing — they are the concrete form the
interaction takes.

**Pooled main effect:** reported as a secondary descriptive
summary, not as the primary finding. A null pooled effect does
not kill the result if the interaction is significant; a
positive pooled effect is a bonus, not a requirement.

**Reporting flow:** the narrative can read as a drilldown
("overall score at $2X: D = X%, B = Y%; within the middle band,
D = X' %, B = Y' %") — the only constraint is that the
statistical primacy is on the interaction, not the pooled
average.

**Fallback if power is too thin to detect the interaction.**
Collapse Phase 1 to the middle band (45–55%) only, with the
other two strata deferred to Phase 2 or dropped. This preserves
the cleanest signal at the cost of the "when does it help"
granularity.


## Compute Budget Structure

This section is load-bearing per the research question. Compare
all conditions at matched compute budgets to ensure that any
heterogeneous-protocol gain is not just an artifact of spending
more compute.

### The compute unit: US dollars

"Compute" is operationalized as **US dollars of API spend**, not
tokens. Two reasons:

1. **Tokens don't compose across tokenizers.** Different
   vendors tokenize differently; a "matched token budget" across
   a cross-family pool would require conversion factors that
   don't naturally exist. Dollars do compose — $1 spent is $1
   spent, regardless of which model consumed it.
2. **Dollars are the binding constraint in practice.** In real
   deployments, the constraint on protocol design is the budget,
   not a token budget. Dollar-matching makes the experiment
   answer the question operators actually care about: given $X
   to spend, what protocol gets the best result?

Pricing anchors are those in the Candidate Model Pool section.
**Pin the anchors at experiment kickoff and re-verify before
each run** — vendor pricing changes are the most common reason
a run's results become non-comparable across weeks.

### Budget tiers

Three dollar-denominated budget tiers, anchored to the
single-model baseline:

- **$X** — the dollar cost of Condition A (one pass from the
  best single subject model on one task instance), averaged
  over the task suite.
- **$2X** — twice that amount, distributed however the protocol
  chooses.
- **$4X** — four times that amount.

All non-A conditions run at $2X and $4X. Condition A only makes
sense at $X (one pass is one pass). Condition B runs at all
three tiers; the $X run is useful as a sanity check but doesn't
test the compute hypothesis.

### The Best-of-N Discipline

No multi-model result is considered valid unless it outperforms
a dollar-matched Condition B (single-model repeat-and-select) at
the same budget tier. A heterogeneous protocol spending $4X is
compared to single-model $4X repeat-and-select, not to
single-model $X single-pass.

The reason this matters: many multi-model results in the
literature report wins against a 1× single-model baseline
without controlling for the fact that the multi-model pipeline
is consuming several times more compute. Those "wins" often
vanish when compared at matched compute. The whole research
question depends on this control being clean.

### Price arbitrage as a structural effect

One honest subtlety in dollar-matching: at matched dollars, a
heterogeneous pool that includes a cheaper model (e.g. Gemini
Flash at $0.30/$2.50 per 1M tokens) will naturally produce more
total tokens than a pool composed only of pricier models. So a
"heterogeneity win" at matched dollars could partly be a
"price-arbitrage win" — the protocol is literally buying more
generation for the same money.

This is not a confound to eliminate. In the capability-enhancement
framing the research question commits to, the ability to mix
price points across a heterogeneous pool is a genuine structural
advantage of heterogeneity, not a confound. But it means
comparisons between homogeneous and heterogeneous conditions
include a price-arbitrage component.

Condition D' (homogeneous ReConcile) is the control that lets
you separate the two effects: if D beats D' at matched dollars
with D' running on the best single subject model, then
heterogeneity is adding *something* — either lineage diversity
proper, or price arbitrage, or both. A follow-on ablation could
pin a single price point across all pool members to isolate
lineage diversity from arbitrage if Phase 1 results make that
distinction interesting.


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

These constraints apply to the subject models. In Phase 1 there
is no judge model; scoring is executable. In Phase 2 the judge
will be allowed richer affordances (e.g. execution-aided
judging on coding tasks) per the Phase 2 design.


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

At each dollar budget tier:

- Success rate (per task bucket and overall)
- Success rate within each difficulty stratum (30–40, 45–55,
  60–70% bands) — preserves the threshold-dynamic signal
- Wall-clock latency
- Total tokens generated (as a supplementary diagnostic; dollars
  are primary)
- Dollars per solved task (**headline efficiency metric**)
- Variance across seeds
- Throughput / items per hour for batch evaluation

Dollars per solved task is the headline efficiency metric and
the one that connects most directly to the compute-matched
constraint.


## Scoring

Phase 1 uses **executable scoring only**. Per task bucket:

- **SWE-bench:** patch application and test suite execution
  inside the per-instance Docker environment. **Binary score**
  per instance: the full per-instance test suite either passes
  or does not.
- **LiveCodeBench:** test execution against the declared test
  set. **Fractional score** per instance: fraction of declared
  tests that pass.
- **BFCL:** executability on the declared tool surface.
  **Binary score** per instance: argument validity + invocation
  success + output-shape match.
- **Private set (if included):** per-item executable check
  paired at authoring time. Binary or fractional depending on
  the check.

**Success rate** is the aggregation: for binary buckets, fraction
of instances scored positively; for fractional buckets, mean
fractional score across instances. Stratum-level success rate
is computed the same way within each stratum.

**Tie-breaking.** For any comparison where two conditions finish
with identical success rates at a matched budget tier (e.g.
both at 0% or both at 100% within a small stratum), the
tie-breaker is **dollars per solved task** — i.e. the cheaper
condition wins. If neither solves anything, the tie stands and
is reported as such.

**Handling of hard failures** (Docker environment refuses to
build, API returns a malformed response, network errors): the
task instance is retried up to three times on transient errors;
after that the instance is scored as a failure for that
condition. All retries are counted toward the dollar budget.
The number of hard failures per condition is recorded as a
diagnostic.

Blinded model identities still matter for the *internal* work
of protocols that include critique steps (Variable K) — see
Independent Variables. But the final scoring step has no LLM
judge whose bias needs to be managed.

LLM-as-judge apparatus — reference-guided judging, cross-family
judge panels, pairwise comparison, human audit on close calls —
is deferred to Phase 2. See
`docs/research/judge-design-notes_draft.md` for that planning.
The Phase 1 executable result becomes a calibration anchor for
Phase 2's judge validation.


## Phased Execution

1. **Phase 1: Method validation on verifiable tasks.** API
   models, executable scoring only, protocol screen plus the D'
   heterogeneity isolator. Establishes which protocol design
   choices matter on tasks where ground truth is mechanical.
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

- **Exact size of the Phase 1 matrix.** How many task instances
  per bucket per condition per budget tier? Driven by dollar
  budget and statistical-power considerations. The three
  difficulty strata roughly triple the instance count needed
  for stratum-level power, though the primary statistical test
  pools across strata.
- **Number of seeds per condition.** Variance metric needs at
  least 3; ideally 5+.
- **Private set feasibility.** Can 50–100 real-workflow items
  be authored with executable checks in reasonable time? If
  not, drop from Phase 1.
- **How to handle the "convincing samples" / few-shot
  persuasion prompts** that appear in the ReConcile paper.
  These are experiment-spec-layer concerns (prompt templates),
  not protocol IR concerns, but they affect comparability of
  replications.
- **Concrete dollar ceiling for Phase 1.** Should be set
  against the pinned pricing anchors before kickoff.
- **Price-arbitrage ablation.** If Phase 1 shows D beating D',
  decide whether a pinned-price-point follow-on is worth
  running to separate lineage diversity from price arbitrage.


## Validation status

This document has been through two rounds of preliminary
feedback from Codex (`mcs-coord`) and Gemini (`mcs-coord-gemini`)
on 2026-04-14. The current revision (third pass, same day)
folds in the substantive points from both rounds.

**From the first round** (converged):

- Condition B's selector needed to be held constant with the
  multi-model conditions. (Addressed structurally by scoping
  Phase 1 to executable scoring.)
- D' (homogeneous ReConcile) added as a heterogeneity-comparison
  control inside the D family.
- K (identity blinding) locked as fixed default.
- Compute unit switched to US dollars.
- Adversarial debate deferred.

**From the first round** (project-originated, not from reviewers
but interacted with their concerns): Phase 1 scope narrowed to
executable scoring only (walk-before-run).

**From the second round** (substantive):

- **Selector-as-oracle flaw (Gemini):** the second-pass draft
  used executable scoring as the internal selector, which
  turns B into Pass@N and mechanically disadvantages
  consensus-building protocols. Fixed: internal selectors are
  now part of each protocol's definition, non-oracle
  (majority vote, peer-LLM judgment, or protocol-native
  aggregation), counting toward the dollar budget. Executable
  scoring is the final evaluator only.
- **Statistical-plan trap (Gemini):** pooling strata for the
  primary test averages opposing threshold effects to null.
  Fixed: the primary pre-registered test is now the Protocol
  × Stratum interaction, with stratified estimates as
  pre-specified detail and the pooled average as secondary
  descriptive summary. Fallback to the middle band alone if
  power is too thin for the interaction.
- **Overreaching isolation claims (Codex):** D' → C and D → E
  were described as isolating comparisons, but each changes
  multiple things. Fixed: those are now described as
  family-level screen comparisons, not isolations. D' → D is
  still the heterogeneity comparison but is described as
  isolating "heterogeneous pool composition within a fixed
  protocol family under market prices" — not lineage diversity
  in a pure sense, because of price arbitrage.
- **Tie-breaking and partial-credit policy (Codex):** now
  specified in the Scoring section.
- **Internal calls count toward the budget (Codex):** now
  explicitly stated.

Before promotion to `experimental-design.md`, this revision
still needs:

- Third-pass review from Codex and Gemini against the latest
  matrix — confirmation that the substantive fixes from round
  two actually resolve the issues they flagged.
- Cross-check against `protocol-inventory.md` that no
  load-bearing axis was dropped.
- Dollar cost estimate for the full Phase 1 matrix at the
  pinned pricing anchors.
- Sign-off that the IR is expressive enough to encode A, B,
  C, D, D', and E.
