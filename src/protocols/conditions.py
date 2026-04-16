"""Phase 1 macro-model condition factories.

Each function builds an IR expression for one experimental condition.
The functions are parameterized by model names and structural parameters
(like sample count) so the same condition can be instantiated at
different budget tiers.

Condition D (heterogeneous ReConcile) is already expressed in
reconcile.py. D' is ReConcile instantiated with a homogeneous pool.

Condition E (hierarchical synthesis) is not yet expressible with the
current IR — see the note at the end of this file.
"""

from __future__ import annotations

from src.ir.ast import Expr
from src.ir.surface import (
    FRESH,
    PEERS_GROUPED,
    bind,
    finalize,
    fuse,
    gen,
    par_gen,
    par_score,
    query,
    revise_round,
    rounds,
    weighted_vote,
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
    """ParGen producing N samples from one model, aggregated by self-scoring.

    The same model independently scores each candidate (pointwise,
    no access to executable ground truth), and the highest-scored
    candidate is selected via WeightedVote.

    N is determined by the budget tier: at $X it's a sanity check
    (N=1 or 2), at $2X and $4X it scales up.

    The design doc specified "same-model peer-judge aggregation
    block" — ParScore + WeightedVote implements this as independent
    pointwise scoring followed by max-selection. The model scores
    each candidate in isolation; it does not see all candidates at
    once. This is a reasonable non-oracle internal aggregation
    mechanism for Phase 1. Comparative (all-at-once) selection is
    a follow-on ablation on the aggregation axis.
    """
    q = query()
    models = [model] * n_samples
    drafts = par_gen(models, q)
    return bind(
        drafts,
        lambda ds: finalize(weighted_vote(ds, par_score(models, ds))),
    )


# ============================================================================
# Condition C: Heterogeneous parallel + peer-LLM aggregation
# ============================================================================

def condition_c(
    subject_models: list[str],
    judge_model: str,
) -> Expr[Answer[Final]]:
    """ParGen one sample per subject model, judged by a peer from the pool.

    One judge model from the subject pool independently scores each
    candidate, and the highest-scored is selected. No critique, no
    revision — tests whether lineage diversity alone produces a real
    gain at matched dollars.

    The judge_model should be drawn from subject_models (it's a
    peer-LLM, not an external judge). The judge scores each draft
    independently via ParScore.
    """
    q = query()
    n = len(subject_models)
    judges = [judge_model] * n
    drafts = par_gen(subject_models, q)
    return bind(
        drafts,
        lambda ds: finalize(weighted_vote(ds, par_score(judges, ds))),
    )


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
    """ParGen + one ReviseRound + Fuse by a meta-reviewer.

    Each subject model generates a draft, then one round of peer
    review-and-revise improves the drafts, then a designated
    meta-reviewer reads all improved drafts and writes a fresh
    synthesized response. The meta-reviewer's synthesis IS the
    final answer — no separate aggregation step.

    The meta_reviewer should typically be drawn from subject_models
    (it's a peer, not an external judge), but this is not enforced.

    Fuse is the node that makes this expressible: it reads multiple
    peer drafts and writes fresh, unlike WeightedVote (mechanical
    selection) or Revise (one draft + one critique).
    """
    q = query()
    drafts = par_gen(subject_models, q)
    revised = revise_round(subject_models, drafts, FRESH, PEERS_GROUPED)
    return finalize(fuse(meta_reviewer, revised, q))
