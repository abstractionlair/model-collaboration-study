"""Runtime value types.

These are the concrete values that flow through the executor as it
walks an AST. They mirror the abstract IR types (Query, Answer,
Critique, Score) but carry actual content — text, floats, and a
small amount of provenance — rather than acting as type tags.

The stage marker on RAnswer (Draft vs Final) is kept so the
executor can assert that only finalized answers are returned to
callers, matching the IR's Answer[Draft] vs Answer[Final]
distinction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.ir.types import Draft, Final


@dataclass(frozen=True)
class RQuery:
    text: str


@dataclass(frozen=True)
class RAnswer:
    text: str
    stage: Any  # Draft or Final class (phantom tag lifted to runtime)
    # production_query is the query text that produced this answer.
    # It's the one piece of provenance a WITH_PRODUCTION reviewer
    # needs; keeping it on the value avoids threading an execution
    # log through the interpreter.
    production_query: str = ""


@dataclass(frozen=True)
class RCritique:
    text: str


@dataclass(frozen=True)
class RScore:
    value: float


def assert_final(a: RAnswer) -> RAnswer:
    if a.stage is not Final:
        raise TypeError(f"Expected Final answer, got stage={a.stage.__name__}")
    return a
