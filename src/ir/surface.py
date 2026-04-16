"""Surface-level authoring API for the protocol IR.

The core IR in ast.py is the object of study — it's what gets
type-checked, serialized, traversed, and mutated. This module is the
authoring front-end: lowercase factory functions that read like math,
hide enum verbosity, and wrap the Let binding in a free function
`bind()` that takes a closure body.

Protocol definitions should import from here, not from ast directly.
The core IR stays the source of truth; this module only changes how
humans (and models) write protocol definitions.
"""

from __future__ import annotations

from typing import Callable, Optional, TypeVar

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
    QueryVar,
    Review,
    Revise,
    SelfReviseRound,
    SelfRounds,
    WeightedVote,
)
from .types import (
    Answer,
    ContextMode,
    Critique,
    Draft,
    Final,
    Query,
    Score,
    Visibility,
)


# ============================================================================
# Enum aliases — use as bare names instead of ContextMode.FRESH etc.
# ============================================================================

FRESH = ContextMode.FRESH
ACCUMULATED = ContextMode.ACCUMULATED

ARTIFACT_ONLY = Visibility.ARTIFACT_ONLY
WITH_PRODUCTION = Visibility.WITH_PRODUCTION
PEERS_GROUPED = Visibility.PEERS_GROUPED
ALL_VISIBLE = Visibility.ALL


# ============================================================================
# Factory functions for AST nodes
# ============================================================================
# Lowercase, positional where clear, no keyword noise. These construct
# the same AST nodes as the core classes, but with an authoring-friendly
# API.

def query(name: str = "q") -> Expr[Query]:
    """The input query variable, bound at execution time."""
    return QueryVar(name=name)


def gen(model: str, q: Expr[Query]) -> Expr[Answer[Draft]]:
    """A model generates a draft from a query."""
    return Gen(model=model, query=q)


def review(
    model: str,
    target: Expr[Answer[Draft]],
    context: ContextMode = FRESH,
    visibility: Visibility = ARTIFACT_ONLY,
) -> Expr[Critique[Answer[Draft]]]:
    """A model reviews a draft, producing a critique."""
    return Review(
        model=model, target=target, context=context, visibility=visibility
    )


def revise(
    model: str,
    draft: Expr[Answer[Draft]],
    critique: Expr[Critique[Answer[Draft]]],
) -> Expr[Answer[Draft]]:
    """A model revises a draft given a critique."""
    return Revise(model=model, draft=draft, critique=critique)


def finalize(draft: Expr[Answer[Draft]]) -> Expr[Answer[Final]]:
    """Mark a draft as the committed final answer."""
    return Finalize(draft=draft)


def par_gen(models: list[str], q: Expr[Query]) -> Expr[list[Answer[Draft]]]:
    """Parallel generation across a list of models."""
    return ParGen(models=models, query=q)


def self_revise_round(
    models: list[str],
    drafts: Expr[list[Answer[Draft]]],
    context: ContextMode = FRESH,
    visibility: Visibility = PEERS_GROUPED,
) -> Expr[list[Answer[Draft]]]:
    """One round of parallel self-review-and-revise across models.

    Each model reviews its OWN draft (with peer drafts visible per
    the visibility annotation) and revises it. The peer-review
    sibling (`peer_revise_round`, different model critiques each
    draft) is the design-faithful version for ReConcile-style
    protocols and will be added when D/D'/E migrate to it.
    """
    return SelfReviseRound(
        models=models, drafts=drafts, context=context, visibility=visibility
    )


def self_rounds(
    n: int,
    models: list[str],
    drafts: Expr[list[Answer[Draft]]],
    context: ContextMode = FRESH,
    visibility: Visibility = PEERS_GROUPED,
) -> Expr[list[Answer[Draft]]]:
    """N rounds of self-review-and-revise across models."""
    return SelfRounds(
        n=n,
        models=models,
        drafts=drafts,
        context=context,
        visibility=visibility,
    )


def peer_revise_round(
    models: list[str],
    drafts: Expr[list[Answer[Draft]]],
    context: ContextMode = FRESH,
    visibility: Visibility = PEERS_GROUPED,
) -> Expr[list[Answer[Draft]]]:
    """One round of peer-review-and-revise across models.

    For each draft d_i, the peer reviewer at index (i+1) % N
    produces the critique and the original writer m_i revises
    its own draft from that critique. Requires at least 2 models.
    """
    return PeerReviseRound(
        models=models, drafts=drafts, context=context, visibility=visibility
    )


def peer_rounds(
    n: int,
    models: list[str],
    drafts: Expr[list[Answer[Draft]]],
    context: ContextMode = FRESH,
    visibility: Visibility = PEERS_GROUPED,
) -> Expr[list[Answer[Draft]]]:
    """N rounds of peer-review-and-revise across models."""
    return PeerRounds(
        n=n,
        models=models,
        drafts=drafts,
        context=context,
        visibility=visibility,
    )


def par_score(
    models: list[str],
    drafts: Expr[list[Answer[Draft]]],
) -> Expr[list[Score[Answer[Draft]]]]:
    """Each model produces a confidence score for its own draft."""
    return ParScore(models=models, drafts=drafts)


def fuse(
    model: str,
    drafts: Expr[list[Answer[Draft]]],
    q: Expr[Query],
) -> Expr[Answer[Draft]]:
    """A model reads multiple peer drafts and writes a fresh response."""
    return Fuse(model=model, drafts=drafts, query=q)


def weighted_vote(
    drafts: Expr[list[Answer[Draft]]],
    scores: Expr[list[Score[Answer[Draft]]]],
) -> Expr[Answer[Draft]]:
    """Confidence-weighted selection from a list of drafts."""
    return WeightedVote(drafts=drafts, scores=scores)


# ============================================================================
# Let binding as a free function
# ============================================================================
# Instead of Let.make(value=..., body_fn=lambda v: ...) which reads as
# ceremony, `bind(value, lambda r: ...)` reads left-to-right: "bind
# this value, then use it in this body."

T1 = TypeVar("T1")
T2 = TypeVar("T2")


def bind(
    value: Expr[T1],
    body: Callable[[Expr[T1]], Expr[T2]],
    name: Optional[str] = None,
) -> Expr[T2]:
    """Bind a value to a name within a body expression.

    Usage:
        result = bind(
            self_rounds(3, models, par_gen(models, q)),
            lambda r: finalize(weighted_vote(r, par_score(models, r))),
        )

    The body receives a fresh Var of the same type as the value and
    returns an Expr using it. The binding is stored as a first-order
    Let node internally for serialization and traversal.

    `name` is an optional debug hint for the generated variable name.
    Omit it unless a specific name aids readability in describe()
    output — the generated name is always fresh either way.
    """
    return Let.make(value=value, body_fn=body, hint=name or "v")
