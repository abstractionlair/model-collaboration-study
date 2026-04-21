"""Protocol IR package.

A typed AST for describing multi-model collaboration protocols,
with room for multiple interpreters (describe, execute, estimate
cost, validate against a config, generate mutations).

This is a first sketch. Expand the type set and AST nodes as new
protocols are added.
"""

from .ast import (
    Expr,
    Finalize,
    Fuse,
    FuseWithCritiques,
    Gen,
    Let,
    ParGen,
    ParPeerReview,
    ParScore,
    PeerReviseRound,
    PeerRounds,
    PickOne,
    QueryVar,
    Review,
    Revise,
    SelfReviseRound,
    SelfRounds,
    Var,
    WeightedVote,
)
from .describe import describe
from .types import (
    Answer,
    ContextMode,
    Critique,
    Draft,
    Final,
    Flag,
    ParseFailurePolicy,
    Plan,
    Query,
    Score,
    TieBreakPolicy,
    Visibility,
)

__all__ = [
    # Types
    "Query",
    "Answer",
    "Critique",
    "Flag",
    "Score",
    "Draft",
    "Final",
    "Plan",
    "ContextMode",
    "Visibility",
    "TieBreakPolicy",
    "ParseFailurePolicy",
    # AST
    "Expr",
    "QueryVar",
    "Gen",
    "Review",
    "Revise",
    "Finalize",
    "Fuse",
    "FuseWithCritiques",
    "ParGen",
    "SelfReviseRound",
    "SelfRounds",
    "PeerReviseRound",
    "PeerRounds",
    "ParPeerReview",
    "ParScore",
    "WeightedVote",
    "PickOne",
    "Var",
    "Let",
    # Interpreters
    "describe",
]
