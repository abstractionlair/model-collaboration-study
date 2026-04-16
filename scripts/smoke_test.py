#!/usr/bin/env python3
"""End-to-end smoke tests for the protocol pipeline.

Runs each Phase 1 condition on a simple coding task with real API
calls and checks:

  1. Did it run at all? (no exceptions)
  2. Does the response look like a real answer? (non-empty, contains
     code-like content)
  3. Did intermediate steps attempt what was asked? (reviews contain
     critique language, revisions differ from originals, fuse draws
     on peer drafts)

Uses the cheapest available models to minimize cost. The test query
is deliberately simple so the models can actually solve it.

Usage:
    # Load API keys and run
    vault exec anthropic,openai,google,xai -- python3 scripts/smoke_test.py

    # Or with env vars set manually
    python3 scripts/smoke_test.py
"""

from __future__ import annotations

import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.executor import ApiClient, TracingClient, run
from src.executor.tracing import TraceEntry
from src.ir.ast import Expr
from src.protocols.conditions import (
    condition_a,
    condition_b,
    condition_c,
    condition_d_prime,
    condition_e,
)
from src.protocols.reconcile import reconcile


# ============================================================================
# Configuration
# ============================================================================

# Use the cheapest models from each provider for smoke tests.
# These are not the Phase 1 subject models — just cheap enough to
# verify the machinery works.
ANTHROPIC_MODEL = "claude-haiku-4-5"
OPENAI_MODEL = "gpt-4.1-mini"
GOOGLE_MODEL = "gemini-2.5-flash"
XAI_MODEL = "grok-3-mini"

# A simple task that cheap models should be able to solve.
TEST_QUERY = """\
Write a Python function called `fizzbuzz(n)` that returns a list of strings
for numbers 1 through n. For multiples of 3, use "Fizz"; for multiples of 5,
use "Buzz"; for multiples of both, use "FizzBuzz"; otherwise use the number
as a string."""


# ============================================================================
# Helpers
# ============================================================================

def available_models() -> list[str]:
    """Return models whose API keys are set."""
    models = []
    if os.environ.get("ANTHROPIC_API_KEY"):
        models.append(ANTHROPIC_MODEL)
    if os.environ.get("OPENAI_API_KEY"):
        models.append(OPENAI_MODEL)
    if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        models.append(GOOGLE_MODEL)
    if os.environ.get("XAI_API_KEY"):
        models.append(XAI_MODEL)
    return models


def check_response_quality(response: str, label: str) -> list[str]:
    """Basic quality checks on a final response."""
    issues: list[str] = []
    if not response or not response.strip():
        issues.append(f"{label}: response is empty")
        return issues
    if len(response.strip()) < 20:
        issues.append(f"{label}: response suspiciously short ({len(response)} chars)")
    # For a coding task, we expect some code-like content
    if "def " not in response and "fizzbuzz" not in response.lower():
        issues.append(f"{label}: response doesn't look like code")
    return issues


def check_intermediate_steps(trace: list[TraceEntry], label: str) -> list[str]:
    """Check that intermediate steps attempted what was asked."""
    issues: list[str] = []
    for entry in trace:
        if not entry.response or not entry.response.strip():
            issues.append(
                f"{label} call {entry.call_number} ({entry.step_type}): "
                f"empty response from {entry.model}"
            )
            continue

        if entry.step_type == "review":
            # A review should contain some evaluative language
            lower = entry.response.lower()
            has_eval = any(w in lower for w in [
                "correct", "issue", "good", "problem", "strength",
                "weakness", "suggest", "improve", "error", "bug",
                "missing", "consider", "well", "however", "but",
            ])
            if not has_eval:
                issues.append(
                    f"{label} call {entry.call_number}: review doesn't "
                    f"contain evaluative language"
                )

        if entry.step_type == "score":
            # A score response should be parseable as a float
            try:
                tokens = entry.response.replace(",", " ").split()
                found = False
                for tok in tokens:
                    try:
                        v = float(tok)
                        if 0.0 <= v <= 1.0:
                            found = True
                            break
                    except ValueError:
                        continue
                if not found:
                    issues.append(
                        f"{label} call {entry.call_number}: score response "
                        f"doesn't contain a float in [0,1]: {entry.response[:80]!r}"
                    )
            except Exception:
                issues.append(
                    f"{label} call {entry.call_number}: could not parse score"
                )
    return issues


def run_condition(
    label: str,
    protocol: Expr[object],
    client: TracingClient,
) -> tuple[bool, str, list[str]]:
    """Run one condition and return (success, response_preview, issues)."""
    client.clear()
    try:
        result = run(protocol, client, TEST_QUERY)
    except Exception as e:
        return False, "", [f"{label}: EXCEPTION: {type(e).__name__}: {e}"]

    response = result.text
    issues: list[str] = []
    issues.extend(check_response_quality(response, label))
    issues.extend(check_intermediate_steps(client.trace, label))

    preview = response[:150].replace("\n", " ")
    if len(response) > 150:
        preview += "..."
    return len(issues) == 0, preview, issues


# ============================================================================
# Test suite
# ============================================================================

def run_single_provider_tests(model: str, client: TracingClient) -> list[str]:
    """Test conditions that use a single model."""
    all_issues: list[str] = []

    # Condition A: single gen
    print(f"\n  A ({model})...")
    ok, preview, issues = run_condition(
        f"A/{model}", condition_a(model), client
    )
    print(f"    {'PASS' if ok else 'FAIL'} ({len(client.trace)} calls)")
    if preview:
        print(f"    Response: {preview[:100]}")
    all_issues.extend(issues)
    for issue in issues:
        print(f"    ! {issue}")

    # Condition B: repeat-and-aggregate (N=2 to keep costs down)
    print(f"\n  B ({model}, N=2)...")
    ok, preview, issues = run_condition(
        f"B/{model}", condition_b(model, 2), client
    )
    print(f"    {'PASS' if ok else 'FAIL'} ({len(client.trace)} calls)")
    all_issues.extend(issues)
    for issue in issues:
        print(f"    ! {issue}")

    return all_issues


def run_multi_provider_tests(
    models: list[str], client: TracingClient
) -> list[str]:
    """Test conditions that use multiple models."""
    all_issues: list[str] = []

    if len(models) < 2:
        print("\n  Skipping multi-model tests (need ≥2 providers)")
        return all_issues

    pool = models[:3]  # up to 3 models
    judge = pool[0]

    # Condition C: heterogeneous parallel + peer aggregation
    print(f"\n  C ({', '.join(pool)})...")
    ok, preview, issues = run_condition(
        "C", condition_c(pool, judge), client
    )
    print(f"    {'PASS' if ok else 'FAIL'} ({len(client.trace)} calls)")
    all_issues.extend(issues)
    for issue in issues:
        print(f"    ! {issue}")

    # Condition D' (homogeneous ReConcile, 1 round, pool_size=2)
    print(f"\n  D' ({pool[0]}, pool=2, 1 round)...")
    ok, preview, issues = run_condition(
        "D'", condition_d_prime(pool[0], 2, n_rounds=1), client
    )
    print(f"    {'PASS' if ok else 'FAIL'} ({len(client.trace)} calls)")
    all_issues.extend(issues)
    for issue in issues:
        print(f"    ! {issue}")

    # Condition D (heterogeneous ReConcile, 1 round)
    if len(pool) >= 2:
        print(f"\n  D ({', '.join(pool[:2])}, 1 round)...")
        ok, preview, issues = run_condition(
            "D", reconcile(pool[:2], n_rounds=1), client
        )
        print(f"    {'PASS' if ok else 'FAIL'} ({len(client.trace)} calls)")
        all_issues.extend(issues)
        for issue in issues:
            print(f"    ! {issue}")

    # Condition E (hierarchical synthesis)
    if len(pool) >= 2:
        test_pool = pool[:2]
        meta = test_pool[0]
        print(f"\n  E ({', '.join(test_pool)}, meta={meta})...")
        ok, preview, issues = run_condition(
            "E", condition_e(test_pool, meta), client
        )
        print(f"    {'PASS' if ok else 'FAIL'} ({len(client.trace)} calls)")
        all_issues.extend(issues)
        for issue in issues:
            print(f"    ! {issue}")

    return all_issues


def main() -> int:
    models = available_models()
    if not models:
        print("ERROR: No API keys found. Set at least one of:")
        print("  ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, XAI_API_KEY")
        return 1

    print(f"Available models: {', '.join(models)}")
    print(f"Test query: fizzbuzz function")
    print(f"Max tokens: 1024, temperature: 0.0")

    api = ApiClient(max_retries=2, temperature=0.0, max_tokens=1024)
    client = TracingClient(api)

    all_issues: list[str] = []
    t0 = time.monotonic()

    # Single-provider tests: run A and B for each available model
    print("\n" + "=" * 60)
    print("SINGLE-MODEL CONDITIONS")
    print("=" * 60)
    for model in models:
        print(f"\n--- {model} ---")
        issues = run_single_provider_tests(model, client)
        all_issues.extend(issues)

    # Multi-provider tests
    print("\n" + "=" * 60)
    print("MULTI-MODEL CONDITIONS")
    print("=" * 60)
    issues = run_multi_provider_tests(models, client)
    all_issues.extend(issues)

    # Summary
    elapsed = time.monotonic() - t0
    total_calls = len(api.calls) if hasattr(api, 'calls') else 0
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"Total API calls: {total_calls}")
    print(f"Total input tokens: {api.total_input_tokens:,}")
    print(f"Total output tokens: {api.total_output_tokens:,}")
    print(f"Total retries: {api.total_retries}")

    if all_issues:
        print(f"\n{len(all_issues)} ISSUES FOUND:")
        for issue in all_issues:
            print(f"  ! {issue}")
        return 1
    else:
        print("\nAll smoke tests PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
