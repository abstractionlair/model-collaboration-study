"""ReConcile: heterogeneous multi-model round-table discussion.

Expresses the protocol from:
  Chen, Saha, Bansal, 2024. "ReConcile: Round-Table Conference
  Improves Reasoning via Consensus among Diverse LLMs."

Structure:
1. Each model independently generates an initial draft.
2. For N rounds: each model reviews its draft, seeing grouped peer
   answers, and revises based on the review.
3. Each model produces a confidence score for its refined draft.
4. Weighted vote selects the team answer.
5. Finalize wraps the selected draft as the committed final answer.

Notes:
- "Convincing samples" (per-model few-shot demonstrations of
  persuasive explanations) are prompt-level details that belong in
  the experiment spec layer, not the protocol IR.
- Confidence is captured by par_score rather than baked into gen, so
  that confidence extraction can be mutated independently.
- Rounds is a single node with an explicit count, so mutating the
  round count is a local field change.
"""

from __future__ import annotations

from src.ir.surface import (
    FRESH,
    PEERS_GROUPED,
    bind,
    finalize,
    par_gen,
    par_score,
    query,
    rounds,
    weighted_vote,
)
from src.ir.types import Answer, Final
from src.ir.ast import Expr


def reconcile(
    models: list[str],
    n_rounds: int = 3,
) -> Expr[Answer[Final]]:
    """Build the ReConcile protocol AST."""
    q = query()
    refined = rounds(
        n_rounds, models, par_gen(models, q), FRESH, PEERS_GROUPED
    )
    return bind(
        refined,
        lambda r: finalize(weighted_vote(r, par_score(models, r))),
        name="refined",
    )


def reconcile_no_discussion(models: list[str]) -> Expr[Answer[Final]]:
    """Ablation: ReConcile with zero discussion rounds.

    Equivalent to heterogeneous parallel generation + weighted vote.
    """
    return reconcile(models, n_rounds=0)
