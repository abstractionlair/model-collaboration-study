# Human Validation Notes

**STATUS: DRAFT — Incomplete.** These notes capture practical human
validation ideas from the exploratory conversations. They are not yet a
final annotation plan.

---

## Why This Exists

The exploratory conversations converged on a clear point: frontier
LLM-as-judge can make an early study feasible, but it is not a full
replacement for human ground truth. Human review is still needed for:

- calibration of judge reliability
- auditing surprising or high-impact outcomes
- checking for systematic blind spots in the automated pipeline
- making later frontier-scale results more credible


## Suggested Staged Strategy

The conversations repeatedly pointed toward a staged path rather than
trying to fund full human validation from the start:

1. **Automated first pass**
   Run the initial API-based study with strong judge discipline,
   execution-based scoring where possible, and a modest audited slice.
2. **Preliminary artifact**
   Treat the automated result as a legitimate preliminary contribution if
   it is compute-matched and methodologically careful.
3. **Expanded human validation**
   Use the preliminary result to justify access to stronger annotation
   resources, whether through funding, institutional affiliation, or a
   later paper stage.

This is partly a research strategy point and partly a resource reality:
independent researchers typically do not have built-in annotator pools.


## What To Send To Humans

Human review seems most valuable on:

- close pairwise calls
- outputs where different judges disagree
- cases where execution and model judgment conflict
- examples that drive headline results
- open-ended helpfulness tasks where ambiguity is structurally higher
- a random calibration slice for base-rate monitoring

The conversations suggested that this does not need to cover the entire
dataset. A targeted subset can still materially improve confidence in
the automated pipeline.


## Scale Estimates Mentioned In Conversation

The exploratory notes suggested something like:

- **5-10% audited subset** for ongoing calibration in an automated study
- **Roughly 200-500 human judgments** for a stronger validation pass on a
  subset of outputs, depending on task complexity and annotation design

These are not final recommendations, only rough planning anchors.


## Potential Sources Of Human Review

The conversations mentioned three broad paths:

- **Paid annotation vendors** such as Surge AI or Scale AI. Estimated cost for a moderate validation slice (200-500 judgments) is on the order of **$2-5K USD**.
- **Direct contractors** hired through marketplaces such as Upwork.
- **Institutional access** through a lab, fellowship, startup, or academic collaboration (e.g., **SPAR, Anthropic Fellows, or MATS alumni orgs**). These institutions provide the built-in annotator infrastructure that independent researchers typically lack.


## Annotation Design Considerations

- Use pairwise comparisons where possible rather than vague scalar scores.
- Keep rubrics short and concrete.
- Separate objective checks from preference-like judgments.
- Blind model identities.
- Randomize answer order.
- Include an adjudication path for ambiguous items rather than forcing
  every case into a single crisp label.


## Open Questions

- What is the minimum audited slice needed to make the automated study
  credible?
- Which task buckets most need human validation versus executable or
  model-based grading?
- Should human review focus on final answers only, or also inspect
  critique traces and revisions?
- At what point does stronger human validation become necessary for
  publishability rather than merely desirable?


## Working Takeaway

Human validation should be treated as a staged strengthening move, not
as an all-or-nothing prerequisite. The likely practical path is:
automated API-first study, modest audit slice, then larger human
validation once the early results justify the cost.
