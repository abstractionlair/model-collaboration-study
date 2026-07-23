"""Phase 1 experiment specification builder.

Constructs a concrete ExperimentSpec for the Phase 1 matrix:
conditions A/B/C/D/D'/E at their respective budget tiers, against
the two committed task buckets (SWE-bench Verified, LiveCodeBench)
stratified by difficulty. BFCL was dropped from Phase 1 by the
2026-07-04 kickoff decisions (`docs/decisions.md`); function-calling
coverage may return in Phase 1.5.

**Calibration contract.** The builder takes calibration results
as required arguments — no defaults for `best_model`,
`n_samples_for_b`, or `pricing`. Previous versions had
placeholder defaults (Haiku as "conservative" best-model,
hand-picked 1/3/6 sample counts, hardcoded pricing "verify
before kickoff"); round-1 reviewers flagged these as footguns
because a caller running pre-calibration could quietly violate
the matched-budget discipline. Requiring explicit args forces
the caller to have real values.

Module constants remain for convenience (`GPT_MINI`, `HAIKU`,
`FLASH`, `SUBJECT_MODELS`, `PHASE1_PRICING_DRAFT`,
`PHASE1_STRATA`), but using them is an explicit choice the
caller makes.
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
# Per the 2026-07-04 kickoff decisions (`docs/decisions.md`):
# gemini-2.5-flash replaced by Gemini 3 Flash. The API serves it
# only under the `-preview` suffix (verified against the live
# ListModels endpoint 2026-07-23; bare `gemini-3-flash` 404s).
FLASH = "gemini-3-flash-preview"

SUBJECT_MODELS = [GPT_MINI, HAIKU, FLASH]

# Pricing anchors. All three entries verified against current
# vendor-published rates on 2026-07-23 (gpt-5.4-mini $0.75/$4.50,
# claude-haiku-4-5 $1.00/$5.00, gemini-3-flash $0.50/$3.00).
# The `_DRAFT` suffix is retained deliberately: rates drift, and
# callers of `build_phase1_spec` must still make an explicit
# choice to trust these numbers (re-verify if meaningful time has
# passed since the date above).
PHASE1_PRICING_DRAFT = PricingTable(
    entries={
        GPT_MINI: PricingEntry(GPT_MINI, input_per_1m=0.75, output_per_1m=4.50),
        HAIKU: PricingEntry(HAIKU, input_per_1m=1.00, output_per_1m=5.00),
        # Confirmed against published gemini-3-flash rates 2026-07-23
        # (two independent pricing trackers agree: $0.50 in / $3.00 out
        # per 1M tokens). Replaces the stale gemini-2.5-flash carry-over
        # ($0.30 / $2.50) that rode along with the 2026-07-04 model swap.
        FLASH: PricingEntry(FLASH, input_per_1m=0.50, output_per_1m=3.00),
    }
)


# ============================================================================
# Phase 1 task buckets
# ============================================================================

# BFCL dropped from Phase 1 per the 2026-07-04 kickoff decisions
# (`docs/decisions.md`): SWE-bench's 500-instance ceiling forces the
# uniform middle-band fallback structurally, and BFCL's saturation
# added noise rather than signal. The adapter (`benchmarks/bfcl.py`)
# is retained for a possible Phase 1.5 `live_*` expansion.
PHASE1_TASKS = [
    TaskBucket(benchmark="swe-bench-verified"),
    TaskBucket(benchmark="livecodebench"),
]


# ============================================================================
# Condition builder
# ============================================================================


def build_phase1_conditions(
    *,
    best_model: str,
    n_samples_for_b: dict[BudgetTier, int],
    subject_models: list[str] = SUBJECT_MODELS,
) -> list[ConditionSpec]:
    """Build all Phase 1 condition-tier pairs.

    Args:
        best_model: The best single subject model — determined by
            calibration, used for A, B, and as the judge in C,
            the pool for D', and the meta-reviewer in E. No
            default: pre-calibration callers would otherwise
            silently use a wrong baseline.
        n_samples_for_b: N per budget tier for Condition B.
            Must cover BudgetTier.X, BudgetTier.TWO_X,
            BudgetTier.FOUR_X. Determined by calibration against
            real per-call costs; no default because hand-picked
            values (1/3/6 was the previous placeholder) can
            violate the $X-cap discipline.
        subject_models: The N-model subject pool. Defaults to
            the module-level SUBJECT_MODELS constant; override
            for ablations.

    Raises:
        ValueError: if n_samples_for_b is missing any tier, or
            if best_model is not in the subject_models pool
            (C's judge and D's pool must be peer-LLMs).
    """
    missing = {BudgetTier.X, BudgetTier.TWO_X, BudgetTier.FOUR_X} - set(
        n_samples_for_b
    )
    if missing:
        raise ValueError(
            f"n_samples_for_b must cover all budget tiers; "
            f"missing {sorted(t.value for t in missing)}"
        )
    if best_model not in subject_models:
        raise ValueError(
            f"best_model {best_model!r} must be in subject_models "
            f"{subject_models!r} (the judge in C and meta-reviewer "
            f"in E are drawn from the pool as peer-LLMs)"
        )

    conditions: list[ConditionSpec] = []

    # A: single-model, one pass. Only at $X.
    conditions.append(ConditionSpec(
        name="A",
        label="Single-model, one pass",
        protocol=condition_a(best_model),
        budget_tier=BudgetTier.X,
        models=[best_model],
    ))

    # B: single-model repeat-and-aggregate. All three tiers.
    for tier in BudgetTier:
        n = n_samples_for_b[tier]
        conditions.append(ConditionSpec(
            name="B",
            label=f"Single-model repeat-and-aggregate (N={n})",
            protocol=condition_b(best_model, n),
            budget_tier=tier,
            models=[best_model],
        ))

    # C: heterogeneous parallel + peer-LLM aggregation. $2X and $4X.
    # Judge is drawn from the subject pool (peer-LLM, not external).
    judge = best_model
    for tier in [BudgetTier.TWO_X, BudgetTier.FOUR_X]:
        conditions.append(ConditionSpec(
            name="C",
            label="Heterogeneous parallel + peer-LLM aggregation",
            protocol=condition_c(subject_models, judge),
            budget_tier=tier,
            models=subject_models,
        ))

    # D: heterogeneous ReConcile-style. $2X and $4X.
    for tier in [BudgetTier.TWO_X, BudgetTier.FOUR_X]:
        conditions.append(ConditionSpec(
            name="D",
            label="Heterogeneous ReConcile-style",
            protocol=condition_d(subject_models, n_rounds=1),
            budget_tier=tier,
            models=subject_models,
        ))

    # D': homogeneous ReConcile-style. $2X and $4X.
    pool_size = len(subject_models)
    for tier in [BudgetTier.TWO_X, BudgetTier.FOUR_X]:
        conditions.append(ConditionSpec(
            name="D'",
            label="Homogeneous ReConcile-style",
            protocol=condition_d_prime(best_model, pool_size, n_rounds=1),
            budget_tier=tier,
            models=[best_model],
        ))

    # E: hierarchical synthesis. $2X and $4X.
    # Meta-reviewer drawn from the subject pool.
    meta_reviewer = best_model
    for tier in [BudgetTier.TWO_X, BudgetTier.FOUR_X]:
        conditions.append(ConditionSpec(
            name="E",
            label="Hierarchical synthesis",
            protocol=condition_e(subject_models, meta_reviewer),
            budget_tier=tier,
            models=subject_models,
        ))

    return conditions


def build_phase1_spec(
    *,
    best_model: str,
    n_samples_for_b: dict[BudgetTier, int],
    pricing: PricingTable,
    subject_models: list[str] = SUBJECT_MODELS,
    base_cost_x: float | None = None,
    seeds: int = 5,
) -> ExperimentSpec:
    """Build the complete Phase 1 experiment specification.

    All calibration-dependent parameters are required arguments.
    See `build_phase1_conditions` for the rationale.

    Args:
        best_model: The best single subject model (calibrated).
        n_samples_for_b: N per budget tier for Condition B.
        pricing: PricingTable with entries for every model in
            subject_models. No default — the "verify before
            kickoff" discipline requires the caller to have
            confirmed rates against current vendor docs. Use
            `PHASE1_PRICING_DRAFT` as a starting point if the
            rates still match reality.
        subject_models: Defaults to SUBJECT_MODELS.
        base_cost_x: The $X anchor (average cost of Condition A
            on one task instance). None if not yet calibrated;
            compute from a dry run and re-invoke.
        seeds: Number of random seeds per condition-tier pair.
    """
    for m in subject_models:
        if m not in pricing.entries:
            raise ValueError(
                f"pricing table missing entry for subject model {m!r}"
            )

    return ExperimentSpec(
        name="phase1-method-validation",
        conditions=build_phase1_conditions(
            best_model=best_model,
            n_samples_for_b=n_samples_for_b,
            subject_models=subject_models,
        ),
        task_buckets=PHASE1_TASKS,
        strata=PHASE1_STRATA,
        pricing=pricing,
        prompts=DEFAULT_PROMPTS,
        base_cost_x=base_cost_x,
        seeds=seeds,
        retry_policy=RetryPolicy(),
    )
