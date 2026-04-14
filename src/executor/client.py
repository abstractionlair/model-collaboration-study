"""Model client protocol and a deterministic fake implementation.

The executor only needs to call one operation on a model:
    complete(model_name, system, user) -> str

Anything that satisfies this Protocol can drive the executor. A
real client would wrap the Anthropic or OpenAI SDK; the fake
client here is what the test suite and early harness runs against.

The fake is intentionally simple and deterministic: it returns
structured strings that encode which model was called and what
role-shaped prompt it saw, so tests can assert on shape without
brittle text comparisons. For prompts that look like a confidence
request, it returns a short parseable float.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol


class ModelClient(Protocol):
    def complete(self, model: str, system: str, user: str) -> str: ...


@dataclass
class FakeClient:
    """Deterministic stand-in for a real model client.

    Records every call so tests can assert on call count, which
    models were invoked, and which prompt shapes each saw.
    """
    calls: list[tuple[str, str, str]] = field(default_factory=list)
    # Optional override: if set, used to produce the response for a
    # given (model, user_prompt) pair. Lets tests inject specific
    # answers without subclassing.
    responder: Callable[[str, str, str], str] | None = None

    def complete(self, model: str, system: str, user: str) -> str:
        self.calls.append((model, system, user))
        if self.responder is not None:
            return self.responder(model, system, user)
        lower = user.lower()
        if "confidence" in lower or "rate" in lower:
            # Vary scores per model so WeightedVote is non-trivial.
            base = (abs(hash(model)) % 50) / 100.0  # 0.00–0.49
            return f"{0.5 + base:.2f}"
        tag = "review" if "review" in lower or "critique" in lower else (
            "revise" if "revise" in lower else "gen"
        )
        return f"[{tag}|{model}|call#{len(self.calls)}]"
