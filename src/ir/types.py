"""Protocol IR — type definitions.

This is a first sketch of a typed AST for multi-model collaboration
protocols, based on the design discussion in docs/discussions/dsl-design-context.md.

Design goals:
- Types encode stage and role, not just data shape.
- Parameterized judgment types (Critique[T]) prevent cross-target
  substitution in mutations.
- Every AST node has a statically known result type via Generic[T].
- Python typed AST with Haskell-shaped design, not Python pretending
  to be Haskell.

This is the minimum type set needed to express Cross-Context Review
(CCR) and its same-session baselines. Expand as more protocols are
added.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Generic, TypeVar


# ============================================================================
# Stage tags (type-level markers for Answer lifecycle)
# ============================================================================
# These are nominal types used as phantom type parameters on Answer.
# An Answer[Draft] is in-progress and subject to revision; an Answer[Final]
# has been committed. Mutations can't accidentally feed a draft into a
# step that expects a final answer (or vice versa) because the type
# parameters don't match.

class Draft:
    """Stage tag: in-progress response, candidate for revision."""
    pass


class Final:
    """Stage tag: committed response, not subject to further revision."""
    pass


class Plan:
    """Stage tag: a pre-response plan or decomposition."""
    pass


# Type variable for stage
S = TypeVar("S", Draft, Final, Plan)


# ============================================================================
# Semantic value types
# ============================================================================
# These represent the kinds of data that flow through a protocol.
# They are parameterized by target where meaningful — Critique[Answer[Draft]]
# is distinct from Critique[Answer[Final]] even though both carry textual
# feedback. This prevents a mutation engine from substituting one for the
# other.

T = TypeVar("T")


@dataclass(frozen=True)
class Query:
    """The original task posed to the protocol."""
    pass


@dataclass(frozen=True)
class Answer(Generic[S]):
    """A response, tagged with its stage (Draft, Final, etc.).

    The S parameter is a phantom type — it carries no runtime data.
    It exists to let the type checker distinguish draft answers from
    final answers.
    """
    pass


@dataclass(frozen=True)
class Critique(Generic[T]):
    """Feedback targeting T.

    Critique[Answer[Draft]] and Critique[Answer[Final]] are distinct
    types. A mutation that substitutes one for the other will fail
    type checking.
    """
    pass


@dataclass(frozen=True)
class Flag(Generic[T]):
    """Structured problem marker (location + label, no rationale).

    A nominal subtype of Critique conceptually; in Python generics
    we express the relationship via runtime validation rather than
    true subtyping, since Python's variance story is weak.
    """
    pass


@dataclass(frozen=True)
class Score(Generic[T]):
    """Numeric quality signal for T."""
    pass


# ============================================================================
# Protocol-level annotations
# ============================================================================
# These are not types in the strict sense — they're enum-valued
# parameters on primitives. They affect the protocol's semantics
# (what the reviewer sees, whether context is fresh) but don't
# change type signatures. Mutations can flip these freely; they're
# the main structural knobs for protocols like CCR.

class ContextMode(Enum):
    """Whether a step runs in a fresh context or inherits history."""
    FRESH = "fresh"                # no prior history visible
    ACCUMULATED = "accumulated"    # inherits session context


class Visibility(Enum):
    """What a reviewer or judge can see alongside the target artifact."""
    ARTIFACT_ONLY = "artifact_only"          # only the thing being reviewed
    WITH_PRODUCTION = "with_production"      # artifact + how it was produced
    PEERS_GROUPED = "peers_grouped"          # artifact + peer answers grouped
    ALL = "all"                              # everything
