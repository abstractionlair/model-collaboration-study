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

Visibility was `PEERS_GROUPED` (peers + draft, task hidden)
through 2026-04-21; moved to `ALL_VISIBLE` per the round-6
context-loss finding so the peer reviewer can see the original
task alongside the other peers' drafts. A reviewer asked to
assess "Correctness" cannot do so without the task. See
`decisions.md` 2026-04-21 entry.

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
    ALL_VISIBLE,
    FRESH,
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

    Uses `ALL_VISIBLE`: the peer reviewer sees the original task,
    the target draft, and the other peers' drafts. This matches
    the ReConcile paper (each agent has the question in hand
    during the round-table phase) and ensures the reviewer can
    assess the "Correctness" critique dimension. Reviewer for
    draft i is models[(i+1) % N]; the original writer m_i
    revises its own draft from the peer critique. Requires N >= 2.
    """
    q = query()
    refined = peer_rounds(
        n_rounds, models, par_gen(models, q), FRESH, ALL_VISIBLE
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
