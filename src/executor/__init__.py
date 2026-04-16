"""Executor for the typed protocol IR.

Walks an Expr tree and actually runs the protocol by calling a
ModelClient. The client is injected so the executor can be driven
by a deterministic fake in tests or by a real API client in
experiments.

Two ModelClient implementations:
- FakeClient: deterministic stand-in for tests
- ApiClient: real API calls to Anthropic, OpenAI, and Google
"""

from .api_client import ApiClient, CallRecord, InfrastructureError
from .client import FakeClient, ModelClient
from .interpreter import Env, Interpreter, run
from .runtime import RAnswer, RCritique, RQuery, RScore, assert_final

__all__ = [
    "ApiClient",
    "CallRecord",
    "InfrastructureError",
    "FakeClient",
    "ModelClient",
    "Env",
    "Interpreter",
    "run",
    "RAnswer",
    "RCritique",
    "RQuery",
    "RScore",
    "assert_final",
]
