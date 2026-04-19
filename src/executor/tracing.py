"""Tracing wrapper for ModelClient.

Captures full request/response pairs for every call, enabling
inspection of intermediate protocol steps (critiques, revisions,
fuse outputs, etc.) without modifying the executor or the
underlying client.

Usage:
    client = TracingClient(ApiClient())
    result, telemetry = run(protocol, client, query)
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

        Order matters. More-specific prompts (fuse_with_critiques,
        pick_one) are checked before less-specific ones (fuse,
        review) because the specific prompts share substrings with
        the general ones. Revise before review/critique because
        revise prompts embed critique text.

        Brittleness note: the classifier inspects prompt-text
        substrings. Custom PromptTemplates with different wording
        will silently misclassify. Known-limitation; fixing
        structurally would require plumbing the step type through
        the executor as explicit metadata. Tracked in review #15
        of `docs/reviews/system-review-opus47-2026-04-16.md`.
        """
        lower = self.user_prompt.lower()
        # More-specific matchers first (they share substrings with
        # the general ones).
        if "critique of draft" in lower and "synthesize" in lower:
            return "fuse_with_critiques"
        if "pick the single best" in lower and "candidate number" in lower:
            return "pick_one"
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
