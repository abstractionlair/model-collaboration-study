"""Phase 1 experiment specification builder.

Constructs a concrete ExperimentSpec for the Phase 1 matrix:
conditions A/B/C/D/D'/E at their respective budget tiers, against
the three committed task buckets (SWE-bench Verified, LiveCodeBench,
BFCL) stratified by difficulty.

Model IDs and pricing are pinned at kickoff. The builder takes
these as inputs and produces the fully-resolved spec.
"""

from __future__ import annotations

from src.experiment.prompts import DEFAULT_PROMPTS
from src.experiment.spec import (
    BudgetTier,
    ConditionSpec,
    ExperimentSpec,
    PHASE1_STRATA,
    PricingEntry,
    PricingTable,
    RetryPolicy,
    TaskBucket,
)
from src.protocols.conditions import (
    condition_a,
    condition_b,
    condition_c,
    condition_d,
    condition_d_prime,
    condition_e,
)


# ============================================================================
# Phase 1 subject models
# ============================================================================

# Concrete model IDs — verify against vendor docs before kickoff.
GPT_MINI = "gpt-5.4-mini"
HAIKU = "claude-haiku-4-5"
FLASH = "gemini-2.5-flash"

SUBJECT_MODELS = [GPT_MINI, HAIKU, FLASH]

# Phase 1 pricing anchors (USD per 1M tokens in/out).
# Captured during exploratory phase — MUST be re-verified at kickoff.
PHASE1_PRICING = PricingTable(
    entries={
        GPT_MINI: PricingEntry(GPT_MINI, input_per_1m=0.75, output_per_1m=4.50),
        HAIKU: PricingEntry(HAIKU, input_per_1m=1.00, output_per_1m=5.00),
        FLASH: PricingEntry(FLASH, input_per_1m=0.30, output_per_1m=2.50),
    }
)


# ============================================================================
# Phase 1 task buckets
# ============================================================================

PHASE1_TASKS = [
    TaskBucket(benchmark="swe-bench-verified"),
    TaskBucket(benchmark="livecodebench"),
    TaskBucket(benchmark="bfcl"),
]


# ============================================================================
# Condition builder
# ============================================================================

def _best_model() -> str:
    """The best single subject model for baselines A and B.

    Determined empirically during calibration. Placeholder: use
    the most expensive model (Haiku) as a conservative default.
    Update after calibration runs.
    """
    return HAIKU


def _n_samples_for_b(tier: BudgetTier) -> int:
    """How many samples B generates at each budget tier.

    Rough heuristic: at $X, one gen + one score ≈ 1.5× the cost
    of A, so N=1 is a sanity check (scoring overhead only). At
    higher tiers, scale linearly. Exact N will be refined during
    calibration when actual per-call costs are measured.
    """
    return {BudgetTier.X: 1, BudgetTier.TWO_X: 3, BudgetTier.FOUR_X: 6}[tier]


def build_phase1_conditions() -> list[ConditionSpec]:
    """Build all Phase 1 condition-tier pairs."""
    best = _best_model()
    conditions: list[ConditionSpec] = []

    # A: single-model, one pass. Only at $X.
    conditions.append(ConditionSpec(
        name="A",
        label="Single-model, one pass",
        protocol=condition_a(best),
        budget_tier=BudgetTier.X,
        models=[best],
    ))

    # B: single-model repeat-and-aggregate. All three tiers.
    for tier in BudgetTier:
        n = _n_samples_for_b(tier)
        conditions.append(ConditionSpec(
            name="B",
            label=f"Single-model repeat-and-aggregate (N={n})",
            protocol=condition_b(best, n),
            budget_tier=tier,
            models=[best],
        ))

    # C: heterogeneous parallel + peer-LLM aggregation. $2X and $4X.
    # Judge is drawn from the subject pool (peer-LLM, not external).
    judge = best  # the best model also judges
    for tier in [BudgetTier.TWO_X, BudgetTier.FOUR_X]:
        conditions.append(ConditionSpec(
            name="C",
            label="Heterogeneous parallel + peer-LLM aggregation",
            protocol=condition_c(SUBJECT_MODELS, judge),
            budget_tier=tier,
            models=SUBJECT_MODELS,
        ))

    # D: heterogeneous ReConcile-style. $2X and $4X.
    for tier in [BudgetTier.TWO_X, BudgetTier.FOUR_X]:
        conditions.append(ConditionSpec(
            name="D",
            label="Heterogeneous ReConcile-style",
            protocol=condition_d(SUBJECT_MODELS, n_rounds=1),
            budget_tier=tier,
            models=SUBJECT_MODELS,
        ))

    # D': homogeneous ReConcile-style. $2X and $4X.
    pool_size = len(SUBJECT_MODELS)
    for tier in [BudgetTier.TWO_X, BudgetTier.FOUR_X]:
        conditions.append(ConditionSpec(
            name="D'",
            label="Homogeneous ReConcile-style",
            protocol=condition_d_prime(best, pool_size, n_rounds=1),
            budget_tier=tier,
            models=[best],
        ))

    # E: hierarchical synthesis. $2X and $4X.
    # Meta-reviewer drawn from the subject pool.
    meta_reviewer = best
    for tier in [BudgetTier.TWO_X, BudgetTier.FOUR_X]:
        conditions.append(ConditionSpec(
            name="E",
            label="Hierarchical synthesis",
            protocol=condition_e(SUBJECT_MODELS, meta_reviewer),
            budget_tier=tier,
            models=SUBJECT_MODELS,
        ))

    return conditions


def build_phase1_spec(
    base_cost_x: float | None = None,
    seeds: int = 5,
) -> ExperimentSpec:
    """Build the complete Phase 1 experiment specification.

    Args:
        base_cost_x: The $X anchor (average cost of Condition A on
            one task instance). None if not yet calibrated.
        seeds: Number of random seeds per condition-tier pair.
    """
    return ExperimentSpec(
        name="phase1-method-validation",
        conditions=build_phase1_conditions(),
        task_buckets=PHASE1_TASKS,
        strata=PHASE1_STRATA,
        pricing=PHASE1_PRICING,
        prompts=DEFAULT_PROMPTS,
        base_cost_x=base_cost_x,
        seeds=seeds,
        retry_policy=RetryPolicy(),
    )
