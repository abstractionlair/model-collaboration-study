#!/usr/bin/env python3
"""Phase 1 pilot driver: full condition set on the LCB middle band.

Runs the complete Phase 1 condition family — A (x each subject),
B (best model, N samples + pick), C, D, D', E — against the
LiveCodeBench medium+hard pool identified by calibration as the
middle band. This is the first run where all conditions face the
same calibrated task pool.

**Pilot, not the pre-registered test.** N here (~86 at test6) is
far below the ~400/arm the power analysis requires. Results are
descriptive: does the machine run end-to-end, and what do the
first compute-matched comparisons look like?

Compute-matching for B: `--b-samples` sets N. The intended
calibration is dollars-matched to Condition D's realized per-task
cost (n ~= D_dollars / A_best_dollars); run `--smoke` first, read
the per-condition costs, then launch the full run with the
matched value.

Checkpointing: `--checkpoint` writes a per-(condition x task)
sidecar after every task, so a mid-run kill loses at most one
task. Re-running with the same checkpoint path skips completed
(condition, task) pairs.

Usage:
    # Smoke first (2 medium + 1 hard task, all conditions):
    vault exec anthropic,openai,google -- \\
        python3 scripts/run_pilot.py --smoke

    # Full pilot (resumable):
    vault exec anthropic,openai,google -- \\
        python3 scripts/run_pilot.py --b-samples 8 \\
            --checkpoint data/pilot_checkpoint.json
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.executor import ApiClient
from src.experiment.benchmarks import LiveCodeBenchBench
from src.experiment.benchmarks.base import Benchmark, ScoreResult, Task
from src.experiment.phase1 import (
    PHASE1_PRICING_DRAFT,
    SUBJECT_MODELS,
)
from src.experiment.runner import TaskResult, run_condition
from src.experiment.spec import BudgetTier, ConditionSpec
from src.protocols.conditions import (
    condition_a,
    condition_b,
    condition_c,
    condition_d,
    condition_d_prime,
    condition_e,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
LCB_DATA = REPO_ROOT / "data" / "livecodebench"
OUTPUT_DIR = REPO_ROOT / "data" / "mini_bench_runs"

# Per-bucket best subject on LCB, from calibration
# (docs/research/calibration-findings.md): gpt-5.4-mini dominates
# both medium and hard on strict and mean_frac.
DEFAULT_BEST_MODEL = "gpt-5.4-mini"


def available_providers() -> set[str]:
    avail = set()
    if os.environ.get("ANTHROPIC_API_KEY"):
        avail.add("anthropic")
    if os.environ.get("OPENAI_API_KEY"):
        avail.add("openai")
    # Google's key is also accepted under the *_EMBEDDING_* names
    # (see CLAUDE.md API credentials, ApiClient._get_google).
    if (
        os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_EMBEDDING_API_KEY")
        or os.environ.get("GEMINI_EMBEDDING_API_KEY")
    ):
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


class _SingleTaskView:
    """Benchmark protocol adapter exposing one task of a full bench.

    Lets the driver call `run_condition` once per task (for
    per-task checkpointing) without re-loading the underlying
    data per call. Scoring delegates to the full benchmark.
    """

    def __init__(self, full: Benchmark, task: Task) -> None:
        self._full = full
        self._task = task
        # Plain attribute: the Benchmark protocol declares `name`
        # as a settable variable, so a read-only property fails
        # structural typing under mypy --strict.
        self.name = full.name

    def tasks(self) -> Iterator[Task]:
        yield self._task

    def score(self, task_id: str, response_text: str) -> ScoreResult:
        return self._full.score(task_id, response_text)


def build_conditions(
    subject_models: list[str],
    best_model: str,
    b_samples: int,
) -> list[ConditionSpec]:
    conditions: list[ConditionSpec] = []
    for model in subject_models:
        conditions.append(ConditionSpec(
            name=f"A ({model})",
            label=f"Single-model one pass, {model}",
            protocol=condition_a(model),
            budget_tier=BudgetTier.X,
            models=[model],
        ))
    conditions.append(ConditionSpec(
        name=f"B ({best_model}, n={b_samples})",
        label=f"Repeat-and-aggregate, {best_model}, {b_samples} samples",
        protocol=condition_b(best_model, b_samples),
        budget_tier=BudgetTier.TWO_X,
        models=[best_model],
    ))
    conditions.append(ConditionSpec(
        name=f"C (judge={best_model})",
        label="Heterogeneous parallel + peer-LLM aggregation",
        protocol=condition_c(subject_models, best_model),
        budget_tier=BudgetTier.TWO_X,
        models=subject_models,
    ))
    conditions.append(ConditionSpec(
        name="D (hetero)",
        label="Heterogeneous ReConcile-style, 1 round",
        protocol=condition_d(subject_models, n_rounds=1),
        budget_tier=BudgetTier.TWO_X,
        models=subject_models,
    ))
    conditions.append(ConditionSpec(
        name=f"D' ({best_model} x{len(subject_models)})",
        label="Homogeneous ReConcile-style, 1 round",
        protocol=condition_d_prime(
            best_model, len(subject_models), n_rounds=1,
        ),
        budget_tier=BudgetTier.TWO_X,
        models=[best_model],
    ))
    conditions.append(ConditionSpec(
        name=f"E (meta={best_model})",
        label="Hierarchical synthesis",
        protocol=condition_e(subject_models, best_model),
        budget_tier=BudgetTier.TWO_X,
        models=subject_models,
    ))
    return conditions


def task_row(
    r: TaskResult, provider_dollars: dict[str, float],
) -> dict[str, Any]:
    return {
        "condition": r.condition_name,
        "task_id": r.task_id,
        "passed": r.passed,
        "fraction": r.fraction,
        "detail": r.detail[:200],
        "elapsed": r.elapsed_seconds,
        "input_tokens": r.input_tokens,
        "output_tokens": r.output_tokens,
        "dollars": r.dollars,
        "provider_dollars": provider_dollars,
        "successful_calls": r.successful_calls,
        "capability_failures": r.capability_failures,
        "infra_failures": r.infra_failures,
        "score_parse_failures": r.score_parse_failures,
        "pick_parse_failures": r.pick_parse_failures,
        "weighted_vote_ties": r.weighted_vote_ties,
        "aborted": r.aborted,
    }


def summarise(rows: list[dict[str, Any]], n_pool: int) -> str:
    by_cond: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_cond.setdefault(r["condition"], []).append(r)

    header = (
        f"{'Condition':<32}  {'Full pass':>10}  {'Mean frac':>9}  "
        f"{'Abort':>5}  {'Dollars':>8}  {'$/task':>7}"
    )
    lines = [header, "-" * len(header)]
    for cond, cond_rows in by_cond.items():
        n = len(cond_rows)
        full_pass = sum(1 for r in cond_rows if r["passed"])
        mean_frac = sum(r["fraction"] for r in cond_rows) / n if n else 0.0
        aborts = sum(1 for r in cond_rows if r["aborted"])
        dollars = sum(r["dollars"] for r in cond_rows)
        lines.append(
            f"{cond:<32}  {full_pass:>4}/{n:<5}  {mean_frac:>9.3f}  "
            f"{aborts:>5}  ${dollars:>7.3f}  ${dollars / n if n else 0.0:>6.4f}"
        )

    provider_totals: dict[str, float] = {}
    for r in rows:
        for prov, d in r.get("provider_dollars", {}).items():
            provider_totals[prov] = provider_totals.get(prov, 0.0) + d
    lines.append("")
    lines.append("Per-provider dollars: " + ", ".join(
        f"{p}=${d:.3f}" for p, d in sorted(provider_totals.items())
    ))
    done_pairs = len(rows)
    lines.append(f"Completed (condition, task) pairs: {done_pairs}")
    lines.append(f"Task pool size: {n_pool}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=str, default="test6")
    parser.add_argument(
        "--difficulties", type=str, default="medium,hard",
        help="Comma-separated LCB difficulty labels (default: medium,hard).",
    )
    parser.add_argument(
        "--tasks", type=str, default=None,
        help="Comma-separated task IDs (overrides the difficulty pool).",
    )
    parser.add_argument(
        "--smoke", action="store_true",
        help="First 2 medium + 1 hard tasks only, all conditions.",
    )
    parser.add_argument(
        "--b-samples", type=int, default=8,
        help="N for Condition B. Dollar-match to D's realized per-task "
             "cost from the smoke run before the full pilot (default: 8, "
             "provisional).",
    )
    parser.add_argument(
        "--best-model", type=str, default=DEFAULT_BEST_MODEL,
        help="Best subject on this bucket per calibration "
             f"(default: {DEFAULT_BEST_MODEL}).",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--timeout", type=float, default=10.0,
        help="Per-test execution timeout in seconds (default: 10).",
    )
    parser.add_argument(
        "--checkpoint", type=str, default=None,
        help="Per-(condition, task) resumable checkpoint path.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("run_pilot")

    jsonl_path = LCB_DATA / f"{args.release}.jsonl"
    if not jsonl_path.exists():
        logger.error(
            "LCB data not found at %s. Run "
            "`python3 scripts/download_livecodebench.py --release %s` first.",
            jsonl_path, args.release,
        )
        return 1

    providers = available_providers()
    subject_models = [
        m for m in SUBJECT_MODELS if model_provider(m) in providers
    ]
    if len(subject_models) < len(SUBJECT_MODELS):
        logger.error(
            "Pilot needs all subject models; missing keys for %s. "
            "Run via `vault exec anthropic,openai,google -- ...`.",
            sorted(set(SUBJECT_MODELS) - set(subject_models)),
        )
        return 1
    if args.best_model not in subject_models:
        logger.error(
            "--best-model %r not in subject pool %s",
            args.best_model, subject_models,
        )
        return 1

    difficulties = [
        d.strip() for d in args.difficulties.split(",") if d.strip()
    ]
    full_bench = LiveCodeBenchBench(
        jsonl_path,
        difficulties=difficulties,
        execution_timeout=args.timeout,
    )
    pool = list(full_bench.tasks())

    if args.tasks:
        wanted = [t.strip() for t in args.tasks.split(",") if t.strip()]
        by_id = {t.id: t for t in pool}
        missing = [tid for tid in wanted if tid not in by_id]
        if missing:
            logger.error("Task IDs not in pool: %s", missing)
            return 1
        tasks = [by_id[tid] for tid in wanted]
    elif args.smoke:
        # Task carries no difficulty field; enumerate per-difficulty
        # ID pools the same way run_calibration.py does.
        med_ids = {
            t.id for t in LiveCodeBenchBench(
                jsonl_path, difficulties=["medium"],
            ).tasks()
        }
        med = [t for t in pool if t.id in med_ids][:2]
        hard = [t for t in pool if t.id not in med_ids][:1]
        tasks = med + hard
    else:
        tasks = pool

    conditions = build_conditions(
        subject_models, args.best_model, args.b_samples,
    )
    calls_per_task = (
        len(subject_models)            # A x subjects
        + args.b_samples + 1           # B
        + len(subject_models) + 1      # C
        + 4 * len(subject_models)      # D (ReConcile, 1 round)
        + 4 * len(subject_models)      # D'
        + 2 * len(subject_models) + 1  # E
    )
    logger.info(
        "Plan: %d tasks x %d conditions (~%d calls/task, ~%d calls total)",
        len(tasks), len(conditions), calls_per_task,
        calls_per_task * len(tasks),
    )

    rows: list[dict[str, Any]] = []
    checkpoint_path = Path(args.checkpoint) if args.checkpoint else None
    done: set[tuple[str, str]] = set()
    if checkpoint_path is not None and checkpoint_path.exists():
        existing = json.loads(checkpoint_path.read_text())
        rows = list(existing.get("rows", []))
        done = {(r["condition"], r["task_id"]) for r in rows}
        logger.info(
            "Resuming from %s: %d (condition, task) pairs complete.",
            checkpoint_path, len(done),
        )

    def write_checkpoint() -> None:
        if checkpoint_path is None:
            return
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = checkpoint_path.with_suffix(checkpoint_path.suffix + ".tmp")
        tmp.write_text(json.dumps({
            "kind": "pilot-checkpoint",
            "release": args.release,
            "difficulties": difficulties,
            "subject_models": subject_models,
            "best_model": args.best_model,
            "b_samples": args.b_samples,
            "seed": args.seed,
            "task_ids": [t.id for t in tasks],
            "rows": rows,
        }, indent=2))
        tmp.replace(checkpoint_path)

    t0 = time.monotonic()
    for cond in conditions:
        remaining = [t for t in tasks if (cond.name, t.id) not in done]
        if not remaining:
            logger.info("Condition %s — all tasks in checkpoint, skip.",
                        cond.name)
            continue
        logger.info(
            "Condition %s — %d/%d tasks remaining.",
            cond.name, len(remaining), len(tasks),
        )
        client = ApiClient()
        for task in remaining:
            call_start = len(client.calls)
            cr = run_condition(
                cond,
                _SingleTaskView(full_bench, task),
                client,
                PHASE1_PRICING_DRAFT,
                seed=args.seed,
            )
            task_calls = client.calls[call_start:]
            provider_dollars: dict[str, float] = {}
            for c in task_calls:
                prov = model_provider(c.model)
                provider_dollars[prov] = (
                    provider_dollars.get(prov, 0.0)
                    + PHASE1_PRICING_DRAFT.cost(
                        c.model, c.input_tokens, c.output_tokens,
                    )
                )
            for r in cr.task_results:
                rows.append(task_row(r, provider_dollars))
            write_checkpoint()

    elapsed = time.monotonic() - t0

    print()
    print("=" * 84)
    print(f"Pilot results (this run elapsed: {elapsed:.1f}s)")
    print("=" * 84)
    print(summarise(rows, n_pool=len(tasks)))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    suffix = "-smoke" if args.smoke else ""
    log_path = OUTPUT_DIR / f"pilot-lcb{suffix}-{ts}.json"
    log_path.write_text(json.dumps({
        "kind": "pilot",
        "timestamp": ts,
        "release": args.release,
        "difficulties": difficulties,
        "smoke": args.smoke,
        "subject_models": subject_models,
        "best_model": args.best_model,
        "b_samples": args.b_samples,
        "seed": args.seed,
        "execution_timeout_seconds": args.timeout,
        "elapsed_seconds": elapsed,
        "task_ids": [t.id for t in tasks],
        "rows": rows,
    }, indent=2))
    logger.info("Wrote pilot log to %s", log_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
