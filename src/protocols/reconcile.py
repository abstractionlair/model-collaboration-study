"""ReConcile: heterogeneous multi-model round-table discussion.

Expresses the protocol from:
  Chen, Saha, Bansal, 2024. "ReConcile: Round-Table Conference
  Improves Reasoning via Consensus among Diverse LLMs."

Structure:
1. Each model independently generates an initial draft.
2. For N rounds: review-and-revise across the pool, with peer
   drafts grouped as visibility context.
3. Each model produces a confidence score for its refined draft.
4. Weighted vote selects the team answer.
5. Finalize wraps the selected draft as the committed final answer.

**Faithfulness note (2026-04-16).** Step 2 currently uses
`SelfRounds` (each model self-reviews its own draft with peer
drafts as context). The ReConcile paper's round-table format has
each agent critiquing peer drafts, not self-reviewing. The
peer-review sibling (`PeerRounds`) is planned; this protocol
will migrate to it. Tracked in `decisions.md` 2026-04-16 entry
"Rename ReviseRound/Rounds to SelfReviseRound/SelfRounds."

Notes:
- "Convincing samples" (per-model few-shot demonstrations of
  persuasive explanations) are prompt-level details that belong in
  the experiment spec layer, not the protocol IR.
- Confidence is captured by par_score rather than baked into gen, so
  that confidence extraction can be mutated independently.
- SelfRounds is a single node with an explicit count, so mutating
  the round count is a local field change.
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
    self_rounds,
    weighted_vote,
)
from src.ir.types import Answer, Final
from src.ir.ast import Expr


def reconcile(
    models: list[str],
    n_rounds: int = 3,
) -> Expr[Answer[Final]]:
    """Build the ReConcile protocol AST.

    Currently uses self-review-with-peer-context per the
    faithfulness note in the module docstring. Will migrate to
    peer review once `PeerRounds` lands.
    """
    q = query()
    refined = self_rounds(
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
