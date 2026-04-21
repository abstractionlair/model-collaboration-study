#!/usr/bin/env python3
"""Framework-validation run against a HumanEval subset.

Runs Condition A (single-model, one pass) with each of the
three Phase 1 subject models plus Condition D (heterogeneous
ReConcile-style peer-review) and Condition E (hierarchical
synthesis via meta-reviewer). The goal is proof-of-life on the
framework, not a research result: HumanEval is heavily
contaminated in training data, so near-ceiling pass rates on
A runs just mean the pipeline works.

Writes a results log to `data/mini_bench_runs/` with a
timestamped filename.

Usage:
    # Load API keys first (vault collection or env vars)
    vault exec anthropic,openai,google,xai -- python3 scripts/run_humaneval.py

    # Or with a specific task subset:
    python3 scripts/run_humaneval.py --tasks HumanEval/0,HumanEval/1,HumanEval/2

    # Or with more/fewer tasks:
    python3 scripts/run_humaneval.py --count 5
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.executor import ApiClient
from src.experiment.benchmarks import HumanEvalBench
from src.experiment.phase1 import (
    FLASH,
    GPT_MINI,
    HAIKU,
    PHASE1_PRICING_DRAFT,
    SUBJECT_MODELS,
)
from src.experiment.runner import ConditionResults, run_condition
from src.experiment.spec import BudgetTier, ConditionSpec
from src.protocols.conditions import (
    condition_a,
    condition_d,
    condition_e,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "data" / "mini_bench_runs"


def available_providers() -> set[str]:
    avail = set()
    if os.environ.get("ANTHROPIC_API_KEY"):
        avail.add("anthropic")
    if os.environ.get("OPENAI_API_KEY"):
        avail.add("openai")
    if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        avail.add("google")
    if os.environ.get("XAI_API_KEY"):
        avail.add("xai")
    return avail


def model_provider(model: str) -> str:
    if model.startswith("claude"):
        return "anthropic"
    if model.startswith("gpt"):
        return "openai"
    if model.startswith("gemini"):
        return "google"
    if model.startswith("grok"):
        return "xai"
    return "unknown"


def format_summary(results: list[ConditionResults]) -> str:
    lines = []
    header = f"{'Condition':<40}  {'Pass':>6}  {'Abort':>5}  {'Dollars':>9}"
    lines.append(header)
    lines.append("-" * len(header))
    for cr in results:
        n = len(cr.task_results)
        passed = sum(1 for r in cr.task_results if r.passed)
        lines.append(
            f"{cr.condition_name:<40}  "
            f"{passed:>3}/{n:<2}  "
            f"{cr.abort_count:>5}  "
            f"${cr.total_dollars:>7.3f}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--count", type=int, default=10,
        help="Number of HumanEval problems to use (default: 10).",
    )
    parser.add_argument(
        "--tasks", type=str, default=None,
        help="Comma-separated task IDs to use (overrides --count).",
    )
    parser.add_argument(
        "--seed", type=int, default=0,
        help="Seed for the interpreter RNG (tie-breaks, fallbacks).",
    )
    parser.add_argument(
        "--skip-d-and-e", action="store_true",
        help="Only run Condition A with each model (cheaper smoke test).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("run_humaneval")

    providers = available_providers()
    if not providers:
        logger.error(
            "No API keys found. Set at least one of "
            "ANTHROPIC_API_KEY / OPENAI_API_KEY / GOOGLE_API_KEY / "
            "XAI_API_KEY (or run via vault).",
        )
        return 1

    # Subset tasks
    if args.tasks:
        task_ids = [t.strip() for t in args.tasks.split(",") if t.strip()]
    else:
        task_ids = [f"HumanEval/{i}" for i in range(args.count)]
    benchmark = HumanEvalBench(task_ids=task_ids)
    logger.info(
        "Running against %d HumanEval tasks: %s",
        len(task_ids), ", ".join(task_ids[:5]) + ("..." if len(task_ids) > 5 else ""),
    )

    # Only run Conditions requiring providers we actually have.
    subject_models = [m for m in SUBJECT_MODELS if model_provider(m) in providers]
    if not subject_models:
        logger.error("No subject models available given current API keys.")
        return 1
    logger.info("Available subject models: %s", subject_models)

    # Build conditions
    condition_specs: list[ConditionSpec] = []
    # Condition A with each available subject model
    for model in subject_models:
        condition_specs.append(ConditionSpec(
            name=f"A ({model})",
            label=f"Single-model one pass, {model}",
            protocol=condition_a(model),
            budget_tier=BudgetTier.X,
            models=[model],
        ))

    if not args.skip_d_and_e and len(subject_models) >= 2:
        # Condition D (heterogeneous ReConcile)
        condition_specs.append(ConditionSpec(
            name=f"D ({'+'.join(subject_models)})",
            label="Heterogeneous ReConcile-style, 1 round",
            protocol=condition_d(subject_models, n_rounds=1),
            budget_tier=BudgetTier.TWO_X,
            models=subject_models,
        ))
        # Condition E (hierarchical synthesis)
        # Meta-reviewer is the first available model.
        meta = subject_models[0]
        condition_specs.append(ConditionSpec(
            name=f"E ({'+'.join(subject_models)}, meta={meta})",
            label="Hierarchical synthesis, 1 round",
            protocol=condition_e(subject_models, meta),
            budget_tier=BudgetTier.TWO_X,
            models=subject_models,
        ))

    logger.info("Running %d conditions", len(condition_specs))

    # Fresh client per condition so per-task call slicing is clean
    # and conditions don't share ApiClient state.
    all_results: list[ConditionResults] = []
    t0 = time.monotonic()
    for cond in condition_specs:
        logger.info("Running condition: %s", cond.name)
        client = ApiClient()  # temperature=None → vendor defaults
        cr = run_condition(
            cond, benchmark, client, PHASE1_PRICING_DRAFT, seed=args.seed,
        )
        all_results.append(cr)

    elapsed = time.monotonic() - t0

    # Summary
    summary = format_summary(all_results)
    print()
    print("=" * 70)
    print(f"Results (elapsed: {elapsed:.1f}s)")
    print("=" * 70)
    print(summary)

    # Write results log
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    log_path = OUTPUT_DIR / f"humaneval-{ts}.json"
    log_data = {
        "timestamp": ts,
        "task_ids": task_ids,
        "seed": args.seed,
        "available_providers": sorted(providers),
        "subject_models": subject_models,
        "elapsed_seconds": elapsed,
        "conditions": [
            {
                "name": cr.condition_name,
                "pass_rate": cr.pass_rate,
                "abort_count": cr.abort_count,
                "total_dollars": cr.total_dollars,
                "tasks": [
                    {
                        "task_id": r.task_id,
                        "passed": r.passed,
                        "fraction": r.fraction,
                        "detail": r.detail[:200],
                        "elapsed": r.elapsed_seconds,
                        "input_tokens": r.input_tokens,
                        "output_tokens": r.output_tokens,
                        "dollars": r.dollars,
                        "successful_calls": r.successful_calls,
                        "capability_failures": r.capability_failures,
                        "infra_failures": r.infra_failures,
                        "score_parse_failures": r.score_parse_failures,
                        "pick_parse_failures": r.pick_parse_failures,
                        "weighted_vote_ties": r.weighted_vote_ties,
                        "aborted": r.aborted,
                    }
                    for r in cr.task_results
                ],
            }
            for cr in all_results
        ],
    }
    log_path.write_text(json.dumps(log_data, indent=2))
    logger.info("Wrote results log to %s", log_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
