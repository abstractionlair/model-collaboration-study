"""Core types for the experiment specification layer.

An ExperimentSpec fully determines a runnable experiment: which
macro-model conditions to compare, on which tasks, at what dollar
budgets, with which prompt templates. A single IR protocol
definition (e.g. ReConcile) can be instantiated into many different
ConditionSpecs by varying the model pool, round count, or budget.

All dollar amounts are in USD. Pricing is pinned at experiment
kickoff and verified before each run batch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.ir.ast import Expr


# ============================================================================
# Budget
# ============================================================================

class BudgetTier(Enum):
    """Dollar-denominated budget tiers, anchored to Condition A cost.

    Each tier is a cap, not an exact spend target. Macro-models that
    spend less than the cap are rewarded in the dollars-per-solved-task
    metric.
    """
    X = "1x"       # cost of one single-model pass (Condition A)
    TWO_X = "2x"   # 2× the single-model cost
    FOUR_X = "4x"  # 4× the single-model cost

    @property
    def multiplier(self) -> int:
        return {BudgetTier.X: 1, BudgetTier.TWO_X: 2, BudgetTier.FOUR_X: 4}[self]


# ============================================================================
# Pricing
# ============================================================================

@dataclass(frozen=True)
class PricingEntry:
    """Per-model pricing anchor. Captured at kickoff, verified per run."""
    model_id: str
    input_per_1m: float    # USD per 1M input tokens
    output_per_1m: float   # USD per 1M output tokens


@dataclass(frozen=True)
class PricingTable:
    """Pinned pricing for all models in the experiment.

    Prices are pinned at kickoff because vendor pricing changes are
    the most common reason runs become non-comparable across weeks.
    """
    entries: dict[str, PricingEntry]

    def cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """Compute the dollar cost of a single model call."""
        e = self.entries[model_id]
        return (
            (input_tokens / 1_000_000) * e.input_per_1m
            + (output_tokens / 1_000_000) * e.output_per_1m
        )

    def budget_cap(self, tier: BudgetTier, base_cost_x: float) -> float:
        """Dollar cap for a given tier, anchored to the $X baseline."""
        return base_cost_x * tier.multiplier


# ============================================================================
# Task configuration
# ============================================================================

@dataclass(frozen=True)
class Stratum:
    """A difficulty stratum defined by one-shot success rate band.

    The strata exist because the research question asks *when* —
    not just whether — a protocol outperforms. The strata hypothesis
    predicts opposing effects across strata: degradation on easy,
    improvement on middle, null on hard.
    """
    name: str           # "easy", "middle", "hard"
    success_low: float  # lower bound of one-shot success rate
    success_high: float # upper bound of one-shot success rate


# Committed Phase 1 strata
EASY = Stratum("easy", 0.60, 0.70)
MIDDLE = Stratum("middle", 0.45, 0.55)
HARD = Stratum("hard", 0.30, 0.40)
PHASE1_STRATA = [EASY, MIDDLE, HARD]


@dataclass(frozen=True)
class TaskBucket:
    """A benchmark + its task instances, stratified by difficulty.

    Instance IDs are determined during calibration: run the best
    subject model once on the full benchmark, then bin instances by
    observed success rate into the strata.
    """
    benchmark: str         # "swe-bench-verified", "livecodebench", "bfcl"
    instance_ids: list[str] = field(default_factory=list)  # empty = all


# ============================================================================
# Prompt templates
# ============================================================================

@dataclass(frozen=True)
class PromptTemplates:
    """Prompt templates for each step type in the executor.

    These replace the placeholder strings currently inlined in
    src/executor/interpreter.py. Template variables use Python
    str.format() syntax: {query}, {draft}, {critique}, {peers},
    {drafts}.

    The default structured-critique format is the baseline for
    Phase 1. The critique-format axis (free-form vs structured
    flags vs flag-only) is a follow-on ablation.
    """
    gen_system: str               # system prompt for FRESH context
    accumulated_system: str       # system prompt for ACCUMULATED context
    gen_user: str                 # expects {query}
    review_artifact: str          # expects {draft}
    review_with_production: str   # expects {query}, {draft}
    review_peers: str             # expects {draft}, {peers}
    review_all: str               # expects {query}, {draft}, {peers}
    revise_user: str              # expects {draft}, {critique}
    fuse_user: str                # expects {query}, {drafts}
    score_user: str               # expects {draft}


# ============================================================================
# Retry / infra-failure policy
# ============================================================================

@dataclass(frozen=True)
class RetryPolicy:
    """How to handle infrastructure failures.

    Infrastructure failures (Docker, network, rate limits) are retried
    and do not count against the dollar budget. Capability failures
    are scored normally.
    """
    max_retries: int = 3
    backoff_base_seconds: float = 1.0
    backoff_max_seconds: float = 60.0


# ============================================================================
# Condition specification
# ============================================================================

@dataclass(frozen=True)
class ConditionSpec:
    """A fully-specified experimental condition at a specific budget tier.

    Each ConditionSpec is one cell of the experiment matrix: a
    concrete macro-model (IR expression with models baked in),
    at a specific budget cap, ready to run against a task suite.
    """
    name: str              # "A", "B", "C", "D", "D'", "E"
    label: str             # human-readable, e.g. "Single-model, one pass"
    protocol: Expr[Any]    # fully-built IR expression with concrete model names
    budget_tier: BudgetTier
    models: list[str]      # concrete model IDs used (for reference / cost tracking)


# ============================================================================
# Experiment specification
# ============================================================================

@dataclass(frozen=True)
class ExperimentSpec:
    """Complete specification for a Phase 1 experiment run.

    Everything needed to execute the experiment matrix, minus the
    task instance data itself (which lives in benchmark repos).
    """
    name: str
    conditions: list[ConditionSpec]
    task_buckets: list[TaskBucket]
    strata: list[Stratum]
    pricing: PricingTable
    prompts: PromptTemplates
    base_cost_x: float | None  # $X, computed from Condition A runs or pre-set
    seeds: int = 5
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
