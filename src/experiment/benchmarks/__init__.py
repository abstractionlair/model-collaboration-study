"""Benchmark adapters for the experiment runner.

Each adapter implements the `Benchmark` protocol: it knows how
to load its task instances, format each as a `query_text` for
`run()`, and score a macro-model's final response executably.
Phase 1's three committed benchmarks (SWE-bench Verified,
LiveCodeBench, BFCL) will each land here; HumanEval is a
framework-validation adapter that deliberately stays out of
the Phase 1 matrix.
"""

from .base import Benchmark, ScoreResult, Task
from .bfcl import BFCLBench
from .humaneval import HumanEvalBench
from .livecodebench import LiveCodeBenchBench

__all__ = [
    "Benchmark",
    "ScoreResult",
    "Task",
    "BFCLBench",
    "HumanEvalBench",
    "LiveCodeBenchBench",
]
