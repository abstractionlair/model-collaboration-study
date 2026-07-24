"""Phase 1 macro-model condition factories.

Each function builds an IR expression for one experimental condition.
The functions are parameterized by model names and structural parameters
(like sample count) so the same condition can be instantiated at
different budget tiers.

**Faithfulness status (2026-04-16).** All three faithfulness gaps
from the cross-lineage review have been reconciled:
- D-family (Codex #1, Gemini #2): D, D', and E use
  `PeerReviseRound`/`PeerRounds`, not the self-review variants.
- B/C aggregation (Opus #1, Codex #2, Gemini #3): B and C use
  `PickOne`, not pointwise scoring.
- E composition (Opus #2, Codex #3, Gemini #4): E uses
  `ParPeerReview` + `FuseWithCritiques` so the meta-reviewer
  sees raw critiques and writes the final directly, per the
  design. The previous implementation lives on as
  `condition_e_writers_revise_then_fuse` (kept as a building
  block — a reasonable macro-model in its own right).

Condition D (heterogeneous ReConcile) is expressed in
reconcile.py. D' is ReConcile instantiated with a homogeneous pool
(requires pool_size >= 2 since peer review is undefined for N=1).
"""

from __future__ import annotations

from src.ir.ast import Expr
from src.ir.surface import (
    ALL_VISIBLE,
    FRESH,
    PEERS_GROUPED,
    bind,
    finalize,
    fuse,
    fuse_with_critiques,
    gen,
    par_gen,
    par_peer_review,
    peer_revise_round,
    pick_one,
    query,
)
from src.ir.types import Answer, Final

from .reconcile import reconcile


# ============================================================================
# Condition A: Single-model, one pass
# ============================================================================

def condition_a(model: str) -> Expr[Answer[Final]]:
    """A single Gen block against the best subject model.

    One response by construction; no aggregation needed.
    Reference point for "what does one model alone get you at $X."
    """
    q = query()
    return finalize(gen(model, q))


# ============================================================================
# Condition B: Single-model repeat-and-aggregate
# ============================================================================

def condition_b(model: str, n_samples: int) -> Expr[Answer[Final]]:
    """ParGen producing N samples from one model, aggregated by `PickOne`.

    Another instance of the same model — the peer judge, blinded
    to identities — sees all N candidates side-by-side and picks
    the single best one. This is the design's "same-model
    peer-judge aggregation block that chooses among the N
    candidates" specification.

    Migrated from ParScore + WeightedVote (pointwise scoring +
    argmax) to PickOne on 2026-04-16; pointwise was a silent
    reinterpretation of "chooses among." See `decisions.md`
    2026-04-16 for the rationale and the principle of keeping
    both aggregation rules as separate building blocks.

    N is determined by the budget tier: at $X it's a sanity
    check (N=1 or 2), at $2X and $4X it scales up.
    """
    q = query()
    models = [model] * n_samples
    drafts = par_gen(models, q)
    return finalize(pick_one(model, drafts))


# ============================================================================
# Condition C: Heterogeneous parallel + peer-LLM aggregation
# ============================================================================

def condition_c(
    subject_models: list[str],
    judge_model: str,
) -> Expr[Answer[Final]]:
    """ParGen one sample per subject model, judged by a peer-LLM via `PickOne`.

    One judge model from the subject pool sees all N candidates
    side-by-side (identities blinded) and picks the single best
    one. No critique, no revision — tests whether lineage
    diversity alone produces a real gain at matched dollars.

    The judge_model should be drawn from subject_models (it's a
    peer-LLM, not an external judge), but this is not enforced.

    Migrated from ParScore + WeightedVote to PickOne on
    2026-04-16; same rationale as condition_b. See `decisions.md`
    2026-04-16.
    """
    q = query()
    drafts = par_gen(subject_models, q)
    return finalize(pick_one(judge_model, drafts))


# ============================================================================
# Condition D: Heterogeneous ReConcile-style
# ============================================================================

# D is just reconcile() from src/protocols/reconcile.py.
# Re-exported here for completeness.
condition_d = reconcile


# ============================================================================
# Condition D': Homogeneous ReConcile-style
# ============================================================================

def condition_d_prime(
    model: str,
    pool_size: int,
    n_rounds: int = 1,
) -> Expr[Answer[Final]]:
    """Structurally identical to D, but the subject pool is homogeneous.

    N instances of the same model, identities still blinded.
    This is the control that supports the cleanest heterogeneity
    comparison: D → D' varies pool composition while holding
    everything else constant.
    """
    return reconcile([model] * pool_size, n_rounds=n_rounds)


# ============================================================================
# Condition E: Hierarchical synthesis
# ============================================================================

def condition_e(
    subject_models: list[str],
    meta_reviewer: str,
) -> Expr[Answer[Final]]:
    """ParGen + ParPeerReview + FuseWithCritiques (design-faithful E).

    Each subject model generates a draft, peer reviewers
    (cyclic 1-peer-per-draft) produce critiques on the drafts,
    then a designated meta-reviewer reads each draft paired
    with its critique and writes a fresh synthesized response.
    The meta-reviewer's synthesis IS the final answer — no
    separate aggregation step. Requires len(subject_models) >= 2.

    The meta_reviewer should typically be drawn from
    subject_models (it's a peer, not an external judge), but
    this is not enforced.

    Migrated 2026-04-16 from the writers-revise-then-fuse
    variant (kept available as
    `condition_e_writers_revise_then_fuse`) to match the design
    specification: meta synthesizes raw critiques directly,
    not revised drafts. Resolves the E composition gap
    surfaced in the cross-lineage review.

    Call count: 2N + 1 (was 3N + 1).
    """
    q = query()
    drafts = par_gen(subject_models, q)
    # ALL_VISIBLE so reviewers see the task alongside the drafts —
    # same rationale as the 2026-04-21 reconcile() fix; E was left
    # on PEERS_GROUPED then and caught by the round-7 review.
    critiques = par_peer_review(subject_models, drafts, FRESH, ALL_VISIBLE)
    # `drafts` is referenced twice (here and inside `critiques`);
    # identity-based memoization in the executor guarantees the
    # meta-reviewer sees the same drafts that were peer-reviewed.
    return finalize(
        fuse_with_critiques(meta_reviewer, drafts, critiques, q)
    )


def condition_e_writers_revise_then_fuse(
    subject_models: list[str],
    meta_reviewer: str,
) -> Expr[Answer[Final]]:
    """ParGen + PeerReviseRound + Fuse over revised drafts.

    The pre-2026-04-16 implementation of condition E. Kept as a
    typed building block — it's a coherent macro-model shape
    that an experiment may want to test as an alternative to the
    design-faithful E. Differences from `condition_e` (the
    current design-faithful version):
    - Subject models revise their own drafts from the peer
      critiques before the meta-reviewer sees anything.
    - Meta-reviewer uses `Fuse` (drafts only) rather than
      `FuseWithCritiques` (drafts + raw critiques).
    - Higher cost (3N + 1 calls vs the design version's 2N + 1).

    The two macro-models test different intuitions about where
    the integration work happens. The design committed to E as
    the meta-does-all-work version; this variant gives writers
    a revision pass first.

    Requires len(subject_models) >= 2.
    """
    q = query()
    drafts = par_gen(subject_models, q)
    revised = peer_revise_round(subject_models, drafts, FRESH, PEERS_GROUPED)
    return finalize(fuse(meta_reviewer, revised, q))
