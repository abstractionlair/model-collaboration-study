"""Experiment specification layer.

Maps an IR protocol expression plus concrete inputs (models, prompts,
tasks, budgets) into a runnable experiment. This is Layer 3 of the
three-layer architecture described in docs/design/system-architecture.md.
"""

from .spec import (
    BudgetTier,
    ConditionSpec,
    ExperimentSpec,
    PricingEntry,
    PricingTable,
    PromptTemplates,
    RetryPolicy,
    Stratum,
    TaskBucket,
)

__all__ = [
    "BudgetTier",
    "ConditionSpec",
    "ExperimentSpec",
    "PricingEntry",
    "PricingTable",
    "PromptTemplates",
    "RetryPolicy",
    "Stratum",
    "TaskBucket",
]
