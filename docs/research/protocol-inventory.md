# Protocol Inventory

Working inventory of multi-model collaboration patterns to consider
for the study. This document is intentionally broad and not yet culled.
Its job in the current phase is to preserve candidate protocol ideas,
surface structural commonalities, and help drive a later literature
search. It is not yet a final design document.


## Semi-formal notation

A notation to make the patterns comparable and to surface
generalizations. Semi-formal: more rigorous than prose, less rigorous
than a language with precise semantics. Expected to evolve.


### Types

```
Q       task / query
        The original problem statement or user request.

P       pre-response artifact
        Anything produced before a candidate answer exists that is meant
        to guide later generation. Includes:
        - rewritten prompts
        - decompositions into sub-problems
        - plans
        - rubrics
        - strategy recommendations
        - routing recommendations

R       response / draft
        A candidate answer. Includes original generations, revisions,
        and fused responses. The key property: an R is what ultimately
        gets judged or delivered.

F       feedback
        Information about an R or P that is not itself an R. Includes:
        - free-form critique
        - structured flags
        - confidence scores
        - rebuttals
        - synthesized meta-feedback
        - judgments about review quality

S       state / transcript / shared context
        Interaction state that accumulates across turns. Includes:
        - dialogue history
        - debate transcript
        - blackboard / shared workspace state
        - step-by-step search state

D       decision
        A verdict, score, ranking, route, or selection. Examples:
        {pass, fail}, chosen index, pairwise winner, escalate / do not
        escalate.

A       action / trajectory artifact
        Multi-step actions and state transitions in an environment.
        Mostly relevant for later agentic-oversight extensions.
```

Why split `Q` and `P`:

- A raw task, a rewritten prompt, and a plan all influence generation,
  but they play different roles.
- The distinction matters if we later want protocol configs that say
  "use planning but not prompt rewriting" or "review the plan before
  execution."

Why split `R`, `F`, and `D`:

- A response is an answer candidate.
- Feedback is information about an answer or plan.
- A decision is a selection or verdict.

Keeping these separate makes "review of review" visibly different from
"review of answer," and makes routing / judging distinct from revision.


### Primitives (typed)

These are not meant to be minimal in the formal-methods sense. They are
meant to be useful building blocks for describing real protocol families.

```
M_gen       : X -> R             generate a response
                                  where X is typically Q, P, or (Q, P)

M_plan      : Q -> P             produce a plan / rubric / strategy
M_rewrite   : Q -> P             rewrite or improve the task framing
M_decomp    : Q -> [P]           decompose task into sub-problems
M_route     : Q -> D             choose model / protocol / branch

M_review_R  : R -> F             review a response
M_review_P  : P -> F             review a plan or pre-response artifact
M_review_F  : F -> F             review feedback (second-order review)

M_flag      : R -> F             constrained review: location + label
M_score     : R -> F             score / confidence as feedback
M_meta      : [F] -> F           synthesize or filter multiple feedback items

M_edit      : R x F -> R         revise a response from feedback
M_edit_P    : P x F -> P         revise a plan from feedback

M_select    : [R] -> D           choose among existing candidates
M_select_F  : [R] x [F] -> D     choose among candidates using reviews or scores
M_judge     : R -> D             evaluate or score a response
M_judge_S   : S -> D             evaluate a transcript / shared state
M_verify    : R -> D             verify / execute / test
M_fuse      : [R] -> R           synthesize a new response from candidates
M_review_A  : A -> F             review an action trace / trajectory
M_audit     : D x X -> F         audit a prior decision against evidence X

M_update    : S x X -> S         update shared state / transcript
M_step      : S -> R | D | F     produce a next-step proposal, decision,
                                  or critique conditioned on state
```

`M_select` vs `M_fuse`:

- `M_select` chooses one of the existing candidates.
- `M_fuse` generates a new response from multiple candidates.

Both operate over `[R]`, but the distinction matters experimentally:
selection is usually simpler and cheaper; fusion is more expressive and
more likely to blur attribution.


### Annotations

```
M(x; fresh)             fresh context (no history)
M(x; s)                 conditioned on accumulated state / transcript s
Mi, Mj  where i != j    different model lineages
Mi, Mi'                 same lineage, different instance / size
blind                   actor does not know source model identity
```


### Composition

```
f . g                   sequential: output of g feeds f
f || g                  parallel: f and g on same input independently
f^n                     apply f n times
if d then f else g      conditional branch on decision d
```


## Orders and timing

Two distinctions are worth keeping separate.

### Pre-response vs post-response

- **Pre-response** acts on `Q` or `P` before any candidate answer exists.
  Examples: planning, decomposition, routing, prompt rewrite, strategy
  elicitation.
- **Post-response** acts on `R`, `F`, or `D` after at least one answer
  candidate exists. Examples: critique, revision, judging, debate,
  selection.

### Oversight order

Order is best understood in terms of the highest-order artifact being
operated on, not just the depth of one operator.

- **Order 0:** act on `Q` or `P`
  Examples: planning, decomposition, prompt rewrite, plan review.
- **Order 1:** act on `R`
  Examples: critique of answer, answer selection, verification,
  revision from critique.
- **Order 2:** act on `F` or `D` about an answer
  Examples: review of review, meta-review, judging judges.
- **Order 3+:** act on meta-feedback, protocol traces, or judge process
  artifacts
  Examples: auditing debate dynamics, reviewing whether a judge was
  itself misled, oversight of the oversight process.

This makes the following distinctions explicit:

- `M_review_R : R -> F` is first-order review.
- `M_review_F : F -> F` is second-order review.
- `M_review_P : P -> F` is zeroth-order oversight, because it reviews a
  pre-response artifact.


## Protocol variants

These describe what models actually do: the pipeline shape. The list is
intentionally broad and includes plausible competitors, adjacent design
patterns, and mechanisms that may later be ruled out.


### Generation and selection

```
1.  M_gen(q) -> r
    one-shot baseline

2.  d = M_select(M_gen(q) || M_gen(q) || ... || M_gen(q))
    best-of-N / self-consistency-style baseline:
    homogeneous parallel generation, choose one existing candidate

3.  d = M_select(M1_gen(q) || M2_gen(q) || M3_gen(q))
    heterogeneous parallel generation, choose one existing candidate

4.  M_fuse(M1_gen(q) || M2_gen(q) || ... || Mn_gen(q)) -> r
    parallel generation, then synthesize a new response from candidates

5.  d = vote(M1_gen(q) || M2_gen(q) || ... || Mn_gen(q))
    majority-vote variant rather than judge-based selection

6.  diverse_subset = diversify(M1_gen(q) || ... || Mn_gen(q));
    d = M_select(diverse_subset)
    diversity-filtered selection: keep a diverse subset before final
    choice rather than selecting directly from the full set
```


### Routing and cascading

```
7.  d = M_route(q);  Mi_gen(q) -> r
    routing: classify query, dispatch to one model, only one generates

8.  M_weak_gen(q) -> r;
    score = M_score(r);
    if score < threshold: M_strong_gen(q) -> r'
    cascading: cheap model tries first, escalate to stronger model on
    low confidence

9.  d = M_route(q);  execute(protocol_d)
    protocol routing: choose among whole pipeline families, not just
    among models
```


### Pre-response

```
10. M_rewrite(q) -> p;  M_gen(q, p) -> r
    prompt critique / rewrite before generation

11. M_decomp(q) -> [p1..pk];
    ri = M_gen(q, pi);
    M_fuse(r1..rk) -> r
    prompt decomposition: split into sub-problems, answer parts,
    synthesize

12. M_plan(q) -> p;  M_gen(q, p) -> r
    plan-then-execute

13. M_plan(q) -> p;  f = M_review_P(p);  p' = M_edit_P(p, f);  M_gen(q, p') -> r
    plan -> critique plan -> revise plan -> execute

14. M_plan(q) -> p
    strategy elicitation / diagnostics:
    ask a model how the task should be attacked before any answer is
    attempted

15. M_plan(q) -> [p1..pn];
    r1 = M_gen(q, p1; s0);
    r2 = M_gen(q, p2; s0 + r1);
    ...
    decomposed strategy execution with explicit state accumulation
```


### Post-response review and revision

```
16. ri = Mi_gen(q);
    fi = Mj_review_R(ri; fresh, blind);
    r'i = M_edit(ri, fi);
    d = M_select(r'1..r'n)
    write -> blind critique (fresh context) -> revise -> select

17. ri = Mi_gen(q);
    fi = Mj_flag(ri; fresh, blind);
    r'i = M_edit(ri, fi);
    d = M_select(r'1..r'n)
    flag-only variant of critique -> revise -> select

18. ri = Mi_gen(q);
    fi = Mj_review_R(ri);
    f* = M_meta(f1..fn);
    r'i = M_edit(ri, f*);
    d = M_select(r'1..r'n)
    hierarchical review:
    writers -> reviewers -> meta-reviewer -> revision -> select

19. ri = Mi_gen(q);
    fi = Mj_review_R(ri);
    d = M_select_F(r1..rn, f1..fn)
    review informs selection but not revision

20. r = Mi_gen(q);
    if M_verify(r) = pass -> accept;
    else f = M_review_R(r) -> ... -> r'
    execution-gated review: review only on verifier failure
```


### Debate, discussion, and transcript-mediated interaction

```
21. s1 = M_update(s0, M1_gen(q));
    s2 = M_update(s1, M2_rebut(s1));
    s3 = M_update(s2, M1_rebut(s2));
    ...
    d = M_judge_S(s_final)
    adversarial debate through a shared transcript

22. s1 = M_update(s0, M1_review(q));
    s2 = M_update(s1, M2_complement(s1));
    ...
    d = M_judge_S(s_final)
    collaborative discussion / complementarity rather than adversarial
    rebuttal

23. ri = Mi_gen(q; s0 + rj)
    MoA-style "collaborativeness":
    generate while seeing other models' outputs, without requiring an
    explicit review framing

24. shared state s evolves as agents choose when to contribute:
    s' = M_update(s, contribution_i)
    blackboard / shared workspace coordination with no fixed topology
```


### Higher-order

```
25. f = M_review_R(r);  f' = M_review_F(f)
    review of review

26. f* = M_meta(f1..fn)
    meta-review: synthesize/filter N pieces of feedback into one

27. d1 = M_judge(r);  f = M_audit(d1, r);  d2 = reconcile(d1, f)
    judging the judge / second-order adjudication

28. apply a pattern recursively to its own outputs
    examples:
    - plan -> critique plan -> revise plan -> execute
    - response -> critique -> critique the critique -> revise
    - judge -> audit judge -> escalate
```


### Step-level and search-mediated

```
29. At each reasoning step i:
      candidates_i = M1_step(si) || M2_step(si) || ...
      si+1 = search(candidates_i, si)     [e.g. beam, MCTS, verifier-guided]
    step-level ensemble: select next moves repeatedly rather than
    selecting only among complete responses

30. At each step:
      propose -> verify -> prune -> continue
    search / verification loop inside generation rather than only at the
    end
```


### Conditional and adaptive

```
31. if confidence(d) < threshold -> escalate to J2 or human
    escalation in the judge layer

32. if task_type = coding -> protocol_A
    else if task_type = open-ended -> protocol_B
    task-adaptive protocol choice

33. if disagreement(reviewers) > threshold -> add another reviewer
    adaptive reviewer allocation based on disagreement

34. if cost budget remains and verifier still fails -> continue rounds
    budget-aware adaptive depth
```


### Agentic / trajectory-oriented

These are not central to Phase 1, but they are worth preserving in the
inventory because they are likely relevant to the later literature
search.

```
35. observe action trajectory a : A;  M_review_A(a) -> f
    review a multi-step plan or action trace rather than a single answer

36. M_plan(q) -> p : P;  execute(p) -> a : A;  M_review_A(a) -> f
    oversight of execution against the original plan

37. at each environment step:
      propose action -> review action -> execute / block
    online agentic oversight
```


## Structural variables

Independent knobs that can be varied within many protocols above.

```
A.  Lineage diversity        cross-family vs same-family
B.  Interaction framing      collaborative vs adversarial
C.  Critique format          free-form vs structured flags vs flag-only
D.  Round count              0, 1, or n review / revision passes
E.  Session context          fresh vs same-session continuation
F.  Selection rule           majority vote / single judge / judge panel / verifier
G.  Information regime       final answers only / process traces / reference-guided
H.  Capability gap           weak reviewing strong / peer / strong reviewing weak
I.  Task type                verifiable vs open-ended vs agentic
J.  Confidence weighting     equal weight vs reported confidence
K.  Identity blinding        blind review vs identity-aware review
L.  Judgment format          pairwise comparison vs pointwise scoring
M.  Ensemble granularity     response-level / step-level / span-level / token-level
N.  Communication content    decisions / flags / full critiques / traces / counterfactuals
O.  Candidate combination    select existing vs fuse new answer
P.  Topology                 fixed graph vs adaptive graph vs blackboard
Q.  Trigger policy           always-on vs verifier-gated vs disagreement-gated
R.  Allocation policy        fixed reviewer count vs adaptive reviewer count
S.  Deliverable type         final answer only vs answer + rationale vs answer + audit trail
```

Token-level and span-level ensemble (M) often require logit access or
fine-grained decoding control, so they may not be feasible with API
models in Phase 1.


## Observations from the notation

1. **Pre-response vs post-response is about the artifact being acted on.**
   `M_rewrite(q) -> p` and `M_review_R(r) -> f` are structurally
   parallel, but they intervene at different points in the pipeline.

2. **Order is artifact depth, not merely repetition count.**
   Reviewing a response (`R -> F`) and reviewing feedback (`F -> F`) are
   both called "review" in prose, but they are different operations.

3. **`Q` and `P` should stay separate.**
   A raw task, a rewritten prompt, and a plan can all feed generation,
   but they are not interchangeable analytically.

4. **Flag-only is mainly an output constraint, not a wholly separate
   family.**
   It restricts the codomain of review, but that constraint may matter
   empirically enough to deserve dedicated conditions.

5. **Session context is an annotation, not a protocol family.**
   Many operations can be run fresh or in accumulated context.

6. **Hierarchical review decomposes cleanly into review + meta-review +
   edit.**
   That means it should usually be thought of as a composite pattern,
   not a primitive.

7. **Selection and fusion are a genuine fork.**
   Both aggregate multiple candidates, but they behave differently and
   should likely be compared explicitly rather than treated as minor
   variants.

8. **Conditional patterns are structurally different from fixed-topology
   pipelines.**
   In conditional patterns, the topology depends on intermediate
   results. That matters for both implementation and fairness of
   compute-matching.

9. **Routing and cascading are real competitors.**
   They do not rely on multi-model joint reasoning, but they may capture
   much of the practical benefit at lower cost.

10. **Transcript-mediated interaction needs an explicit `S` type.**
    Debate, collaborative discussion, MoA-style conditioning, and
    blackboard protocols are awkward to express if context is only an
    annotation rather than a first-class artifact.

11. **Step-level methods break the `q -> r` atomicity assumption.**
    Most other patterns treat response generation as one unit; these
    intervene inside generation.

12. **The inventory now includes both central candidates and
    literature-search bait.**
    Some patterns are probably poor Phase 1 experiments but still worth
    retaining because they point to adjacent literatures or useful
    negative controls.


## Not yet cleanly placed

Patterns that still strain the notation or likely need a more explicit
state-machine treatment:

- **Dynamic topology generation:** a model or learned controller chooses
  the communication graph per query.

- **Sensitivity sharing / Ripple Effect:** agents share conditional
  counterfactuals such as "I would switch if X changed."

- **Large-population swarm protocols:** many-agent voting or market-like
  mechanisms designed for dozens or hundreds of agents rather than a
  small 2-3 model regime.

- **Token-level consensus decoding:** interesting in principle, but
  probably outside the practical API-based scope of Phase 1.


## Working takeaway

The inventory now spans:

- direct generation baselines
- generation plus selection
- pre-response interventions
- post-response critique and revision
- hierarchical and higher-order oversight
- transcript-mediated discussion
- search / step-level methods
- conditional / adaptive policies
- early agentic-oversight extensions

That is intentionally broader than the likely first experiment matrix.
The purpose at this stage is to preserve the design space in a form that
supports both later culling and a more systematic literature review.
