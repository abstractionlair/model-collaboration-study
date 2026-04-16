"""Tracing wrapper for ModelClient.

Captures full request/response pairs for every call, enabling
inspection of intermediate protocol steps (critiques, revisions,
fuse outputs, etc.) without modifying the executor or the
underlying client.

Usage:
    client = TracingClient(ApiClient())
    result = run(protocol, client, query)
    for entry in client.trace:
        print(entry)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .client import ModelClient


@dataclass(frozen=True)
class TraceEntry:
    """One model call with full request and response."""
    call_number: int
    model: str
    system: str
    user_prompt: str
    response: str
    latency_seconds: float

    @property
    def step_type(self) -> str:
        """Classify this call by what the prompt is asking for.

        Order matters: revise prompts contain "critique" (in the
        embedded critique text), so "revise" must be checked before
        "review"/"critique".
        """
        lower = self.user_prompt.lower()
        if "write your own response" in lower and "peer drafts" in lower:
            return "fuse"
        if "confidence" in lower and "0.0-1.0" in lower:
            return "score"
        if "revise the draft" in lower or "revised answer" in lower:
            return "revise"
        if "review" in lower or "critique" in lower:
            return "review"
        return "gen"

    def summary(self, max_response: int = 200) -> str:
        """One-line summary for quick inspection."""
        resp_preview = self.response[:max_response]
        if len(self.response) > max_response:
            resp_preview += "..."
        return (
            f"[{self.call_number}] {self.step_type:6s} "
            f"model={self.model} "
            f"({self.latency_seconds:.1f}s) "
            f"→ {resp_preview!r}"
        )


class TracingClient:
    """Wraps any ModelClient and records full request/response traces.

    Satisfies ModelClient protocol itself, so it can be used
    anywhere a ModelClient is expected.
    """

    def __init__(self, inner: Any) -> None:
        self.inner: Any = inner
        self.trace: list[TraceEntry] = []

    def complete(self, model: str, system: str, user: str) -> str:
        t0 = time.monotonic()
        response: str = self.inner.complete(model, system, user)
        latency = time.monotonic() - t0
        self.trace.append(TraceEntry(
            call_number=len(self.trace) + 1,
            model=model,
            system=system,
            user_prompt=user,
            response=response,
            latency_seconds=latency,
        ))
        return response

    def print_trace(self, max_response: int = 200) -> None:
        """Print a human-readable trace summary."""
        for entry in self.trace:
            print(entry.summary(max_response))

    def clear(self) -> None:
        """Clear the trace for reuse."""
        self.trace.clear()
