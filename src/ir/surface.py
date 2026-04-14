"""Surface-level authoring API for the protocol IR.

The core IR in ast.py is the object of study — it's what gets
type-checked, serialized, traversed, and mutated. This module is the
authoring front-end: lowercase factory functions that read like math,
hide enum verbosity, and expose the Let binding as an Expr method
instead of a classmethod with keyword arguments.

Protocol definitions should import from here, not from ast directly.
The core IR stays the source of truth; this module only changes how
humans (and models) write protocol definitions.
"""

from __future__ import annotations

from typing import Callable, TypeVar

from .ast import (
    Expr,
    Finalize,
    Gen,
    Let,
    ParGen,
    ParScore,
    QueryVar,
    Review,
    Revise,
    ReviseRound,
    Rounds,
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


def revise_round(
    models: list[str],
    drafts: Expr[list[Answer[Draft]]],
    context: ContextMode = FRESH,
    visibility: Visibility = PEERS_GROUPED,
) -> Expr[list[Answer[Draft]]]:
    """One round of parallel review-and-revise across models."""
    return ReviseRound(
        models=models, drafts=drafts, context=context, visibility=visibility
    )


def rounds(
    n: int,
    models: list[str],
    drafts: Expr[list[Answer[Draft]]],
    context: ContextMode = FRESH,
    visibility: Visibility = PEERS_GROUPED,
) -> Expr[list[Answer[Draft]]]:
    """N rounds of review-and-revise across models."""
    return Rounds(
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


def weighted_vote(
    drafts: Expr[list[Answer[Draft]]],
    scores: Expr[list[Score[Answer[Draft]]]],
) -> Expr[Answer[Draft]]:
    """Confidence-weighted selection from a list of drafts."""
    return WeightedVote(drafts=drafts, scores=scores)


# ============================================================================
# Let binding as an Expr method
# ============================================================================
# Instead of Let.make(value=..., body_fn=lambda v: ...) which reads as
# ceremony, we want `.let(lambda r: ...)` as a method call on the
# value expression. This reads left-to-right: "bind this value, then
# use it in this body."

T1 = TypeVar("T1")
T2 = TypeVar("T2")


def bind(
    value: Expr[T1],
    body: Callable[[Expr[T1]], Expr[T2]],
    name: str = "v",
) -> Expr[T2]:
    """Bind a value to a name within a body expression.

    Usage:
        result = bind(
            rounds(3, models, par_gen(models, q)),
            lambda r: finalize(weighted_vote(r, par_score(models, r))),
            name="refined",
        )

    The body receives a fresh Var of the same type as the value and
    returns an Expr using it. The binding is stored as a first-order
    Let node internally for serialization and traversal.
    """
    return Let.make(value=value, body_fn=body, hint=name)
