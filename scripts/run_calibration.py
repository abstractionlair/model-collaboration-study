#!/usr/bin/env python3
"""Per-bucket calibration driver.

Runs Condition A (one pass) for each subject model against
each slice of each Phase 1 benchmark, and reports one combined
per-(bench, slice, model) pass-rate table. Answers the
calibration question: "where does one-shot pass rate actually
land on the three subjects for each bucket?"

Slices:
- LCB test6, stdin-only: difficulty in {easy, medium, hard}
  (26 / 26 / 60 tasks at the current release).
- BFCL: category in {simple_python, multiple, parallel,
  parallel_multiple, live_simple}.

Sampling: first-N tasks in file order for BFCL (deterministic
across runs); all stdin-only for LCB.

Usage:
    vault exec anthropic,openai,google -- \\
        python3 scripts/run_calibration.py           # full
    python3 scripts/run_calibration.py --smoke       # 3/1
    python3 scripts/run_calibration.py --bench lcb
    python3 scripts/run_calibration.py --bench bfcl
    python3 scripts/run_calibration.py --bfcl-n 30
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
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.executor import ApiClient
from src.experiment.benchmarks import BFCLBench, LiveCodeBenchBench
from src.experiment.benchmarks.base import Benchmark
from src.experiment.phase1 import (
    PHASE1_PRICING_DRAFT,
    SUBJECT_MODELS,
)
from src.experiment.runner import ConditionResults, run_condition
from src.experiment.spec import BudgetTier, ConditionSpec
from src.protocols.conditions import condition_a


REPO_ROOT = Path(__file__).resolve().parent.parent
BFCL_DATA = REPO_ROOT / "data" / "bfcl"
LCB_DATA = REPO_ROOT / "data" / "livecodebench"
OUTPUT_DIR = REPO_ROOT / "data" / "mini_bench_runs"

BFCL_CATEGORIES = (
    "simple_python", "multiple", "parallel",
    "parallel_multiple", "live_simple",
)
LCB_DIFFICULTIES = ("easy", "medium", "hard")


def available_providers() -> set[str]:
    avail = set()
    if os.environ.get("ANTHROPIC_API_KEY"):
        avail.add("anthropic")
    if os.environ.get("OPENAI_API_KEY"):
        avail.add("openai")
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


def build_bfcl_slice(
    category: str, n: int,
) -> tuple[Benchmark, list[str]]:
    qpath = BFCL_DATA / f"BFCL_v4_{category}.json"
    apath = BFCL_DATA / "possible_answer" / f"BFCL_v4_{category}.json"
    if not qpath.exists() or not apath.exists():
        raise FileNotFoundError(
            f"BFCL data for {category!r} not found at {qpath}. "
            f"Run `scripts/download_bfcl.py` first."
        )
    all_bench = BFCLBench(category=category, questions_path=qpath, answers_path=apath)
    task_ids = [t.id for t in list(all_bench.tasks())[:n]]
    bench = BFCLBench(
        category=category, questions_path=qpath, answers_path=apath,
        task_ids=task_ids,
    )
    return bench, task_ids


def build_lcb_slice(
    difficulty: str, release: str, n: int | None,
) -> tuple[Benchmark, list[str]]:
    path = LCB_DATA / f"{release}.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"LCB data not found at {path}. "
            f"Run `scripts/download_livecodebench.py` first."
        )
    full = LiveCodeBenchBench(jsonl_path=path, difficulties=[difficulty])
    task_ids = [t.id for t in full.tasks()]
    if n is not None:
        task_ids = task_ids[:n]
    bench = LiveCodeBenchBench(
        jsonl_path=path, difficulties=[difficulty], task_ids=task_ids,
    )
    return bench, task_ids


def run_one_cell(
    bench_name: str,
    slice_name: str,
    model: str,
    benchmark: Benchmark,
    seed: int,
) -> ConditionResults:
    cond = ConditionSpec(
        name=f"A ({model})",
        label=f"Calibration: {bench_name}/{slice_name}/{model}",
        protocol=condition_a(model),
        budget_tier=BudgetTier.X,
        models=[model],
    )
    client = ApiClient()
    return run_condition(cond, benchmark, client, PHASE1_PRICING_DRAFT, seed=seed)


def summarise(rows: list[dict[str, Any]]) -> str:
    # Group rows by (bench, slice); columns are models.
    lines: list[str] = []
    by_key: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    models: list[str] = []
    for r in rows:
        key = (r["bench"], r["slice"])
        by_key.setdefault(key, {})[r["model"]] = r
        if r["model"] not in models:
            models.append(r["model"])

    header = f"{'Bench':<6}  {'Slice':<18}  {'N':>4}"
    for m in models:
        header += f"  {m[:20]:>20}"
    lines.append(header)
    lines.append("-" * len(header))

    for key in sorted(by_key):
        bench, slice_ = key
        any_row = next(iter(by_key[key].values()))
        n = any_row["n_tasks"]
        row = f"{bench:<6}  {slice_:<18}  {n:>4}"
        for m in models:
            cell = by_key[key].get(m)
            if cell is None:
                row += f"  {'—':>20}"
            else:
                strict = cell["strict_pass_rate"]
                meanfrac = cell["mean_fraction"]
                if abs(strict - meanfrac) < 1e-6:
                    text = f"{strict:.2f}"
                else:
                    text = f"{strict:.2f} ({meanfrac:.2f})"
                row += f"  {text:>20}"
        lines.append(row)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bench", choices=["all", "lcb", "bfcl"], default="all",
    )
    parser.add_argument(
        "--smoke", action="store_true",
        help="Tiny run: 3 tasks × 1 model per bench.",
    )
    parser.add_argument(
        "--bfcl-n", type=int, default=50,
        help="Tasks per BFCL category (default: 50).",
    )
    parser.add_argument(
        "--lcb-n", type=int, default=None,
        help="Tasks per LCB difficulty; default: all stdin-only.",
    )
    parser.add_argument("--lcb-release", default="test6")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--checkpoint", type=str, default=None,
        help="Path to a per-cell checkpoint file. If it exists at "
             "start, previously-completed cells are skipped. Every "
             "cell result is appended so a mid-run kill is resumable.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("run_calibration")

    providers = available_providers()
    if not providers:
        logger.error(
            "No API keys found. Run via `vault exec anthropic,openai,google -- ...`",
        )
        return 1
    subject_models = [m for m in SUBJECT_MODELS if model_provider(m) in providers]
    if not subject_models:
        logger.error("No subject models available given current API keys.")
        return 1

    if args.smoke:
        subject_models = subject_models[:1]
        args.bfcl_n = 3
        args.lcb_n = 3
        logger.info("SMOKE MODE: %s, bfcl_n=3, lcb_n=3", subject_models)
    else:
        logger.info("Subject models: %s", subject_models)

    # Assemble the plan.
    slices: list[tuple[str, str, Benchmark, list[str]]] = []
    if args.bench in ("all", "lcb"):
        for d in LCB_DIFFICULTIES:
            bench, tids = build_lcb_slice(d, args.lcb_release, args.lcb_n)
            if tids:
                slices.append(("lcb", d, bench, tids))
    if args.bench in ("all", "bfcl"):
        for cat in BFCL_CATEGORIES:
            bench, tids = build_bfcl_slice(cat, args.bfcl_n)
            if tids:
                slices.append(("bfcl", cat, bench, tids))

    total_cells = len(slices) * len(subject_models)
    total_calls_est = sum(len(tids) for _, _, _, tids in slices) * len(subject_models)
    logger.info(
        "Plan: %d cells, ~%d Condition-A calls total",
        total_cells, total_calls_est,
    )

    rows: list[dict[str, Any]] = []
    checkpoint_path = Path(args.checkpoint) if args.checkpoint else None
    done_keys: set[tuple[str, str, str]] = set()
    if checkpoint_path is not None and checkpoint_path.exists():
        existing = json.loads(checkpoint_path.read_text())
        rows = list(existing.get("rows", []))
        done_keys = {(r["bench"], r["slice"], r["model"]) for r in rows}
        logger.info(
            "Resuming from %s: %d cells already complete.",
            checkpoint_path, len(done_keys),
        )

    t0 = time.monotonic()
    cell_i = 0
    for bench_name, slice_name, bench, task_ids in slices:
        for model in subject_models:
            cell_i += 1
            if (bench_name, slice_name, model) in done_keys:
                logger.info(
                    "[cell %d/%d] %s / %s / %s — SKIP (in checkpoint)",
                    cell_i, total_cells, bench_name, slice_name, model,
                )
                continue
            logger.info(
                "[cell %d/%d] %s / %s / %s (N=%d)",
                cell_i, total_cells, bench_name, slice_name, model, len(task_ids),
            )
            cr = run_one_cell(
                bench_name, slice_name, model, bench, args.seed,
            )

            n = len(cr.task_results)
            strict_passed = sum(1 for r in cr.task_results if r.passed)
            mean_frac = sum(r.fraction for r in cr.task_results) / n if n else 0.0
            rows.append({
                "bench": bench_name,
                "slice": slice_name,
                "model": model,
                "n_tasks": n,
                "strict_passed": strict_passed,
                "strict_pass_rate": strict_passed / n if n else 0.0,
                "mean_fraction": mean_frac,
                "abort_count": cr.abort_count,
                "total_dollars": cr.total_dollars,
                "task_ids": task_ids,
                "tasks": [
                    {
                        "task_id": r.task_id,
                        "passed": r.passed,
                        "fraction": r.fraction,
                        "detail": r.detail[:200],
                        "elapsed": r.elapsed_seconds,
                        "dollars": r.dollars,
                        "aborted": r.aborted,
                    }
                    for r in cr.task_results
                ],
            })
            logger.info(
                "  → strict %d/%d (%.2f), mean_frac %.2f, $%.3f, aborts=%d",
                strict_passed, n,
                strict_passed / n if n else 0.0,
                mean_frac,
                cr.total_dollars,
                cr.abort_count,
            )
            if checkpoint_path is not None:
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                tmp = checkpoint_path.with_suffix(
                    checkpoint_path.suffix + ".tmp"
                )
                tmp.write_text(json.dumps({
                    "kind": "calibration-checkpoint",
                    "subject_models": subject_models,
                    "seed": args.seed,
                    "bfcl_n": args.bfcl_n,
                    "lcb_n": args.lcb_n,
                    "lcb_release": args.lcb_release,
                    "rows": rows,
                }, indent=2))
                tmp.replace(checkpoint_path)

    elapsed = time.monotonic() - t0
    total_dollars = sum(r["total_dollars"] for r in rows)

    print()
    print("=" * 78)
    print(f"Calibration results (elapsed: {elapsed:.1f}s, total ${total_dollars:.3f})")
    print("=" * 78)
    print(summarise(rows))
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    suffix = "-smoke" if args.smoke else ""
    log_path = OUTPUT_DIR / f"calibration-{args.bench}{suffix}-{ts}.json"
    log_data = {
        "kind": "calibration",
        "timestamp": ts,
        "bench_filter": args.bench,
        "subject_models": subject_models,
        "seed": args.seed,
        "bfcl_n": args.bfcl_n,
        "lcb_n": args.lcb_n,
        "lcb_release": args.lcb_release,
        "smoke": args.smoke,
        "elapsed_seconds": elapsed,
        "total_dollars": total_dollars,
        "rows": rows,
    }
    log_path.write_text(json.dumps(log_data, indent=2))
    logger.info("Wrote calibration log to %s", log_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
