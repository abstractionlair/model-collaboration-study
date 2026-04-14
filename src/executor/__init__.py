"""Minimal executor for the typed protocol IR.

Walks an Expr tree and actually runs the protocol by calling a
ModelClient. The client is injected so the executor can be driven
by a deterministic fake in tests or by a real API client in
experiments.

Prompts and model routing belong in the experiment-spec layer that
isn't built yet; for now the executor carries default templates
inline. Anything prompt-shaped here is a placeholder.
"""

from .runtime import RAnswer, RCritique, RQuery, RScore
from .client import FakeClient, ModelClient
from .interpreter import Env, Interpreter, run
from .runtime import assert_final

__all__ = [
    "RAnswer",
    "RCritique",
    "RQuery",
    "RScore",
    "FakeClient",
    "ModelClient",
    "Env",
    "Interpreter",
    "run",
    "assert_final",
]
