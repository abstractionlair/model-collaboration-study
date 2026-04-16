"""ReConcile: heterogeneous multi-model round-table discussion.

Expresses the protocol from:
  Chen, Saha, Bansal, 2024. "ReConcile: Round-Table Conference
  Improves Reasoning via Consensus among Diverse LLMs."

Structure:
1. Each model independently generates an initial draft.
2. For N rounds: each draft is critiqued by a peer (cyclic
   1-peer-per-draft assignment), then the writer revises its own
   draft from the peer critique. Other peer drafts visible to
   the reviewer per the visibility annotation.
3. Each model produces a confidence score for its refined draft.
4. Weighted vote selects the team answer.
5. Finalize wraps the selected draft as the committed final answer.

Migrated to `PeerRounds` on 2026-04-16; previously used
`SelfRounds` (a faithfulness gap surfaced by the cross-lineage
review round). See `decisions.md` 2026-04-16 entry.

Notes:
- "Convincing samples" (per-model few-shot demonstrations of
  persuasive explanations) are prompt-level details that belong in
  the experiment spec layer, not the protocol IR.
- Confidence is captured by par_score rather than baked into gen, so
  that confidence extraction can be mutated independently.
- PeerRounds is a single node with an explicit count, so mutating
  the round count is a local field change.
- Requires N >= 2 (peer review is undefined for a single model).
"""

from __future__ import annotations

from src.ir.surface import (
    FRESH,
    PEERS_GROUPED,
    bind,
    finalize,
    par_gen,
    par_score,
    peer_rounds,
    query,
    weighted_vote,
)
from src.ir.types import Answer, Final
from src.ir.ast import Expr


def reconcile(
    models: list[str],
    n_rounds: int = 3,
) -> Expr[Answer[Final]]:
    """Build the ReConcile protocol AST.

    Uses peer-review-with-peer-context per the design's D
    specification. Reviewer for draft i is models[(i+1) % N];
    the original writer m_i revises its own draft from the peer
    critique. Requires N >= 2.
    """
    q = query()
    refined = peer_rounds(
        n_rounds, models, par_gen(models, q), FRESH, PEERS_GROUPED
    )
    return bind(
        refined,
        lambda r: finalize(weighted_vote(r, par_score(models, r))),
    )


def reconcile_no_discussion(models: list[str]) -> Expr[Answer[Final]]:
    """Ablation: ReConcile with zero discussion rounds.

    Equivalent to heterogeneous parallel generation + weighted vote.
    """
    return reconcile(models, n_rounds=0)
