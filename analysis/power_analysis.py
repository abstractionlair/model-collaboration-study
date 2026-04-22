"""Pre-kickoff power analysis for the Phase 1 Protocol x Stratum interaction test.

The pre-registered primary test is the Protocol x Stratum interaction on the
task-level binary success rate. The utility curve assumed for the power calc is
fixed in `docs/research/experimental-design.md`:

  easy   (60-70% one-shot) : baseline 0.65, collab 0.60  ->  -5pp
  middle (45-55% one-shot) : baseline 0.50, collab 0.60  ->  +10pp
  hard   (30-40% one-shot) : baseline 0.35, collab 0.35  ->   0pp

If the interaction test has <80% power at alpha=0.05 under this curve at the
Phase 1 N per stratum per protocol, the pre-declared fallback is to collapse
to the middle band alone and run a two-proportion main-effect test there.

Usage:
    vault exec -- python3 analysis/power_analysis.py

    (no vault collections are needed; this is a pure-stats script.)

Outputs: a printed summary table plus a JSON file under analysis/ with the
full power grid.
"""
from __future__ import annotations

import json
import math
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import statsmodels.api as sm  # type: ignore[import-untyped]
from scipy import stats  # type: ignore[import-untyped]
from statsmodels.tools.sm_exceptions import (  # type: ignore[import-untyped]
    PerfectSeparationWarning,
)

# The full interaction model is saturated on the 6-cell design (6 params,
# 6 cells). statsmodels issues PerfectSeparationWarning and a divide-by-zero
# on the residual-scale calc because df_resid=0; both are benign for our
# purposes (we only use llf for the LRT, which is well-defined).
warnings.filterwarnings("ignore", category=PerfectSeparationWarning)
warnings.filterwarnings(
    "ignore", message="divide by zero encountered in scalar divide"
)


# --------------------------------------------------------------------------
# Pre-declared utility curve. Changing these values invalidates the operational
# gate; only touch if the design doc changes.
# --------------------------------------------------------------------------
STRATA = ("easy", "middle", "hard")
PROTOCOLS = ("baseline", "collab")

RATES: dict[tuple[str, str], float] = {
    ("baseline", "easy"): 0.65,
    ("collab", "easy"): 0.60,
    ("baseline", "middle"): 0.50,
    ("collab", "middle"): 0.60,
    ("baseline", "hard"): 0.35,
    ("collab", "hard"): 0.35,
}

ALPHA = 0.05
POWER_TARGET = 0.80


# --------------------------------------------------------------------------
# Simulation: one draw -> aggregated 6-cell binomial count table -> LRT for
# the 2-df interaction term.
# --------------------------------------------------------------------------
def _design_matrix(n_per_cell: int) -> pd.DataFrame:
    """Return a 6-row frame with P, S_easy, S_hard, P*S_easy, P*S_hard, n_trials."""
    rows = []
    for p_idx, protocol in enumerate(PROTOCOLS):
        for stratum in STRATA:
            s_easy = 1 if stratum == "easy" else 0
            s_hard = 1 if stratum == "hard" else 0
            rows.append({
                "protocol": protocol,
                "stratum": stratum,
                "P": p_idx,
                "S_easy": s_easy,
                "S_hard": s_hard,
                "P_easy": p_idx * s_easy,
                "P_hard": p_idx * s_hard,
                "n_trials": n_per_cell,
                "p_true": RATES[(protocol, stratum)],
            })
    return pd.DataFrame(rows)


def _simulate_counts(
    design: pd.DataFrame, rng: np.random.Generator
) -> "np.ndarray[tuple[int, ...], np.dtype[np.int64]]":
    """Draw a success count per cell under the true rates."""
    out = rng.binomial(
        design["n_trials"].to_numpy(), design["p_true"].to_numpy()
    )
    return out  # type: ignore[no-any-return]


def _interaction_lrt_pvalue(
    succ: np.ndarray, design: pd.DataFrame
) -> float | None:
    """Fit full + reduced GLM binomial, return p-value for the 2-df LRT.

    Returns None on convergence failure or separation; callers treat that as
    'skip this sim'.
    """
    endog = np.column_stack([succ, design["n_trials"].to_numpy() - succ]).astype(float)
    # Reduced: main effects only.
    exog_reduced = sm.add_constant(design[["P", "S_easy", "S_hard"]].to_numpy())
    # Full: main effects + 2 interaction terms.
    exog_full = sm.add_constant(
        design[["P", "S_easy", "S_hard", "P_easy", "P_hard"]].to_numpy()
    )
    try:
        m_red = sm.GLM(endog, exog_reduced, family=sm.families.Binomial()).fit()
        m_full = sm.GLM(endog, exog_full, family=sm.families.Binomial()).fit()
    except Exception:
        return None
    if not (np.isfinite(m_red.llf) and np.isfinite(m_full.llf)):
        return None
    lr = 2.0 * (m_full.llf - m_red.llf)
    if lr < 0:  # numerical slop around the MLE; treat as null-ish.
        lr = 0.0
    pval: float = float(stats.chi2.sf(lr, df=2))
    return pval


@dataclass
class PowerResult:
    n_per_cell: int
    n_sims: int
    n_skipped: int
    power_interaction: float
    power_middle_main: float  # main effect within the middle band, same N per arm
    power_easy_main: float
    power_hard_main: float


def _two_proportion_pvalue(
    succ_a: int, n_a: int, succ_b: int, n_b: int
) -> float:
    """Two-sided z-test on two proportions (pooled variance). Returns NaN if degenerate."""
    if n_a == 0 or n_b == 0:
        return math.nan
    p_a = succ_a / n_a
    p_b = succ_b / n_b
    pooled = (succ_a + succ_b) / (n_a + n_b)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    if se == 0:
        return 1.0 if p_a == p_b else 0.0
    z = (p_b - p_a) / se
    pval: float = 2.0 * float(1 - stats.norm.cdf(abs(z)))
    return pval


def power_at_n(
    n_per_cell: int, n_sims: int, seed: int, alpha: float = ALPHA
) -> PowerResult:
    """Simulate `n_sims` datasets at n_per_cell per (protocol, stratum) cell.

    Reports power for:
      - the primary Protocol x Stratum interaction LRT,
      - the within-middle-band two-proportion test (the pre-declared fallback),
      - within-easy and within-hard two-proportion tests (diagnostic).
    """
    rng = np.random.default_rng(seed)
    design = _design_matrix(n_per_cell)

    n_reject_interaction = 0
    n_skipped = 0
    per_stratum_reject = {"easy": 0, "middle": 0, "hard": 0}

    for _ in range(n_sims):
        succ = _simulate_counts(design, rng)

        p_inter = _interaction_lrt_pvalue(succ, design)
        if p_inter is None:
            n_skipped += 1
        elif p_inter < alpha:
            n_reject_interaction += 1

        # Per-stratum main-effect tests: pair baseline vs collab within each stratum.
        for stratum in STRATA:
            idx_base = design.index[
                (design["protocol"] == "baseline") & (design["stratum"] == stratum)
            ][0]
            idx_coll = design.index[
                (design["protocol"] == "collab") & (design["stratum"] == stratum)
            ][0]
            p = _two_proportion_pvalue(
                int(succ[idx_base]),
                n_per_cell,
                int(succ[idx_coll]),
                n_per_cell,
            )
            if not math.isnan(p) and p < alpha:
                per_stratum_reject[stratum] += 1

    effective = n_sims - n_skipped
    power_interaction = n_reject_interaction / effective if effective else math.nan
    return PowerResult(
        n_per_cell=n_per_cell,
        n_sims=n_sims,
        n_skipped=n_skipped,
        power_interaction=power_interaction,
        power_middle_main=per_stratum_reject["middle"] / n_sims,
        power_easy_main=per_stratum_reject["easy"] / n_sims,
        power_hard_main=per_stratum_reject["hard"] / n_sims,
    )


# --------------------------------------------------------------------------
# Analytical cross-check for the middle-band fallback.
# --------------------------------------------------------------------------
def analytical_two_proportion_power(
    p1: float, p2: float, n_per_arm: int, alpha: float = ALPHA
) -> float:
    """Normal-approximation power for a two-sided two-proportion z-test."""
    pbar = (p1 + p2) / 2
    se_null = math.sqrt(2 * pbar * (1 - pbar) / n_per_arm)
    se_alt = math.sqrt((p1 * (1 - p1) + p2 * (1 - p2)) / n_per_arm)
    z_crit = stats.norm.ppf(1 - alpha / 2)
    # Power = P(|Z| > z_crit | alt) with Z measured in null-SE units,
    # but the test statistic under the alternative has mean (p2-p1)/se_null
    # and SD se_alt / se_null. Solve directly:
    mean_alt = (p2 - p1) / se_null
    sd_alt = se_alt / se_null
    # P(Z > z_crit) + P(Z < -z_crit) where Z ~ N(mean_alt, sd_alt^2)
    upper = 1 - stats.norm.cdf((z_crit - mean_alt) / sd_alt)
    lower = stats.norm.cdf((-z_crit - mean_alt) / sd_alt)
    return float(upper + lower)


def analytical_n_for_two_proportion(
    p1: float, p2: float, power: float = POWER_TARGET, alpha: float = ALPHA
) -> int:
    """Smallest integer N per arm where analytical power reaches `power`."""
    # Closed-form formula (Fleiss et al., unequal-variance version is more honest
    # than the pooled shortcut for planning).
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    pbar = (p1 + p2) / 2
    num = z_a * math.sqrt(2 * pbar * (1 - pbar)) + z_b * math.sqrt(
        p1 * (1 - p1) + p2 * (1 - p2)
    )
    n = (num / (p2 - p1)) ** 2
    # Verify by walking up a couple of integers in case of rounding.
    n_int: int = math.ceil(n)
    while analytical_two_proportion_power(p1, p2, n_int, alpha) < power:
        n_int += 1
    return n_int


# --------------------------------------------------------------------------
# Driver.
# --------------------------------------------------------------------------
def run_grid(
    n_grid: Iterable[int], n_sims: int, seed: int
) -> list[PowerResult]:
    return [power_at_n(n, n_sims, seed + i) for i, n in enumerate(n_grid)]


def find_n_for_target(
    n_grid: Iterable[int], results: list[PowerResult], attr: str, target: float
) -> int | None:
    """First N in the grid where `attr` >= target, else None."""
    for n, r in zip(n_grid, results):
        if getattr(r, attr) >= target:
            return n
    return None


def main() -> None:
    # Grid of candidate N per (protocol x stratum) cell. Widely spaced so we can
    # see the power curve; narrow in later if Scott wants a precise threshold.
    n_grid = [25, 50, 75, 100, 150, 200, 300, 400, 600, 800, 1200, 1600]
    n_sims = 2000
    seed = 20260421

    print(f"Simulating {n_sims} trials per N across grid {n_grid}")
    print(f"alpha = {ALPHA}, target power = {POWER_TARGET}")
    print("Utility curve:")
    for (prot, strat), p in RATES.items():
        print(f"  {prot:>8s} x {strat:>6s} : {p:.2f}")
    print()

    t0 = time.time()
    results = run_grid(n_grid, n_sims, seed)
    elapsed = time.time() - t0
    print(f"Simulation done in {elapsed:.1f}s\n")

    # Print table.
    print(
        f"{'N/cell':>8s}  {'interaction':>12s}  {'middle 2p':>11s}  "
        f"{'easy 2p':>9s}  {'hard 2p':>9s}  {'skipped':>8s}"
    )
    print("-" * 72)
    for r in results:
        print(
            f"{r.n_per_cell:>8d}  {r.power_interaction:>12.3f}  "
            f"{r.power_middle_main:>11.3f}  {r.power_easy_main:>9.3f}  "
            f"{r.power_hard_main:>9.3f}  {r.n_skipped:>8d}"
        )
    print()

    # Headline results.
    n_for_inter = find_n_for_target(n_grid, results, "power_interaction", POWER_TARGET)
    n_for_middle_sim = find_n_for_target(n_grid, results, "power_middle_main", POWER_TARGET)
    n_for_middle_analytical = analytical_n_for_two_proportion(
        RATES[("baseline", "middle")], RATES[("collab", "middle")]
    )
    middle_analytical_power_curve = {
        n: analytical_two_proportion_power(
            RATES[("baseline", "middle")], RATES[("collab", "middle")], n
        )
        for n in n_grid
    }

    print("Headline:")
    print(
        f"  N/cell for >= {POWER_TARGET:.0%} power on interaction (simulated): "
        f"{n_for_inter if n_for_inter is not None else 'not reached in grid'}"
    )
    print(
        f"  N/arm for >= {POWER_TARGET:.0%} power on middle-band main effect "
        f"(simulated): "
        f"{n_for_middle_sim if n_for_middle_sim is not None else 'not reached in grid'}"
    )
    print(
        f"  N/arm for >= {POWER_TARGET:.0%} power on middle-band main effect "
        f"(analytical): {n_for_middle_analytical}"
    )

    # Persist.
    out_dir = Path(__file__).parent
    out = {
        "alpha": ALPHA,
        "power_target": POWER_TARGET,
        "utility_curve": {f"{k[0]}|{k[1]}": v for k, v in RATES.items()},
        "n_sims_per_point": n_sims,
        "seed": seed,
        "grid": [
            {
                "n_per_cell": r.n_per_cell,
                "power_interaction": r.power_interaction,
                "power_middle_main_sim": r.power_middle_main,
                "power_easy_main_sim": r.power_easy_main,
                "power_hard_main_sim": r.power_hard_main,
                "power_middle_main_analytical": middle_analytical_power_curve[
                    r.n_per_cell
                ],
                "n_skipped": r.n_skipped,
            }
            for r in results
        ],
        "n_for_interaction_80pct": n_for_inter,
        "n_for_middle_main_80pct_sim": n_for_middle_sim,
        "n_for_middle_main_80pct_analytical": n_for_middle_analytical,
    }
    out_path = out_dir / "power_results.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {out_path.relative_to(Path.cwd().parent) if out_path.is_absolute() else out_path}")


if __name__ == "__main__":
    main()
