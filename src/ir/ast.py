"""Protocol IR — AST node definitions.

Expression nodes form a typed AST. Each subclass of Expr[T] produces
a value of type T. The Python type checker (mypy/pyright) verifies
that compositions respect the types at each interface.

This is the minimum set needed to express CCR. Extend as needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from typing import Any, Callable, Generic, TypeVar

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


T = TypeVar("T")
T1 = TypeVar("T1")
T2 = TypeVar("T2")

# Module-level counter for fresh variable names
_var_counter = count()


def _fresh_var_name(hint: str = "v") -> str:
    return f"_{hint}{next(_var_counter)}"


# ============================================================================
# Base expression type
# ============================================================================

class Expr(Generic[T]):
    """Abstract base for all AST nodes.

    An Expr[T] is a protocol step that, when evaluated, produces a
    value of type T. Composition happens by nesting Expr instances
    as fields on other Expr instances.
    """
    pass


# ============================================================================
# Leaf nodes
# ============================================================================

@dataclass(frozen=True)
class QueryVar(Expr[Query]):
    """The input query to the protocol.

    Treated as a bound variable in the AST — its concrete value is
    supplied at execution time, not at AST construction time.
    """
    name: str = "q"


# ============================================================================
# Generation
# ============================================================================

@dataclass(frozen=True)
class Gen(Expr[Answer[Draft]]):
    """A model generates a draft answer to a query.

    Type: Model -> Query -> Answer[Draft]
    """
    model: str
    query: Expr[Query]


# ============================================================================
# Review
# ============================================================================

@dataclass(frozen=True)
class Review(Expr[Critique[Answer[Draft]]]):
    """A model reviews a draft answer and produces a critique.

    Type: Model -> Answer[Draft] -> Critique[Answer[Draft]]

    The context and visibility annotations control the reviewer's
    situation: whether the review happens in a fresh or accumulated
    context, and whether the reviewer sees the artifact alone or
    alongside production history or peer answers.

    These annotations are the main structural knobs for CCR and
    its same-session baselines.
    """
    model: str
    target: Expr[Answer[Draft]]
    context: ContextMode
    visibility: Visibility


# ============================================================================
# Revision
# ============================================================================

@dataclass(frozen=True)
class Revise(Expr[Answer[Draft]]):
    """A model revises a draft based on a critique.

    Type: Model -> Answer[Draft] -> Critique[Answer[Draft]] -> Answer[Draft]

    The result is still a Draft — revision doesn't finalize. Use
    Finalize to mark a draft as committed.
    """
    model: str
    draft: Expr[Answer[Draft]]
    critique: Expr[Critique[Answer[Draft]]]


# ============================================================================
# Finalization
# ============================================================================

@dataclass(frozen=True)
class Finalize(Expr[Answer[Final]]):
    """Mark a draft as the committed final answer.

    Type: Answer[Draft] -> Answer[Final]

    This is a type-level operation — it doesn't modify the content,
    just tags the draft as final. The distinction lets downstream
    steps refuse to accept still-in-progress drafts where only a
    final answer is meaningful.
    """
    draft: Expr[Answer[Draft]]


# ============================================================================
# Parallel operations over models
# ============================================================================
# ReConcile and similar protocols need to apply an operation across
# multiple models in parallel. These nodes encode that directly.
# A more abstract ParMap combinator is possible but less ergonomic
# in Python's generic system; protocol-specific nodes are clearer.

@dataclass(frozen=True)
class ParGen(Expr[list[Answer[Draft]]]):
    """Parallel generation: each model in the list produces a draft independently.

    Type: [Model] -> Query -> [Answer[Draft]]

    The result list is aligned with the models list — result[i] is the
    draft from models[i]. This alignment is an invariant enforced at
    execution time.
    """
    models: list[str]
    query: Expr[Query]


@dataclass(frozen=True)
class ReviseRound(Expr[list[Answer[Draft]]]):
    """One round of parallel review-and-revise across models.

    Each model reviews its own draft, with visibility of peer drafts
    controlled by the visibility parameter. Then each model revises
    its own draft based on the review it generated.

    Type: [Model] -> [Answer[Draft]] -> [Answer[Draft]]

    This is not a primitive — it's morally equivalent to
        [revise(m_i, d_i, review(m_i, d_i, peers)) for (m_i, d_i) in zip(models, drafts)]
    But bundling it as a single node simplifies mutation and
    execution scheduling. An unrolled version using per-model Review
    and Revise nodes would be more explicit but much more verbose
    for larger model pools.
    """
    models: list[str]
    drafts: Expr[list[Answer[Draft]]]
    context: ContextMode
    visibility: Visibility


@dataclass(frozen=True)
class Rounds(Expr[list[Answer[Draft]]]):
    """N rounds of ReviseRound applied to an initial list of drafts.

    Type: Int -> [Model] -> [Answer[Draft]] -> [Answer[Draft]]

    Having the round count as an explicit field (rather than
    unrolling N ReviseRound nodes) makes "change the number of
    rounds" a local mutation — flip one integer field — instead
    of a structural tree edit.
    """
    n: int
    models: list[str]
    drafts: Expr[list[Answer[Draft]]]
    context: ContextMode
    visibility: Visibility


@dataclass(frozen=True)
class ParScore(Expr[list[Score[Answer[Draft]]]]):
    """Each model scores its own draft's confidence.

    Type: [Model] -> [Answer[Draft]] -> [Score[Answer[Draft]]]

    Aligned with the models list: result[i] is the confidence
    models[i] assigns to drafts[i].
    """
    models: list[str]
    drafts: Expr[list[Answer[Draft]]]


# ============================================================================
# Aggregation / selection
# ============================================================================

@dataclass(frozen=True)
class WeightedVote(Expr[Answer[Draft]]):
    """Select one draft from a list via confidence-weighted vote.

    Type: [Answer[Draft]] -> [Score[Answer[Draft]]] -> Answer[Draft]

    Note: this produces Answer[Draft], not Answer[Final]. A protocol
    wanting the selected draft to be treated as final should wrap
    this in Finalize. This separates the structural operation
    (selection) from the semantic status (committed vs in-progress).
    """
    drafts: Expr[list[Answer[Draft]]]
    scores: Expr[list[Score[Answer[Draft]]]]


# ============================================================================
# Let bindings (HOAS style)
# ============================================================================
# Let bindings name a sub-expression so it can be referenced multiple
# times in a body without duplicating the AST. The Python construction
# uses a closure (HOAS — higher-order abstract syntax), which is the
# most Haskell-like approach: the binding scope is a Python lambda,
# the bound variable is the lambda's parameter.
#
# Internally we store the body as a static Expr (with a Var node
# substituted for the binding), not as a closure. This keeps the AST
# pure-data for serialization, mutation, and traversal, while still
# letting the user write Let.make(value, lambda v: body_using(v)).

@dataclass(frozen=True)
class Var(Expr[T], Generic[T]):
    """Reference to a let-bound variable.

    The type parameter T is a phantom — it carries no runtime data.
    Mypy will check uses of Var[T] against contexts expecting Expr[T],
    but cannot verify that the binding actually produces a T at
    construction time. Runtime type checks (or property tests) can
    catch mismatches.
    """
    name: str


@dataclass(frozen=True)
class Let(Expr[T2], Generic[T1, T2]):
    """Bind a value to a name within a body expression.

    Type: Expr[T1] -> (Expr[T1] -> Expr[T2]) -> Expr[T2]

    Constructed via Let.make(value, lambda v: body_using(v)).
    The lambda captures the binding by Python closure; we
    immediately apply it to a fresh Var to get a static body.
    """
    var_name: str
    value: Expr[T1]
    body: Expr[T2]

    @classmethod
    def make(
        cls,
        value: Expr[T1],
        body_fn: Callable[[Expr[T1]], Expr[T2]],
        hint: str = "v",
    ) -> "Let[T1, T2]":
        """Construct a Let using a closure for the body.

        The body_fn receives a fresh Var of the same type as the value,
        and returns an Expr that uses it. This is HOAS — the binding
        is expressed as a Python function, not by manual variable
        management.
        """
        var_name = _fresh_var_name(hint)
        var: Var[T1] = Var(name=var_name)
        body = body_fn(var)
        return cls(var_name=var_name, value=value, body=body)
