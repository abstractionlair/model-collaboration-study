"""Cross-Context Review (CCR) and same-session baselines.

Expresses the protocols tested in:
  Song, 2026. "Cross-Context Review: Improving LLM Output Quality by
  Separating Production and Review Sessions."

The paper compares four variants that differ only in the review step's
context and visibility. In the typed IR, they share the same structural
shape and differ only in annotation values on the review step.
"""

from __future__ import annotations

from src.ir.surface import (
    ACCUMULATED,
    ALL_VISIBLE,
    ARTIFACT_ONLY,
    FRESH,
    WITH_PRODUCTION,
    finalize,
    gen,
    query,
    review,
    revise,
)
from src.ir.types import Answer, Final
from src.ir.ast import Expr


def ccr(model: str) -> Expr[Answer[Final]]:
    """Cross-Context Review: review in a fresh context, artifact only."""
    q = query()
    d = gen(model, q)
    return finalize(revise(model, d, review(model, d, FRESH, ARTIFACT_ONLY)))


def sr(model: str) -> Expr[Answer[Final]]:
    """Same-session review: reviewer inherits full accumulated context."""
    q = query()
    d = gen(model, q)
    return finalize(revise(model, d, review(model, d, ACCUMULATED, ALL_VISIBLE)))


def sa(model: str) -> Expr[Answer[Final]]:
    """Subagent review: fresh context, but production prompt visible."""
    q = query()
    d = gen(model, q)
    return finalize(revise(model, d, review(model, d, FRESH, WITH_PRODUCTION)))
