DRAFT -- INCOMPLETE
Full bibliographic details not yet gathered. Additional papers to be added during literature phase.
Relevance notes are drawn from source conversations; claims have not been independently verified against the original papers.


GENERATION + SELECTION / ENSEMBLING

Self-Consistency (Wang et al., 2022)
  Standard baseline for sampling diverse reasoning paths and majority voting. Widely used instantiation of the generate-then-select pattern.

Confidence-Informed Self-Consistency (CISC, 2026)
  Matched self-consistency accuracy with 40%+ fewer samples by weighting on confidence.

Soft Self-Consistency
  Needed roughly half as many samples as vanilla SC for comparable results on interactive tasks.

OSCA
  Better accuracy than best single inference with 25-128x less compute on reasoning and code tasks.

ModelSwitch (2025)
  Heterogeneous routing across models. 34% lower sampling count, 10.2 points above best single LLM on MMLU-Pro. Small model combinations matched much larger models.

Mixture-of-Agents (MoA)
  Open-source ensemble reached 65.1% on AlpacaEval 2.0 vs 57.5% for GPT-4o. Reported a "collaborativeness" phenomenon: LLMs generate better responses when presented with outputs from other models.

Self-MoA
  Argued single-model aggregation often beats mixed-model MoA. 6.6% improvement over standard MoA on AlpacaEval 2.0.


CRITIQUE / PEER REVIEW / REVISION

Multi-Agent Peer Review Collaboration (2023)
  Closest to full generate-then-cross-critique-then-revise pipeline. Agents independently construct, review, assign confidence, revise. +1.4 on GSM8K, +3.8 on SVAMP. Weaker models benefited more from stronger diverse critics: one pairing improved GPT-3.5-0613 from 75.4 to 83.0 when paired with Claude Instant 1.2, while the stronger model barely moved (85.4 to 86.0).

EdgeJury
  Parallel generation + cross-review + synthesis + verification. 76.2% on TruthfulQA MC1 vs 62.8% single 8B baseline.

LLM-PeerReview
  Peer-review-inspired ensemble for selecting among candidates.

RMoA
  Diversity-based filtering before aggregation.

MARS
  Hierarchical author-then-reviewers-then-meta-reviewer-then-revision structure. Accuracy comparable to MAD at roughly 50% token cost.

LLM Review
  Blind peer review for creative generation. Agents exchange targeted feedback but revise independently to avoid homogenization.

Faulty-agent resilience / hierarchical-structure paper (ICML 2025)
  Hierarchical structures were reported as more robust than flatter all-to-all interaction when some agents are faulty. Relevant to topology choice, not just raw quality.


DEBATE

Irving et al. (2018)
  Original AI safety via debate framework.

Kenton et al. (2024)
  Largest formal debate study. 9 tasks, roughly 5M model calls. Debate consistently outperformed consultancy but showed small or no advantage over direct QA on non-information-asymmetry tasks. CoT tended to harm judge performance.

Debate or Vote (2025)
  Disentangled debate from voting. Majority voting accounts for most gains attributed to MAD across seven NLP benchmarks.

ColMAD
  Collaborative debate improved error detection by up to 19%. Competitive debate degraded it by up to 15% vs single-agent. Theoretical analysis showed optimal judge strategy with two dishonest competitive agents is to ignore the transcript.

ICLR 2025 blogpost
  Surveyed five MAD frameworks across nine benchmarks. Concluded MAD does not consistently beat simpler baselines.


SELF-CORRECTION

"Large Language Models Cannot Self-Correct Reasoning Yet"
  Intrinsic self-correction without external feedback often fails or worsens performance.

CorrectBench
  Self-correction can substantially help on reasoning-heavy tasks. Diminishing returns from stacking correction methods.

Google DeepMind (planning tasks)
  Strong gains from intrinsic self-critique in planning tasks.


SESSION / ROUND EFFECTS

Cross-Context Review
  Review in fresh session beat same-session self-review (F1 28.6% vs 24.6%). Repeated same-session review was even worse (21.7%).

"More Rounds, More Noise"
  Single-pass cross-context review beat multi-turn variants. 0.376 F1 for single-pass vs 0.303 for best multi-turn. 62% more false positives in multi-turn.


HETEROGENEITY / ROUTING

RECONCILE
  Heterogeneous multi-model systems with confidence-weighted voting.

Coordinated QA study
  Confirmed heterogeneous agents consistently outperform homogeneous ones due to varied reasoning strategies and error profiles.

Routing benchmarks (2025)
  Complementarity is real but many fancy routers fail to beat simple baselines. Diminishing returns from adding more models. Model curation matters more than ensemble size.


SCALABLE OVERSIGHT

"Scaling Laws for Scalable Oversight"
  Tested 15 models. Monitors improve faster than adversaries at some tasks, but adversary slope steeper at others. Task-dependent.

ColMAD theoretical analysis
  Also relevant here for its formalization of the oversight game structure between competing agents and a judge.


LLM-AS-JUDGE

Judge reliability study (2025)
  Without correct reference, agreement drops sharply on questions the judge cannot answer. GPT-4o pairwise agreement dropped from 0.86 to 0.16 on hard items with own reference.

Reference-guided judging (2026)
  High-quality references substantially improved judge accuracy across 11 judges and 5 benchmarks. Stronger-model references gave 6.8% absolute improvement.

PoLL paper
  Judge panels/juries outperform single large judge and reduce intra-model bias. Better correlation with humans than single GPT-4 judge while cheaper.

Anthropic production LLM judging writeup
  Useful practical reference for rubric-based judging dimensions such as factual accuracy, citation accuracy, completeness, source quality, and tool efficiency. More production note than benchmark paper, but relevant to judge prompt design.

Self-preference bias
  Judges tend to favor outputs stylistically closer to themselves.

Position and verbosity bias
  Well-established problems in LLM judging.


SURVEYS

Multi-agent LLM collaboration survey
  Presents the area as structurally diverse and open-ended rather than converged.

Agent-as-a-judge review
  Describes AI-based judging as an emerging response to the scalable oversight bottleneck.
