"""Phase 1 macro-model condition factories.

Each function builds an IR expression for one experimental condition.
The functions are parameterized by model names and structural parameters
(like sample count) so the same condition can be instantiated at
different budget tiers.

**Faithfulness note (2026-04-16).** Conditions D, D', and E now
use `PeerReviseRound` / `PeerRounds` — each draft reviewed by a
different model (cyclic 1-peer-per-draft assignment). This
matches the design's "1–2 peers" specification at the lower
bound and resolves the D-family review-semantics faithfulness
gap surfaced in the cross-lineage review round.

Condition E retains a remaining faithfulness gap: the design
specifies that the meta-reviewer synthesizes raw critiques and
writes the final response directly, while the implementation
has writers revise their drafts before the meta-reviewer fuses
the revised drafts. Resolution requires a `FuseWithCritiques`
(or similar) node that lets Fuse consume both drafts and
critiques; tracked in `docs/status.md` "Currently routed to."

Condition D (heterogeneous ReConcile) is expressed in
reconcile.py. D' is ReConcile instantiated with a homogeneous pool
(requires pool_size >= 2 since peer review is undefined for N=1).
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
    """ParGen + one PeerReviseRound + Fuse by a meta-reviewer.

    Each subject model generates a draft, then one round of
    peer-review-and-revise improves the drafts (each draft
    critiqued by a peer per cyclic assignment, original writer
    revises), then a designated meta-reviewer reads all improved
    drafts and writes a fresh synthesized response. The
    meta-reviewer's synthesis IS the final answer — no separate
    aggregation step. Requires len(subject_models) >= 2.

    The meta_reviewer should typically be drawn from
    subject_models (it's a peer, not an external judge), but this
    is not enforced.

    Fuse is the node that makes this expressible: it reads
    multiple peer drafts and writes fresh, unlike WeightedVote
    (mechanical selection) or Revise (one draft + one critique).

    Remaining faithfulness gap (E composition): the design
    specifies that the meta-reviewer synthesizes raw critiques
    directly, not revised drafts. This implementation has writers
    revise before the meta-reviewer fuses, which is
    structurally a different macro-model. Resolution requires a
    FuseWithCritiques-style node; tracked in
    `docs/status.md` "Currently routed to."
    """
    q = query()
    drafts = par_gen(subject_models, q)
    revised = peer_revise_round(subject_models, drafts, FRESH, PEERS_GROUPED)
    return finalize(fuse(meta_reviewer, revised, q))
