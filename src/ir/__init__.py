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
    Gen,
    Let,
    ParGen,
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
    Plan,
    Query,
    Score,
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
    # AST
    "Expr",
    "QueryVar",
    "Gen",
    "Review",
    "Revise",
    "Finalize",
    "Fuse",
    "ParGen",
    "SelfReviseRound",
    "SelfRounds",
    "PeerReviseRound",
    "PeerRounds",
    "ParScore",
    "WeightedVote",
    "PickOne",
    "Var",
    "Let",
    # Interpreters
    "describe",
]
