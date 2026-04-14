# Papers to Read

## Per-Model Recommendations

### Claude

MUST READ — engage deeply (15 papers):

  Core protocol comparison:
  - Kenton et al. (2407.04622) — The template. Most comprehensive head-to-head of oversight protocols. Finding that many tuning knobs don't matter is crucial.
  - ColMAD (2510.20963) — Competitive debate hurts, collaborative helps. "Debate hacking" failure mode. Cross-family pairs reduce errors 30%+.
  - Demystifying MAD (2601.19921) — Proves vanilla MAD is a martingale (no expected improvement). Diversity and confidence are the two fixes.
  - Talk Isn't Always Cheap (2509.05396) — When debate actively harms. Correct-to-incorrect flips dominate. Anti-sycophancy prompting doesn't fix it.
  - Voting or Consensus (2502.19130) — Most systematic decision-protocol comparison. Voting helps reasoning (+13.2%), consensus helps knowledge (+2.8%). More rounds hurts voting.
  - ReConcile (2309.13007) — Closest existing multi-model protocol comparison. Diversity is the biggest contributor. Missing: compute matching.

  Diversity and selection theory:
  - Don't Always Pick the Highest-Performing (2602.08003) — Information-theoretic proof of why diversity beats top-k. Saturation theorem. Budget-constrained framework.
  - Diversity of Thought (2410.12853) — Diverse medium models (91%) beat GPT-4 (87%) on GSM-8K. Works at all scales.

  Protocol design variables:
  - When Identity Skews Debate (2510.07517) — Anonymization nearly eliminates identity bias. Zero-cost intervention. IBC metric.
  - Information Propagation in Topologies (2505.23352) — Moderate sparsity is optimal. Causal framework for error vs insight propagation.
  - Exploring Collaboration: Social Psychology (2310.02124) — Systematically varies trait x pattern x strategy. Measures token efficiency.

  Judge methodology (critical for our experimental design):
  - PoLL (2404.18796) — Cross-family judge panels beat GPT-4 at 7x lower cost.
  - Pairwise or Pointwise (2504.14716) — Pairwise flips 35% of cases with distractors vs 9% for pointwise. Scoring protocol is a real variable.
  - Preference Leakage (2502.01534) — Cross-family bias is pervasive and subtle. Must control for model relatedness.

  Scaling and compute:
  - Scaling Laws for Scalable Oversight (2504.18530) — Quantitative scaling laws for when oversight works. Debate 51.7% success vs 9-13% for other games.
  - Scaling Test-Time Compute (2408.03314) — Compute-optimal allocation. 4x efficiency over best-of-N. Optimal strategy varies by difficulty.

  Plus the LLM Ensemble Survey (2502.18036) as essential reference for the design space taxonomy.

  WORTH READING — useful but less central (9 papers):

  - Debate Helps Weak-to-Strong (2501.13124) — Debate transcripts as training signal. Different paradigm (finetuning) but strong results.
  - Can LLMs Really Debate (2511.07784) — Confirms: model strength and diversity are the only structural factors that matter.
  - More Rounds More Noise (2603.16244) — Additional rounds degrade review via false positive pressure. Single-model, but the failure modes transfer.
  - MoA (2406.04692) — "Collaborativeness" phenomenon. Even weak model outputs improve strong models.
  - Resilience with Faulty Agents (2408.00989) — Hierarchical structures most resilient (5.5% drop vs 23.7%). Inspector agents recover 96.4%.
  - CISC (2502.06233) — Confidence weighting reduces compute 40%. Within-question discrimination matters more than calibration.
  - Prover-Verifier Games (2407.13692) — Legibility to small verifiers transfers to humans. Training-time, but foundational framing.
  - Let's Verify Step by Step (2305.20050) — Process supervision beats outcome supervision. Sets up the PRM paradigm.
  - LE-MCTS (2412.15797) — Process-level ensemble is the only granularity that works for hard reasoning. Token and output level fail.

  SKIM ONLY (5 papers):
  - Group Conformity, LLM-Blender, Cross-Context Review, Multi-Agent Collaboration Survey, LLM-as-Judge Survey

  SKIP (1 paper):
  - Plan-and-Solve (single-model prompting, not relevant)

  My recommendation for your personal deep reading: Start with Kenton, then ColMAD, then Demystifying MAD. Those three together give you the strongest foundation — the most comprehensive
  protocol comparison, the collaborative vs adversarial result, and the theoretical framework for why debate fails or succeeds. Then read the information-theoretic paper (2602.08003) for
  the formal argument about diversity, and PoLL + Preference Leakage for judge design since that's foundational to our methodology.

  That's 6 papers for the core understanding. The other 9 MUST READs fill in specific variables (anonymization, topology, decision protocol, scaling) and can be read more selectively based
   on which protocol variables you decide to test.

### Codex

  Read In Full

  - data/papers/2407.04622.html
    On Scalable Oversight with Weak LLMs Judging Strong LLMs
    This is the clearest direct match to your core question. It gives you the oversight framing, the debate/consultancy/direct-QA comparison, and a concrete benchmark for what
    “oversight protocol” means in the alignment literature.
  - data/papers/2603.12123.tex
    Cross-Context Review
    Very high relevance to your session-context variable. It is unusually close to your protocol inventory and likely to matter directly for experimental design.
  - data/papers/2603.16244.tex
    More Rounds, More Noise
    Probably one of the most actionable papers in the folder. It bears directly on whether multi-turn review is actually worth testing or should mostly be treated as a likely
    failure mode.
  - data/papers/2510.20963.tex
    On Scalable Oversight with Collaborative Multi-Agent Debate in Error Detection
    This is the best direct match for collaborative vs adversarial interaction in an oversight-like setting.
  - data/papers/2504.18530.tex
    Scaling Laws For Scalable Oversight
    Worth reading closely because it sharpens the capability-gap and task-dependence arguments behind the whole project.
  - data/papers/2309.13007.tex
    ReConcile
    Important because it is one of the strongest concrete multi-model protocol papers in your space: diversity, discussion, confidence weighting, and consensus.
  - data/papers/2502.19130.tex
    Voting or Consensus? Decision-Making in Multi-Agent Debate
    This looks very useful for separating protocol claims from aggregation claims.
  - data/papers/2601.19921.tex
    Demystifying Multi-Agent Debate: The Role of Confidence and Diversity
    Worth a full read because it seems aimed exactly at mechanism-level interpretation rather than just leaderboard gains.
  - data/papers/2404.18796.tex
    Replacing Judges with Juries / PoLL
    If judge design is part of the protocol, this is one of the most important non-generation papers in the set.
  - data/papers/2502.01534.tex
    Preference Leakage
    This matters because your study will rely heavily on model judging. If you do not understand this paper well, it is easy to accidentally build contamination into the
    evaluation.

  Read Closely If You Expect That Branch To Matter

  - data/papers/2305.05176.tex
    FrugalGPT
    Read if routing/cascading will remain a serious competitor in your design.
  - data/papers/2406.18665.tex
    RouteLLM
    Same reason. Important if you want strong “single-route competitor” baselines.
  - data/papers/2502.06233.tex
    CISC
    Read if confidence-weighted aggregation is likely to become a central baseline.
  - data/papers/2408.00989.tex
    Resilience with Faulty Agents
    Read if topology and robustness to bad reviewers become central variables.
  - data/papers/2407.13692.tex
    Prover-Verifier Games Improve Legibility of LLM Outputs
    More useful for conceptual framing and later extensions than for the immediate Phase 1 matrix, but still important.
  - data/papers/2305.20050.tex
    Let’s Verify Step by Step
    Read if verifier/process-supervision ideas will influence your protocol definitions or judging setup.

  Probably Skim Rather Than Read Fully Right Now

  - data/papers/2501.06322.tex
    Survey, useful for mapping, but not where I’d spend deep reading time first.
  - data/papers/2411.15594.tex
    Judge survey, useful as a directory, less useful than the concrete judge-bias papers.
  - data/papers/2305.04091.tex and data/papers/2410.12853.md
    Relevant, but I would not prioritize them ahead of the papers above.

  If I had to cut this to a smallest serious reading set, I’d pick 8:

  1. Kenton
  2. Cross-Context Review
  3. More Rounds, More Noise
  4. ColMAD
  5. ReConcile
  6. Scaling Laws for Scalable Oversight
  7. PoLL
  8. Preference Leakage


### Gemini

✦ I've analyzed the 37 downloaded papers and recommend focusing on the following five for deep engagement, as they directly address our research into collaboration protocols:

  1. On Scalable Oversight with Weak LLMs (Kenton et al., 2024)
   * Location: data/papers/2407.04622.html
   * Why it’s critical: This is the primary anchor for our study. It compares Debate, Consultancy, and Direct QA in a "weak-overseeing-strong" regime. It establishes the baseline finding
     that adversarial debate helps a weaker judge extract truth, but also identifies the domains (like math/logic) where this advantage narrows.

  2. ColMAD: Collaborative Multi-Agent Debate (Chen et al., 2026)
   * Location: data/papers/2510.20963.tex
   * Why it’s critical: Directly addresses our Variable B (Interaction Framing). It demonstrates that reframing the "game" from competitive (zero-sum) to collaborative (non-zero-sum)
     significantly improves error detection and reduces "debate hacking"—where models optimize for persuasion rather than truth.

  3. More Rounds, More Noise (Song, 2026)
   * Location: data/papers/2603.16244.tex
   * Why it’s critical: Provides the most important "negative result" in the current literature. It details the "Precision Collapse" phenomenon, where increasing the rounds of interaction
     leads to hallucinated flaws (noise), arguing that single-pass, fresh-session review is consistently more reliable.

  4. Don't Always Pick the Highest-Performing Model (Turkmen et al., 2026)
   * Location: data/papers/2602.08003.tex
   * Why it’s critical: Offers a strong theoretical and empirical argument for Variable A (Lineage Diversity). It shows that because model errors are correlated (especially within the same
     lineage), selecting a diverse set of "good-enough" models often outperforms an ensemble of the highest-accuracy models from the same family.

  5. ReConcile: Round-Table Conference (Chen et al., 2024)
   * Location: data/papers/2309.13007.tex
   * Why it’s critical: A key example of a Hierarchical Topology. It uses a multi-model "round-table" discussion with confidence-weighted voting and shows that this collaborative synthesis
     can help a team of smaller models exceed the performance of a single frontier model (like GPT-4).

  Landscape Overviews
  If you need to map the broader "Multi-Agent" or "Ensemble" landscape, these two surveys are the most comprehensive in the folder:
   * 2502.18036.tex: Harnessing Multiple LLMs: A Survey on LLM Ensemble (Chen et al., 2025)
   * 2501.06322.tex: Multi-Agent Collaboration Mechanisms: A Survey of LLMs (Tran et al., 2025)

  These five (plus the surveys) cover the most relevant "levers" we’ve discussed: debate vs. collaboration, fresh vs. same session, and diversity vs. raw capability.





## Consolidation

- (2407.04622) Cl,Co,G: Kenton et al. 
- (2510.20963) Cl,Co,G: ColMAD
- (2309.13007) Cl,Co,G: ReConcile

- (2601.19921) Cl,Co: Demystifying MAD
- (2502.19130) Cl,Co: Voting or Consensus
- (2404.18796) Cl,Co: PoLL
- (2502.01534) Cl,Co: Preference Leakage
- (2504.18530) Cl,Co: Scaling Laws for Scalable Oversight
- (2602.08003) Cl,G: Don't Always Pick the Highest-Performing
- (2603.16244) Co,G: More Rounds, More Noise

- (2509.05396) Cl: Talk Isn't Always Cheap
- (2410.12853) Cl: Diversity of Thought
- (2510.07517) Cl: When Identity Skews Debate
- (2505.23352) Cl: Information Propagation in Topologies
- (2310.02124) Cl: Exploring Collaboration: Social Psychology
- (2504.14716) Cl: Pairwise or Pointwise
- (2408.03314) Cl: Scaling Test-Time Compute
- (2603.12123) Co: Cross-Context Review


    
 
