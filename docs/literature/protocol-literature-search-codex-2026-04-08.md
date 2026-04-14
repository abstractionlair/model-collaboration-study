# Protocol Literature Search (Codex)

**Date:** 2026-04-08  
**Searcher:** Codex / OpenAI  
**Purpose:** Candidate literature relevant to the protocol inventory in
[docs/research/protocol-inventory.md](/home/claude/projects/model-collaboration-study/docs/research/protocol-inventory.md),
plus related notes in `tmp/` and current draft literature notes.

This is a search artifact, not yet a deduplicated synthesis. It is
intended to be merged with findings from other models before gaps are
assessed.


## Search Focus

The search targeted literature relevant to these protocol buckets:

- Generation + selection baselines
- Heterogeneity / same-family vs cross-family aggregation
- Critique / review / revision
- Hierarchical and meta-review structures
- Debate and collaborative vs adversarial interaction
- Pre-response planning / prompt rewriting / decomposition
- Session / round effects
- LLM-as-judge design, bias, and reference-guided judging
- Scalable oversight framing


## High-Priority Papers

These look most central to the current research direction.

1. [AI Safety via Debate](https://arxiv.org/abs/1805.00899)  
   Irving, Christiano, Amodei, 2018.  
   Foundational oversight framing. Important as the original debate
   anchor even though the project is now broader than debate.

2. [On Scalable Oversight with Weak LLMs Judging Strong LLMs](https://arxiv.org/abs/2407.04622)  
   Kenton et al., 2024.  
   Best direct match for scalable oversight with weaker judges and
   stronger agents. Compares debate, consultancy, and direct QA across
   several task types.

3. [Debate or Vote: Which Yields Better Decisions in Multi-Agent Large Language Models?](https://openreview.net/forum?id=iUjGNJzrF1)  
   Choi, Zhu, Li, NeurIPS 2025.  
   Strong match for the "best-of-N discipline" and the question of
   whether debate adds much beyond aggregation.

4. [Towards Scalable Oversight with Collaborative Multi-Agent Debate in Error Detection](https://openreview.net/forum?id=W6qSjvTQMW)  
   Chen et al., ICLR 2026 submission.  
   Strongest hit for collaborative vs competitive framing in an
   oversight-like setting. Very relevant to the "collaborative review vs
   adversarial debate" axis.

5. [Scaling Laws For Scalable Oversight](https://openreview.net/forum?id=u1j6RqH8nM)  
   Engels, Baek, Kantamneni, Tegmark, NeurIPS 2025.  
   Relevant for capability-gap arguments and the broader claim that
   oversight success depends on task type and capability mismatch.

6. [Self-Consistency Improves Chain of Thought Reasoning in Language Models](https://openreview.net/forum?id=1PL1NIMMrw)  
   Wang et al., ICLR 2023.  
   Mandatory baseline reference for generate-then-select.

7. [Large Language Models Cannot Self-Correct Reasoning Yet](https://openreview.net/forum?id=IkmD3fKBPQ)  
   Huang et al., ICLR 2024.  
   Important negative baseline on intrinsic self-correction without
   external feedback.

8. [CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing](https://openreview.net/forum?id=Sx038qxjek)  
   Gou et al., ICLR 2024.  
   Important contrast case showing that self-correction becomes more
   plausible with external feedback.

9. [ReConcile: Round-Table Conference Improves Reasoning via Consensus among Diverse LLMs](https://openreview.net/forum?id=Yol6nUVIJD)  
   Chen, Saha, Bansal, ACL 2024 / earlier OpenReview submission.  
   Strong hit for heterogeneous discussion, confidence-weighted voting,
   and multi-round consensus.

10. [MARS: Toward More Efficient Multi-agent Collaboration for LLM Reasoning](https://openreview.net/forum?id=UWRfA2eWKE)  
    Wang et al., ICLR 2026 submission.  
    Strong hit for hierarchical author-reviewer-meta-reviewer topology
    and efficiency claims.


## Generation, Selection, and Aggregation

- [Self-Consistency Improves Chain of Thought Reasoning in Language Models](https://openreview.net/forum?id=1PL1NIMMrw)  
  Wang et al., ICLR 2023.  
  Canonical generate-multiple-then-select baseline.

- [Mixture-of-Agents Enhances Large Language Model Capabilities](https://arxiv.org/abs/2406.04692)  
  Wang, Wang, Athiwaratkun, Zhang, Zou, 2024.  
  Important for MoA-style layered aggregation and for the empirical
  claim that models can improve when conditioned on other models'
  outputs.

- [Rethinking Mixture-of-Agents: Is Mixing Different Large Language Models Beneficial?](https://openreview.net/forum?id=K6WwK8URlV)  
  Li, Lin, Xia, Jin, TMLR 2026.  
  Very relevant to the distinction between heterogeneity and simply
  aggregating many outputs from the best single model. Useful for
  tempering claims about cross-lineage gains.

- [Debate or Vote: Which Yields Better Decisions in Multi-Agent Large Language Models?](https://openreview.net/forum?id=iUjGNJzrF1)  
  Choi, Zhu, Li, NeurIPS 2025.  
  Strong reference for the claim that voting may explain much of the
  gains attributed to richer interaction.


## Critique, Review, Revision, Hierarchy

- [CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing](https://openreview.net/forum?id=Sx038qxjek)  
  Gou et al., ICLR 2024.  
  Important example of review / critique improving outputs when backed
  by external validation.

- [Large Language Models Cannot Self-Correct Reasoning Yet](https://openreview.net/forum?id=IkmD3fKBPQ)  
  Huang et al., ICLR 2024.  
  Important counterweight to optimistic review / revise claims.

- [ReConcile: Round-Table Conference Improves Reasoning via Consensus among Diverse LLMs](https://openreview.net/forum?id=Yol6nUVIJD)  
  Chen, Saha, Bansal, ACL 2024 / OpenReview 2023 submission.  
  Useful for diverse-agent discussion and confidence-weighted voting.

- [MARS: Toward More Efficient Multi-agent Collaboration for LLM Reasoning](https://openreview.net/forum?id=UWRfA2eWKE)  
  Wang et al., ICLR 2026 submission.  
  Particularly relevant to hierarchical review with a meta-reviewer.

- [PRD: Peer Rank and Discussion Improve Large Language Model based Evaluations](https://openreview.net/forum?id=YVD1QqWRaj)  
  Li, Patel, Du, TMLR 2024.  
  Not a generation protocol paper, but highly relevant to judge panels,
  peer discussion, and aggregation of evaluator opinions.


## Debate and Collaborative vs Adversarial Framing

- [AI Safety via Debate](https://arxiv.org/abs/1805.00899)  
  Irving, Christiano, Amodei, 2018.  
  Foundational framing.

- [On Scalable Oversight with Weak LLMs Judging Strong LLMs](https://arxiv.org/abs/2407.04622)  
  Kenton et al., 2024.  
  Strong direct empirical reference for debate / consultancy / direct QA.

- [Debate or Vote: Which Yields Better Decisions in Multi-Agent Large Language Models?](https://openreview.net/forum?id=iUjGNJzrF1)  
  Choi, Zhu, Li, NeurIPS 2025.  
  Important for disentangling aggregation from interaction.

- [Towards Scalable Oversight with Collaborative Multi-Agent Debate in Error Detection](https://openreview.net/forum?id=W6qSjvTQMW)  
  Chen et al., ICLR 2026 submission.  
  Strongest direct hit for collaborative vs competitive debate in an
  oversight-flavored error-detection setup.

- [Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate](https://openreview.net/forum?id=QAwaaLJNCk)  
  Liang et al., EMNLP 2024.  
  Classic MAD-style reference. More about debate as a general reasoning
  mechanism than oversight specifically.


## Pre-Response Planning, Prompt Editing, and Decomposition

- [Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning by Large Language Models](https://aclanthology.org/2023.acl-long.147/)  
  Wang et al., ACL 2023.  
  Strong direct match for pre-response planning and decomposition.

- [Self-Polish: Enhance Reasoning in Large Language Models via Problem Refinement](https://aclanthology.org/2023.findings-emnlp.762/)  
  Xi et al., EMNLP Findings 2023.  
  Strong match for rewriting / refining the problem before generation.

- [Tree of Thoughts: Deliberate Problem Solving with Large Language Models](https://proceedings.neurips.cc/paper_files/paper/2023/hash/271db9922b8d1f4dd7aaef84ed5ac703-Abstract-Conference.html)  
  Yao et al., NeurIPS 2023.  
  Relevant to step-level search, structured decomposition, and
  non-atomic generation.

- [Evoke: Evoking Critical Thinking Abilities in LLMs via Reviewer-Author Prompt Editing](https://openreview.net/forum?id=OXv0zQ1umU)  
  Hu et al., ICLR 2024.  
  Mentioned in prior discussion as relevant to prompt-review/edit loops.
  I have not independently verified its exact relevance in detail yet.


## Session / Round Effects

- [Cross-Context Review: Improving LLM Output Quality by Separating Production and Review Sessions](https://arxiv.org/abs/2603.12123)  
  Song, 2026.  
  Strong direct match for the "fresh context vs same-session" variable.

- [More Rounds, More Noise: Why Multi-Turn Review Fails to Improve Cross-Context Verification](https://arxiv.org/abs/2603.16244)  
  Song, 2026.  
  Strong direct match for the "one round vs multiple rounds" variable.

These two papers look unusually well aligned with the protocol inventory,
especially the distinction between fresh-context review and repeated
review.


## Judge Design, Bias, and Multi-Judge Aggregation

- [Can Large Language Models Be an Alternative to Human Evaluations?](https://aclanthology.org/2023.acl-long.870/)  
  Chiang, Lee, ACL 2023.  
  Early positive paper on LLM-as-evaluator.

- [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://papers.nips.cc/paper_files/paper/2023/hash/91f18a1287b398d378ef22505bf41832-Abstract-Datasets_and_Benchmarks.html)  
  Zheng et al., NeurIPS 2023.  
  Core judge-design and bias reference.

- [Replacing Judges with Juries: Evaluating LLM Generations with a Panel of Diverse Models](https://arxiv.org/abs/2404.18796)  
  Verga et al., 2024.  
  Strong match for panel / jury judging. I did not get the official
  Anthology or OpenReview page in this pass, but the arXiv identifier was
  repeatedly corroborated in other sources.

- [LLM Evaluators Recognize and Favor Their Own Generations](https://proceedings.neurips.cc/paper_files/paper/2024/hash/7f1f0218e45f5414c79c0679633e47bc-Abstract-Conference.html)  
  Panickssery, Bowman, Feng, NeurIPS 2024.  
  Important for self-preference bias.

- [PRD: Peer Rank and Discussion Improve Large Language Model based Evaluations](https://openreview.net/forum?id=YVD1QqWRaj)  
  Li, Patel, Du, TMLR 2024.  
  Relevant to panel-style evaluation, peer discussion, and judge
  aggregation.

- [An Empirical Study of LLM-as-a-Judge for LLM Evaluation: Fine-tuned Judge Model is not a General Substitute for GPT-4](https://aclanthology.org/2025.findings-acl.306/)  
  Huang et al., ACL Findings 2025.  
  Good caution against assuming small fine-tuned judges are interchangeable
  with stronger frontier judges.

- [Reference-Guided Verdict: LLMs-as-Judges in Automatic Evaluation of Free-Form QA](https://aclanthology.org/2025.winlp-main.37/)  
  Badshah, Sajjad, WiNLP 2025.  
  Relevant to reference-guided judging and multi-judge setups.

- [Do Before You Judge: Self-Reference as a Pathway to Better LLM Evaluation](https://aclanthology.org/2025.findings-emnlp.1342/)  
  Lin et al., EMNLP Findings 2025.  
  Relevant to self-reference-guided judging and the broader question of
  when judgment ability tracks generation ability.


## Scalable Oversight Framing

- [AI Safety via Debate](https://arxiv.org/abs/1805.00899)
- [On Scalable Oversight with Weak LLMs Judging Strong LLMs](https://arxiv.org/abs/2407.04622)
- [Scaling Laws For Scalable Oversight](https://openreview.net/forum?id=u1j6RqH8nM)
- [Towards Scalable Oversight with Collaborative Multi-Agent Debate in Error Detection](https://openreview.net/forum?id=W6qSjvTQMW)

Together these seem to provide the cleanest current backbone for the
alignment / oversight framing, while the multi-agent collaboration
papers fill in the protocol-design side.


## Papers Mentioned Earlier But Not Yet Verified Cleanly In This Pass

These names came up in the repo notes, but I do not yet have a clean
primary-source confirmation sufficient to rely on them without another
pass.

- `EdgeJury`
- `ModelSwitch`
- `RMoA`
- `Multi-Agent Peer Review Collaboration`
- `LLM-PeerReview`
- `LLM Review`
- `faulty-agent resilience / hierarchical-structure paper`
- `routing benchmarks (2025)` as a specific paper rather than a general area

These may all be real and useful, but they need a more targeted search
before being treated as solid references.


## Apparent Gaps After This Pass

These still look weakly covered or absent in the literature found so far:

- Explicit testing of **flag-only vs explanation-heavy critique**
- Clean isolation of **training-lineage diversity** from other forms of
  heterogeneity
- Clean comparisons of **fresh-context review** outside the very recent
  Cross-Context Review line
- Direct application of these protocol families to **agentic oversight of
  multi-step plans / actions**
- Strong literature on **blackboard / shared-workspace** or
  **adaptive-topology** protocols in the small 2-3 model regime

These are only provisional "apparent gaps" pending merge with other
models' findings.


## Practical Read Order

If reading time is limited, I would start with:

1. Kenton et al. on scalable oversight with weak judges
2. Debate or Vote
3. ColMAD
4. Self-Consistency
5. ReConcile
6. MARS
7. Cross-Context Review
8. More Rounds, More Noise
9. Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena
10. Replacing Judges with Juries

Then move to:

- Self-Polish
- Plan-and-Solve
- CRITIC
- Self-MoA / Rethinking Mixture-of-Agents
- Reference-Guided Verdict
- Do Before You Judge


## Notes On Confidence

- Confidence is highest for papers linked through official venues such as
  ACL Anthology, OpenReview, NeurIPS proceedings, and direct arXiv IDs.
- Confidence is lowest for placeholder names inherited from earlier notes
  when I could not yet tie them to a clear primary source in this pass.
- Some recent 2026 items are still submissions or fresh arXiv preprints,
  so they are useful for coverage but should be treated accordingly.


## Additional Findings (Gemini CLI - April 2026)

Supplementary findings to be merged into the final synthesis.


### New High-Priority Papers & Frameworks

11. [Confidence Improves Self-Consistency in LLMs](https://aclanthology.org/2025.acl-long.147/)  
    Taubenfeld et al., ACL 2025.  
    Introduces **CISC (Confidence-Informed Self-Consistency)**. Found
    that weighting by self-reported P(True) achieves 40% efficiency gains
    over vanilla majority voting.

12. [Scaling LLM Inference with Optimized Sample Compute Allocation](https://arxiv.org/abs/2410.02731)  
    Zhang et al., NAACL 2025.  
    Introduces **OSCA**. Shows that mixed strategies (diverse models and
    temperatures) can outperform pure scaling by 25x-128x in compute
    efficiency for reasoning/coding.

13. [EdgeJury: A Truthful AI Council for Small Language Models](https://arxiv.org/abs/2511.08231)  
    2025/2026.  
    Detailed four-stage protocol (Role-Diverse Gen -> Anonymized Cross-Review ->
    Chairman Synthesis -> Consistency Verification) for high-truthfulness
    on edge-scale hardware.

14. [FindTheFlaws: Annotated Errors for Detecting Flawed Reasoning](https://aaai.org/papers/2026/findtheflaws)  
    AAAI 2026.  
    Strong evidence for the **"Detection vs. Explanation" gap**. Confirms
    that models often recognize *that* a solution is flawed while failing
    to locate or explain the specific flaw.


### Specific Findings on Existing Themes

**On Mixture-of-Agents (MoA) vs. Self-MoA:**
- [Self-MoA: Is Mixing Different Large Language Models Beneficial?](https://arxiv.org/abs/2501.12948)  
  Li et al. (Princeton), 2025.  
  Directly challenges Mixed-MoA. Reports that **Self-MoA outperforms
  Mixed-MoA by ~6.6% on AlpacaEval 2.0**, arguing that high-quality models
  are diluted by weaker proposers in heterogeneous pools.

**On "Flag don't explain":**
- [Are LLMs Better than Reported? Label Error Detection via Confidence](https://aclanthology.org/2025.findings-acl.102)  
  2025.  
  Corroborates that **binary flagging** based on confidence is often more
  reliable than generated explanations, which can be sycophantic or
  hallucinated.

**On RECONCILE & Consensus:**
- [ReConcile: Round-Table Conference Improves Reasoning](https://arxiv.org/abs/2309.13007)  
  Chen et al., ACL 2024.  
  Crucial for **confidence-weighted voting** and the use of
  "convincing human demonstrations" to improve multi-model discussion
  convergence.


### Emerging Patterns (2025-2026)

- **Precision Collapse in Multi-Turn Review:** Song et al. (2026) "More
  Rounds, More Noise" identifies that while multiple turns increase
  recall (catching more errors), they suffer from a **collapse in
  precision** as reviewers begin to hallucinate false positives.
- **Within-Question Discrimination (WQD):** Taubenfeld et al. (2025) argue
  that the ability to distinguish between two reasoning paths for the
  *same* question is more important for aggregation than overall model
  calibration.
- **Hierarchical Efficiency:** MARS and EdgeJury suggest that
  hierarchical "Author -> Reviewer -> Synthesizer" structures capture
  most of the value of dense interaction at a fraction of the token cost.


## Additional Reference (Blog Post)

- [The Mismanaged Geniuses Hypothesis](https://alexzhang13.github.io/blog/2026/mgh/)
  Alex L. Zhang, Zhening (Zed) Li, Omar Khattab, April 2026.
  Argues that frontier models are severely underutilized due to
  sub-optimal orchestration, not insufficient capability. The next
  capability leap comes from decomposition and self-management, not
  scaling. Key evidence: a 4B RLM achieves 100% on 1M-context task
  after RL training on 32K version. Directly relevant to the project's
  framing: if the bottleneck is management/orchestration, then protocol
  design variables are the lever. Connected to DSPy (same author,
  Khattab). Does not test multi-model collaboration specifically, but
  the decomposition-space concept maps to our pre-response protocol
  family (collaborative decomposition of Q into P before generation).


## Additional Findings (Claude - April 2026)

Supplementary findings from four parallel literature searches targeting
gaps in the existing coverage. Organized by protocol inventory category.
Papers already listed above are not repeated.


### Surveys and Taxonomies

- [Harnessing Multiple Large Language Models: A Survey on LLM Ensemble](https://arxiv.org/abs/2502.18036)
  Chen, Li, Chen et al., 2025.
  First systematic review of LLM ensembles. Taxonomy: ensemble-before,
  during, and after inference. Companion repo: Awesome-LLM-Ensemble.

- [Multi-Agent Collaboration Mechanisms: A Survey of LLMs](https://arxiv.org/abs/2501.06322)
  Tran et al., 2025.
  Five-dimension framework: actors, types (cooperation/competition/
  coopetition), structures, strategies, coordination protocols.

- [Agentic AI: Architectures, Taxonomies, and Evaluation of LLM Agents](https://arxiv.org/abs/2601.12560)
  Arunkumar, Gangadharan, Buyya, 2026.
  Unified taxonomy covering perception, planning, action, tool use,
  collaboration. Includes MCP and evaluation practices.

- [A Survey on Collaborative Mechanisms Between Large and Small Language Models](https://arxiv.org/abs/2505.07460)
  Chen et al., 2025.
  Taxonomy of LLM-SLM interaction: pipeline, routing, auxiliary,
  distillation, fusion.

- [Ensemble Learning for Large Language Models in Text and Code Generation: A Survey](https://arxiv.org/abs/2503.13505)
  Ashiga et al., 2025.
  Seven ensemble methods: weight merging, knowledge fusion, MoE,
  reward ensemble, output ensemble, routing, prompt augmentation.

- [Dynamic Model Routing and Cascading for Efficient LLM Inference: A Survey](https://arxiv.org/abs/2603.04445)
  Moslem & Kelleher, 2026.
  Systematic review of routing paradigms and cascading strategies.

- [A Survey on Collaborating Small and Large Language Models](https://arxiv.org/abs/2510.13890)
  Wang et al., 2025.
  Four-goal taxonomy: performance, cost, privacy, trustworthiness.

- [Large Language Model Agent: A Survey on Methodology, Applications and Challenges](https://arxiv.org/abs/2503.21460)
  2025. Methodology-centered taxonomy linking architecture,
  collaboration, and evolution.

- [A Survey on LLM-as-a-Judge](https://arxiv.org/abs/2411.15594)
  Gu et al., 2024. Published in The Innovation (Cell Press), 2026.
  Comprehensive: definition, classification, reliability strategies.

- [LLMs-as-Judges: A Comprehensive Survey on LLM-based Evaluation Methods](https://arxiv.org/abs/2412.05579)
  Li et al., 2024.
  Five perspectives: functionality, methodology, applications,
  meta-evaluation, limitations.

- [A Survey of Confidence Estimation and Calibration in Large Language Models](https://arxiv.org/abs/2311.08298)
  Geng et al., NAACL 2024.
  First comprehensive confidence calibration survey for LLMs.


### Routing and Cascading (new section)

- [RouteLLM: Learning to Route LLMs with Preference Data](https://arxiv.org/abs/2406.18665)
  Ong et al., ICLR 2025. [KEY]
  Trains routers on human preference data. 2x+ cost reduction, no
  quality loss. Strong open-source framework.

- [FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance](https://arxiv.org/abs/2305.05176)
  Chen, Zaharia, Zou, TMLR 2024. [KEY]
  LLM cascade: cheaper models first, escalate on low confidence.
  Matches GPT-4 at up to 98% cost reduction.

- [AutoMix: Automatically Mixing Language Models](https://arxiv.org/abs/2310.12963)
  Aggarwal, Madaan et al., NeurIPS 2024.
  Few-shot self-verification + POMDP router. 50%+ compute savings.

- [A Unified Approach to Routing and Cascading for LLMs](https://arxiv.org/abs/2410.10347)
  Dekoninck, Baader, Vechev, ICLR 2025.
  Provably optimal routing and cascading. Up to 14% on SWE-Bench.

- [Hybrid LLM: Cost-Efficient and Quality-Aware Query Routing](https://arxiv.org/abs/2404.14618)
  Ding et al., Microsoft, ICLR 2024.
  Difficulty-based routing. 40% cost savings.

- [Zooter: Routing to the Expert](https://arxiv.org/abs/2311.08692)
  Lu et al., NAACL 2024.
  Reward-distilled routing function.

- [FORC: Fly-Swat or Cannon?](https://arxiv.org/abs/2308.06077)
  Sakota et al., WSDM 2024.
  Two-step meta-model routing with cost optimization.

- [SelectLLM: Query-Aware Efficient Selection Algorithm](https://arxiv.org/abs/2408.08545)
  Maurya et al., ACL 2025 Findings.
  Multi-label: selects optimal subset of LLMs per query.

- [GraphRouter](https://arxiv.org/abs/2410.03834)
  Feng et al., ICLR 2025.
  GNN-based heterogeneous graph for LLM recommendation.

- [RouterDC](https://arxiv.org/abs/2409.19886)
  Chen et al., NeurIPS 2024.
  Dual contrastive learning for router training.

- [MixLLM: Dynamic Routing in Mixed Large Language Models](https://arxiv.org/abs/2502.18482)
  Wang et al., NAACL 2025.
  Contextual-bandit routing. 97.25% GPT-4 quality at 24% cost.

- [UniRoute: Universal Model Routing for Efficient LLM Inference](https://arxiv.org/abs/2502.08773)
  Jitkrittum et al., Google, 2025.
  Routes to previously unseen LLMs via feature vectors.

- [Harnessing the Power of Multiple Minds: Lessons Learned from LLM Routing](https://arxiv.org/abs/2405.00467)
  Srivatsa et al., ACL 2024 Workshop.
  Important negative result: routing not always feasible.

- [Eagle: Efficient Training-Free Router](https://arxiv.org/abs/2409.15518)
  Zhao et al., NeurIPS 2024 Workshop.
  ELO-based training-free routing. 100-200x faster updates.

- [Router-R1](https://arxiv.org/abs/2506.09033)
  Zhao et al., 2025.
  RL-trained router for multi-round routing and aggregation.

- [Rerouting LLM Routers](https://arxiv.org/abs/2501.01818)
  Shafran et al., COLM 2025.
  Adversarial robustness of routers. Defines control plane integrity.

- [RouterBench](https://arxiv.org/abs/2403.12031)
  Hu et al., 2024.
  First comprehensive routing benchmark, 405K+ inference outcomes.

- [Smoothie: Label Free Language Model Routing](https://arxiv.org/abs/2412.04692)
  Guha et al., NeurIPS 2024.
  Unsupervised routing via latent variable model. No labels needed.

- [RoBoN: Routed Online Best-of-n](https://arxiv.org/abs/2512.05542)
  2025.
  Training-free online routing across LLM portfolio.


### Response Fusion (new section)

- [LLM-Blender: Ensembling LLMs with Pairwise Ranking and Generative Fusion](https://arxiv.org/abs/2306.02561)
  Jiang, Ren, Lin, ACL 2023. [KEY]
  PairRanker + GenFuser. Seminal selection-then-regeneration paper.

- [URG: A Unified Ranking and Generation Method for Ensembling Language Models](https://aclanthology.org/2024.findings-acl.261/)
  Lv et al., ACL 2024 Findings.
  Joint ranking-generation eliminates error propagation.

- [FuseChat: Knowledge Fusion of Chat Models](https://arxiv.org/abs/2408.07990)
  Wan et al., EMNLP 2025.
  Weight-space fusion variant. FuseChat-7B outperforms larger baselines.


### Token-Level and Span-Level Ensemble (new section)

- [DeePEn: Ensemble Learning for Heterogeneous LLMs with Deep Parallel Collaboration](https://arxiv.org/abs/2404.12715)
  Huang et al., NeurIPS 2024 Spotlight.
  Training-free token-level via universal relative space.

- [FusionRoute: Token-Level LLM Collaboration](https://arxiv.org/abs/2601.05106)
  Xiong et al., 2025.
  Lightweight router selects expert + contributes logit correction.

- [PackLLM: Model Fusion at Test-Time via Perplexity Optimization](https://arxiv.org/abs/2404.11531)
  Mavromatis et al., 2024.
  Training-free weighted logit ensemble optimizing perplexity.

- [CITER: Collaborative Inference with Token-Level Routing](https://arxiv.org/abs/2502.01976)
  Zheng et al., COLM 2025.
  Routes critical tokens to LLM, non-critical to SLM.

- [Cool-Fusion: Fuse Large Language Models without Training](https://arxiv.org/abs/2407.19807)
  Liu et al., ACL 2025.
  Span-level ensemble. +17.4% on GSM8K from three source LLMs.

- [SweetSpan: Hit the Sweet Spot! Span-Level Ensemble](https://arxiv.org/abs/2409.18583)
  Xu et al., COLING 2025.
  Mutual perplexity-based span selection.

- [SpecFuse: Ensembling LLMs via Next-Segment Prediction](https://arxiv.org/abs/2412.07380)
  Lv et al., 2024.
  Speculative draft-then-verify at segment level with weight updates.

- [EVA: Bridging the Gap between Different Vocabularies for LLM Ensemble](https://arxiv.org/abs/2404.09492)
  Xu et al., NAACL 2024.
  Vocabulary mapping for fine-grained token-level ensemble.


### Pre-Response Planning and Decomposition (additions)

- [Least-to-Most Prompting](https://arxiv.org/abs/2205.10625)
  Zhou et al., ICLR 2023.
  Decomposes into simpler subproblems solved in sequence.

- [ReWOO: Decoupling Reasoning from Observations](https://arxiv.org/abs/2305.18323)
  Xu et al., 2023.
  Planner/Worker/Solver modules. 5x token efficiency.

- [HuggingGPT: Solving AI Tasks with ChatGPT and its Friends](https://arxiv.org/abs/2303.17580)
  Shen et al., NeurIPS 2023.
  Canonical orchestrator-worker with heterogeneous specialist models.

- [MetaGPT: Meta Programming for Multi-Agent Collaborative Framework](https://arxiv.org/abs/2308.00352)
  Hong et al., ICLR 2024.
  Encodes human SOPs into multi-agent collaboration.

- [ChatDev: Communicative Agents for Software Development](https://arxiv.org/abs/2307.07924)
  Qian et al., ACL 2024.
  Role-based chat chains for phased software development.

- [CAMEL: Communicative Agents for "Mind" Exploration](https://arxiv.org/abs/2303.17760)
  Li et al., NeurIPS 2023.
  Inception prompting for autonomous role-play cooperation.

- [LM2: A Simple Society of Language Models Solves Complex Reasoning](https://arxiv.org/abs/2404.02255)
  Juneja et al., EMNLP 2024.
  Decomposer/solver/verifier trained to coordinate. +8.1% on MATH.

- [Anthropic: Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
  2024.
  Orchestrator-workers pattern. Distinguishes workflows from agents.


### Prompt Rewriting and Meta-Prompting (new section)

- [APE: Large Language Models Are Human-Level Prompt Engineers](https://arxiv.org/abs/2211.01910)
  Zhou et al., ICLR 2023.
  LLM generates, scores, and selects candidate instructions.

- [Meta-Prompting: Enhancing Language Models with Task-Agnostic Scaffolding](https://arxiv.org/abs/2401.12954)
  Suzgun & Kalai, 2024.
  Single LLM as conductor delegating to expert instances. +17.1%.

- [OPRO: Large Language Models as Optimizers](https://arxiv.org/abs/2309.03409)
  Yang et al., DeepMind, 2023.
  LLMs iteratively optimize prompts. Up to +50% on Big-Bench Hard.

- [Self-Refine: Iterative Refinement with Self-Feedback](https://arxiv.org/abs/2303.17651)
  Madaan et al., NeurIPS 2023.
  Generate, self-critique, refine iteratively. ~20% average improvement.

- [PRomPTed: Rewriting Prompts for Instances with LLMs in the Loop](https://arxiv.org/abs/2310.02107)
  Saha et al., ACL 2024 Findings.
  Meta-LLM rewrites prompts per-instance. GPT-3.5 rewriting for GPT-4
  sometimes exceeds GPT-4 rewriting for itself.

- [EvoPrompt: Connecting LLMs with Evolutionary Algorithms](https://arxiv.org/abs/2309.08532)
  Guo et al., ICLR 2024.
  Evolutionary prompt optimization. Up to +25% on BIG-Bench Hard.

- [Promptbreeder: Self-Referential Self-Improvement via Prompt Evolution](https://arxiv.org/abs/2309.16797)
  Fernando et al., DeepMind, ICML 2024.
  Evolves both task-prompts and mutation-prompts.

- [DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines](https://arxiv.org/abs/2310.03714)
  Khattab et al., Stanford, 2023.
  Framework for automatic prompt optimization via compilation.


### Step-Level Ensemble and Tree Search (additions)

- [LATS: Language Agent Tree Search](https://arxiv.org/abs/2310.04406)
  Zhou et al., ICML 2024.
  MCTS with LLM-powered value functions and self-reflections.
  92.7% pass@1 on HumanEval with GPT-4.

- [MCTSr: Monte Carlo Tree Self-Refine](https://arxiv.org/abs/2406.07394)
  Zhang et al., 2024.
  MCTS + self-refinement. LLaMA-3 8B reaches GPT-4 level on math
  olympiad problems.

- [LE-MCTS: Ensembling LLMs with Process Reward-Guided Tree Search](https://arxiv.org/abs/2412.15797)
  Park et al., NAACL 2025. [KEY]
  Multi-model step-level ensemble. Models propose next-steps, PRM
  guides MCTS. +3.6% MATH, +4.3% MQA.

- [AB-MCTS: Adaptive Branching MCTS](https://arxiv.org/abs/2503.04412)
  Sakana AI, 2025. [KEY]
  Multi-frontier-model cooperation via MCTS. Adaptively balances
  depth vs width. 30%+ of ARC-AGI-2 test problems solved.

- [ReST-MCTS*: LLM Self-Training via Process Reward Guided Tree Search](https://arxiv.org/abs/2406.03816)
  Zhang et al., NeurIPS 2024.
  Process reward-guided search for self-training data collection.


### Process Reward Models and Verifier-Guided Search (new section)

- [Training Verifiers to Solve Math Word Problems](https://arxiv.org/abs/2110.14168)
  Cobbe et al., OpenAI, 2021. [KEY]
  Foundational verifier paper. Introduces GSM8K. Established the
  generate-then-verify paradigm.

- [Let's Verify Step by Step](https://arxiv.org/abs/2305.20050)
  Lightman et al., OpenAI, 2023. [KEY]
  Process supervision beats outcome supervision. Releases PRM800K.

- [Math-Shepherd: Verify and Reinforce LLMs Step-by-step without Human Annotations](https://arxiv.org/abs/2312.08935)
  Wang et al., ACL 2024.
  Auto-constructed process reward model. Avoids human annotation.

- [OmegaPRM](https://arxiv.org/abs/2406.06592)
  Google, 2024.
  Divide-and-conquer MCTS for process supervision data. Gemini Pro
  51% -> 69.4% on MATH500.

- [GenPRM: Scaling Test-Time Compute of Process Reward Models via Generative Reasoning](https://arxiv.org/abs/2504.00891)
  Zhao et al., AAAI 2026.
  Generative PRM with CoT + code verification. 1.5B GenPRM
  outperforms GPT-4o on ProcessBench.

- [Scaling LLM Test-Time Compute Optimally](https://arxiv.org/abs/2408.03314)
  Snell et al., Berkeley/DeepMind, 2024.
  Optimal strategy depends on prompt difficulty. Compute-optimal
  allocation matches 14x larger model.


### Newer Debate Work (additions to existing section)

- [Breaking Mental Set: Diverse Multi-Agent Debate (DMAD)](https://openreview.net/forum?id=t6QHYUOQL7)
  Liu et al., ICLR 2025.
  Agents use distinct reasoning strategies. Outperforms standard MAD.

- [Can LLM Agents Really Debate?](https://arxiv.org/abs/2511.07784)
  Wu et al., 2025.
  Intrinsic reasoning + group diversity dominate; structural choices
  matter little; groups suppress dissent.

- [Demystifying Multi-Agent Debate](https://arxiv.org/abs/2601.19921)
  Zhu et al., 2026.
  Vanilla MAD underperforms majority vote due to lacking initial
  diversity and calibrated confidence. Proposes diversity-aware
  initialization.

- [DynaDebate: Dynamic Path Generation](https://arxiv.org/abs/2601.05746)
  Li et al., 2026.
  Process-centric step-level auditing during debate.

- [Free-MAD: Consensus-Free Multi-Agent Debate](https://arxiv.org/abs/2509.11035)
  Cui et al., 2025.
  Score-based trajectory evaluation + anti-conformity mechanism.
  Better reasoning in a single debate round.

- [CortexDebate: Sparse Debating Graph](https://arxiv.org/abs/2507.03928)
  Sun et al., ACL 2025.
  Brain cortex-inspired sparse graph. McKinsey Trust Formula for
  credibility.

- [M3MAD-Bench](https://arxiv.org/abs/2601.02854)
  Li et al., 2026.
  Unified MAD benchmark across 5 domains, text and vision-language.

- [SWE-Debate: Competitive Multi-Agent Debate for Software Issue Resolution](https://arxiv.org/abs/2507.23348)
  Li et al., 2025.
  Fault propagation traces + three-round specialized debate. SOTA
  on SWE-bench.

- [Debate Helps Weak-to-Strong Generalization](https://arxiv.org/abs/2501.13124)
  Lang et al., AAAI 2025 Oral.
  Debate helps weak model extract trustworthy info from untrustworthy
  strong model.

- [Talk Isn't Always Cheap: Understanding Failure Modes in Multi-Agent Debate](https://arxiv.org/abs/2509.05396)
  Wynn et al., 2025.
  Debate can decrease accuracy even when stronger models outnumber
  weaker. Sycophancy and conformity as failure modes.

- [Debate4MATH: Fine-Grained Multi-Agent Debate](https://aclanthology.org/2025.findings-acl.862/)
  Zhang & Xiong, ACL 2025 Findings.
  46K debate-derived reasoning examples. Debate-based reward model.

- [Voting or Consensus? Decision-Making in Multi-Agent Debate](https://arxiv.org/abs/2502.19130)
  Kaesberg et al., ACL 2025 Findings.
  Voting improves reasoning (+13.2%), consensus improves knowledge
  (+2.8%). Task-type-dependent.

- [Diversity of Thought Elicits Stronger Reasoning](https://arxiv.org/abs/2410.12853)
  Hegazy, 2024.
  Diverse medium models (91%) beat GPT-4 on GSM-8K; three identical
  models reach only 82%.


### Higher-Order Oversight (new section)

- [Leveraging LLMs as Meta-Judges](https://arxiv.org/abs/2504.17087)
  Li et al., 2025.
  Three-stage meta-judge: rubric creation, multi-agent scoring,
  threshold filtering. +15.5% over raw judgments.

- [Know Thy Judge: On the Robustness Meta-Evaluation of LLM Safety Judges](https://arxiv.org/abs/2503.04474)
  Eiras et al., ICLR 2025 Workshop.
  LLM safety judges are brittle: small style changes cause large
  false negative jumps.

- [Judging the Judges: A Systematic Study of Position Bias](https://arxiv.org/abs/2406.07791)
  Shi et al., AACL 2025.
  150K+ evaluations. Bias varies by judge and task; quality gap
  affects bias more than length.

- [DeepReview: Improving LLM-based Paper Review](https://arxiv.org/abs/2503.08569)
  ACL 2025.
  Multi-stage framework. Trained 14B outperforms 70B reviewer.

- [ReViewGraph: Automatic Paper Reviewing via Heterogeneous Graph Reasoning](https://arxiv.org/abs/2511.08317)
  Li et al., AAAI 2026.
  Simulates reviewer-author debates, extracts opinion graph, GNN
  for decisions. +15.7%.


### Identity, Bias, and Blinding (new section)

- [When Identity Skews Debate: Anonymization for Bias-Reduced Multi-Agent Reasoning](https://arxiv.org/abs/2510.07517)
  Choi et al., 2025.
  First principled framework for sycophancy + self-bias in MAD.
  Formalizes as identity-weighted Bayesian updating. Proposes
  response anonymization.

- [Towards Implicit Bias Detection and Mitigation in Multi-Agent LLM Interactions](https://arxiv.org/abs/2410.02584)
  Borah & Mihalcea, EMNLP 2024 Findings.
  Biases escalate following multi-agent interactions.

- [An Empirical Study of Group Conformity in Multi-Agent Systems](https://arxiv.org/abs/2506.01332)
  Choi et al., ACL 2025 Findings.
  2500+ simulated debates. A single high-intelligence agent
  influences neutral agents more than a larger group of weaker ones.

- [Preference Leakage: A Contamination Problem in LLM-as-a-judge](https://arxiv.org/abs/2502.01534)
  Li et al., ICML 2025.
  Defines same-model, inheritance, same-family relatedness. Cross-
  family bias empirically confirmed. More pervasive than prior biases.

- [Self-Preference Bias in LLM-as-a-Judge](https://arxiv.org/abs/2410.21819)
  Wataoka et al., 2024.
  Root cause is perplexity: LLMs prefer lower-perplexity text
  regardless of whether self-generated.


### Communication Topology (new section)

- [G-Designer: Architecting Multi-agent Communication Topologies via GNNs](https://arxiv.org/abs/2410.11782)
  ICML 2025.
  Variational graph auto-encoder for task-adaptive topology design.

- [GoAgent: Group-of-Agents Communication Topology Generation](https://arxiv.org/abs/2603.19677)
  Chen et al., 2026.
  Groups as atomic units. Information bottleneck compression.
  93.84% accuracy, 17% fewer tokens.

- [ARG-Designer: Assemble Your Crew](https://arxiv.org/abs/2507.18224)
  Li et al., AAAI 2026 Oral.
  Autoregressive graph generation: determines agent count, selects
  roles, establishes links.

- [GTD: Dynamic Generation of Multi-LLM Communication Topologies](https://arxiv.org/abs/2510.07799)
  Jiang et al., 2025.
  Conditional discrete graph diffusion for topology synthesis.

- [Understanding Information Propagation Effects of Communication Topologies](https://arxiv.org/abs/2505.23352)
  Shen et al., EMNLP 2025.
  Moderately sparse topologies optimally balance error suppression
  and information diffusion.

- [Improving Multi-Agent Debate with Sparse Communication Topology](https://arxiv.org/abs/2406.11776)
  Li et al., EMNLP 2024 Findings.
  Sparse topologies achieve comparable performance at lower cost.

- [Rethinking Multi-Agent Intelligence Through Small-World Networks](https://arxiv.org/abs/2512.18094)
  Wang et al., 2025.
  Small-world connectivity stabilizes consensus. Uncertainty-guided
  rewiring between divergent agents.

- [Hear Both Sides: Diversity-Aware Message Retention](https://arxiv.org/abs/2603.20640)
  Nguyen et al., 2026.
  Selective message propagation keeping maximally disagreeing subset.


### Collaborative vs Adversarial Framing (additions)

- [MultiAgentBench: Evaluating Collaboration and Competition of LLM Agents](https://arxiv.org/abs/2503.01935)
  Zhu et al., ACL 2025.
  Cooperative and adversarial scenarios. Graph topology performs best.

- [Exploring Collaboration Mechanisms: A Social Psychology View](https://arxiv.org/abs/2310.02124)
  Zhang et al., ACL 2024.
  LLM agents exhibit conformity and consensus-building.

- [On the Resilience of Multi-Agent Collaboration with Faulty Agents](https://arxiv.org/abs/2408.00989)
  Huang et al., ICML 2025.
  Hierarchical structures: 5.5% drop vs 23.7% for flat. Challenger
  and Inspector mechanisms recover 96.4% of errors.

- [Game-Theoretic Lens on LLM-based Multi-Agent Systems](https://arxiv.org/abs/2601.15047)
  Hao et al., 2026.
  Survey organizing multi-agent LLM work through four game theory
  elements.


### Adaptive and Conditional Protocols (additions)

- [DebUnc: Improving LLM Agent Communication with Uncertainty Metrics](https://arxiv.org/abs/2407.06426)
  Yoffe et al., 2024.
  Attention-scaling shifts weights toward more confident agents.

- [OI-MAS: Orchestrating Intelligence with Confidence-Aware Routing](https://arxiv.org/abs/2601.04861)
  Wang et al., 2026.
  Adaptive model-scale selection per reasoning stage. +12.88%
  accuracy, -79.78% cost.

- [MasRouter: Learning to Route LLMs for Multi-Agent Systems](https://arxiv.org/abs/2502.11133)
  Yue et al., ACL 2025.
  Cascaded controller for collaboration mode, role allocation, and
  LLM routing. 52x overhead reduction.

- [Dynamic Role Assignment for Multi-Agent Debate](https://arxiv.org/abs/2601.17152)
  Zhang et al., 2026.
  "Meta-Debate" for capability-aware agent-to-role assignment.
  Up to 74.8% improvement over uniform assignment.


### Confidence Calibration and Weighting (additions)

- [Scalable Best-of-N Selection via Self-Certainty](https://arxiv.org/abs/2502.18581)
  Kang et al., NeurIPS 2025.
  Divergence from uniform distribution as confidence. Scales without
  external reward model.

- [Deep Think with Confidence (DeepConf)](https://arxiv.org/abs/2508.15260)
  Meta AI, 2025.
  Confidence-weighted voting + dynamic termination. 99.9% AIME 2025
  at 512 samples. 84.7% token reduction.

- [Learning to Route LLMs with Confidence Tokens (Self-REF)](https://arxiv.org/abs/2410.13284)
  Chuang et al., ICML 2025.
  Trains confidence tokens into LLMs via self-reflection with
  error-based feedback.

- [Don't Always Pick the Highest-Performing Model: An Information Theoretic View](https://arxiv.org/abs/2602.08003)
  2026.
  Gaussian-copula model for correlated errors. Same-family models
  share failure modes; adding high-accuracy models may degrade
  ensemble performance.


### Scalable Oversight (additions)

- [Prover-Verifier Games Improve Legibility of LLM Outputs](https://arxiv.org/abs/2407.13692)
  Kirchner et al., OpenAI, 2024.
  Trains provers to produce verifier-checkable solutions. Legibility
  to small LLMs transfers to humans.

- [A Benchmark for Scalable Oversight Protocols](https://arxiv.org/abs/2504.03731)
  Sudhir et al., ICLR 2025 Workshop.
  Agent Score Difference metric. Python package for benchmarking
  oversight protocols.

- [When Weak LLMs Speak](https://openreview.net/forum?id=ROioaZ45Yz)
  ICLR 2026.
  Aligning strong LLM under weak LLM supervision.


### LLM-as-Judge (additions)

- [Pairwise or Pointwise? Evaluating Feedback Protocols for Bias](https://arxiv.org/abs/2504.14716)
  Tripathi et al., 2025.
  Pairwise flips ~35% of cases vs ~9% for absolute scores. Pairwise
  more vulnerable to distracted evaluation.

- [Am I More Pointwise or Pairwise? Rubric Position Bias](https://arxiv.org/abs/2602.02219)
  Xu et al., 2026.
  Rubric-based evaluation has position bias. Balanced permutation
  improves human correlation.

- [CollabEval: Enhancing LLM-as-a-Judge via Multi-Agent Collaboration](https://arxiv.org/abs/2603.00993)
  Amazon Science, 2025/2026.
  Three-phase collaborative judging. Collaboration over competition.

- [Multi-Agent Debate for LLM Judges with Adaptive Stability Detection](https://arxiv.org/abs/2510.12697)
  Hu et al., 2025.
  Proves collaborative discussion improves over static ensembles.
  Adaptive stopping via Beta-Binomial mixture model.


### Foundational Single-Model Techniques (context for multi-model work)

- [Chain-of-Thought Prompting Elicits Reasoning](https://arxiv.org/abs/2201.11903)
  Wei et al., NeurIPS 2022. [KEY]
  Foundation for reasoning via explicit intermediate steps.

- [Strategic Chain-of-Thought (SCoT)](https://arxiv.org/abs/2409.03271)
  Wang et al., 2024.
  Two-stage: elicit strategy first, then guided CoT. +21% GSM8K.

