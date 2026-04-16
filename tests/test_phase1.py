"""Tests for Phase 1 builder calibration gates.

Previously `build_phase1_conditions()` and `build_phase1_spec()`
built a runnable spec from hardcoded placeholder values
(`_best_model()` returning Haiku, `_n_samples_for_b()` picking
1/3/6 by hand, `PHASE1_PRICING` baked in). Running against
placeholders would silently violate the matched-budget
discipline. These tests pin the new behavior: all calibration
parameters are required, and obviously wrong combinations
fail loudly.
"""

from __future__ import annotations

import pytest

from src.experiment.phase1 import (
    HAIKU,
    PHASE1_PRICING_DRAFT,
    SUBJECT_MODELS,
    build_phase1_conditions,
    build_phase1_spec,
)
from src.experiment.spec import BudgetTier


VALID_N_SAMPLES = {
    BudgetTier.X: 1,
    BudgetTier.TWO_X: 3,
    BudgetTier.FOUR_X: 6,
}


def test_build_conditions_requires_all_tiers() -> None:
    """Missing a budget tier in n_samples_for_b raises ValueError
    at build time, not silently later."""
    incomplete = {BudgetTier.X: 1, BudgetTier.TWO_X: 3}
    with pytest.raises(ValueError, match="missing"):
        build_phase1_conditions(
            best_model=HAIKU, n_samples_for_b=incomplete,
        )


def test_build_conditions_requires_best_model_in_pool() -> None:
    """best_model must be in subject_models; C's judge and E's
    meta-reviewer are peer-LLMs drawn from the subject pool."""
    with pytest.raises(ValueError, match="must be in subject_models"):
        build_phase1_conditions(
            best_model="not-a-subject-model",
            n_samples_for_b=VALID_N_SAMPLES,
        )


def test_build_conditions_succeeds_with_explicit_calibration() -> None:
    """With all required args provided and consistent, the builder
    produces the expected 12 condition-tier pairs."""
    conditions = build_phase1_conditions(
        best_model=HAIKU,
        n_samples_for_b=VALID_N_SAMPLES,
    )
    # A (1 tier) + B (3 tiers) + C (2 tiers) + D (2 tiers) +
    # D' (2 tiers) + E (2 tiers) = 12
    assert len(conditions) == 12
    names = sorted({c.name for c in conditions})
    assert names == ["A", "B", "C", "D", "D'", "E"]


def test_build_spec_requires_pricing_argument() -> None:
    """No default for pricing — the 'verify before kickoff'
    discipline requires the caller to explicitly pass one."""
    # build_phase1_spec requires pricing as a kw-arg; calling
    # without it is a TypeError, not a silent default.
    with pytest.raises(TypeError):
        build_phase1_spec(  # type: ignore[call-arg]
            best_model=HAIKU,
            n_samples_for_b=VALID_N_SAMPLES,
        )


def test_build_spec_checks_pricing_covers_subject_models() -> None:
    """If subject_models includes a model with no pricing entry,
    fail loudly rather than silently producing an un-costable spec."""
    from src.experiment.spec import PricingEntry, PricingTable

    partial_pricing = PricingTable(
        entries={
            HAIKU: PricingEntry(HAIKU, 1.0, 5.0),
            # missing GPT_MINI and FLASH
        }
    )
    with pytest.raises(ValueError, match="missing entry"):
        build_phase1_spec(
            best_model=HAIKU,
            n_samples_for_b=VALID_N_SAMPLES,
            pricing=partial_pricing,
        )


def test_build_spec_succeeds_with_explicit_draft_pricing() -> None:
    """End-to-end construction with all required args produces
    a valid ExperimentSpec."""
    spec = build_phase1_spec(
        best_model=HAIKU,
        n_samples_for_b=VALID_N_SAMPLES,
        pricing=PHASE1_PRICING_DRAFT,
    )
    assert spec.name == "phase1-method-validation"
    assert len(spec.conditions) == 12
    for m in SUBJECT_MODELS:
        assert m in spec.pricing.entries
