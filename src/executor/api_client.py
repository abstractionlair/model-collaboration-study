"""Real model client backed by Anthropic, OpenAI, and Google APIs.

Routes model IDs to the appropriate provider SDK, retries
infrastructure failures with exponential backoff, and tracks
token usage for cost accounting.

Provider routing is by model-ID prefix:
  - "claude-*"  → Anthropic
  - "gpt-*"     → OpenAI
  - "gemini-*"  → Google

API keys are read from environment variables:
  - ANTHROPIC_API_KEY
  - OPENAI_API_KEY
  - GOOGLE_API_KEY  (or GEMINI_API_KEY)

SDK clients are created lazily on first use, so missing keys for
unused providers don't cause errors.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic
import google.genai
import google.genai.errors
import google.genai.types
import openai


logger = logging.getLogger(__name__)


# ============================================================================
# Call record — what we track per API call
# ============================================================================

@dataclass(frozen=True)
class CallRecord:
    """One model API call with usage and cost metadata."""
    model: str
    input_tokens: int
    output_tokens: int
    latency_seconds: float
    retries: int  # infra retries before success


# ============================================================================
# Infrastructure error — the retryable kind
# ============================================================================

class InfrastructureError(Exception):
    """Retryable infrastructure failure (network, rate limit, server error).

    Wraps the provider-specific exception so retry logic doesn't need
    to know which SDK threw. The original exception is chained via
    __cause__.
    """
    pass


# ============================================================================
# Provider-specific infrastructure error classification
# ============================================================================

_ANTHROPIC_INFRA = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.InternalServerError,
    anthropic.RateLimitError,
)

_OPENAI_INFRA = (
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.InternalServerError,
    openai.RateLimitError,
)

_GOOGLE_INFRA = (
    google.genai.errors.ServerError,
    google.genai.errors.ClientError,
)


# ============================================================================
# The client
# ============================================================================

class ApiClient:
    """Real model client routing to Anthropic, OpenAI, and Google APIs.

    Satisfies the ModelClient protocol from src/executor/client.py.
    Tracks every call in self.calls for cost accounting.

    Infrastructure failures (network, rate limits, server errors) are
    retried with exponential backoff. Capability failures (the model
    returns a response, even an empty or wrong one) are NOT retried —
    they pass through to the caller.
    """

    def __init__(
        self,
        *,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        backoff_max: float = 60.0,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> None:
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.calls: list[CallRecord] = []

        # Lazy-init SDK clients on first use
        self._anthropic: anthropic.Anthropic | None = None
        self._openai: openai.OpenAI | None = None
        self._google: google.genai.Client | None = None

    # ------------------------------------------------------------------
    # Lazy provider initialization
    # ------------------------------------------------------------------

    def _get_anthropic(self) -> anthropic.Anthropic:
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic()
        return self._anthropic

    def _get_openai(self) -> openai.OpenAI:
        if self._openai is None:
            self._openai = openai.OpenAI()
        return self._openai

    def _get_google(self) -> google.genai.Client:
        if self._google is None:
            api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get(
                "GEMINI_API_KEY"
            )
            if not api_key:
                raise ValueError(
                    "Set GOOGLE_API_KEY or GEMINI_API_KEY to use Gemini models"
                )
            self._google = google.genai.Client(api_key=api_key)
        return self._google

    # ------------------------------------------------------------------
    # Provider routing
    # ------------------------------------------------------------------

    def _route(self, model: str) -> str:
        """Return the provider name for a model ID."""
        if model.startswith("claude"):
            return "anthropic"
        if model.startswith("gpt"):
            return "openai"
        if model.startswith("gemini"):
            return "google"
        raise ValueError(
            f"Unknown model prefix: {model!r}. "
            "Expected 'claude-*', 'gpt-*', or 'gemini-*'."
        )

    # ------------------------------------------------------------------
    # Provider-specific calls
    # ------------------------------------------------------------------

    def _call_anthropic(
        self, model: str, system: str, user: str
    ) -> tuple[str, int, int]:
        """Call Anthropic API. Returns (text, input_tokens, output_tokens)."""
        client = self._get_anthropic()
        try:
            response = client.messages.create(
                model=model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except _ANTHROPIC_INFRA as e:
            raise InfrastructureError(str(e)) from e

        # Extract text from the first TextBlock in the response.
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text = block.text
                break
        return (
            text,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

    def _call_openai(
        self, model: str, system: str, user: str
    ) -> tuple[str, int, int]:
        """Call OpenAI API. Returns (text, input_tokens, output_tokens)."""
        client = self._get_openai()
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except _OPENAI_INFRA as e:
            raise InfrastructureError(str(e)) from e

        text = response.choices[0].message.content or "" if response.choices else ""
        usage = response.usage
        return (
            text,
            usage.prompt_tokens if usage else 0,
            usage.completion_tokens if usage else 0,
        )

    def _call_google(
        self, model: str, system: str, user: str
    ) -> tuple[str, int, int]:
        """Call Google GenAI API. Returns (text, input_tokens, output_tokens)."""
        client = self._get_google()
        try:
            response = client.models.generate_content(
                model=model,
                contents=user,
                config=google.genai.types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=self.max_tokens,
                    temperature=self.temperature,
                ),
            )
        except _GOOGLE_INFRA as e:
            raise InfrastructureError(str(e)) from e

        text = response.text or ""
        usage = response.usage_metadata
        input_tok = (usage.prompt_token_count or 0) if usage else 0
        output_tok = (usage.candidates_token_count or 0) if usage else 0
        return (text, input_tok, output_tok)

    # ------------------------------------------------------------------
    # Main entry point (satisfies ModelClient protocol)
    # ------------------------------------------------------------------

    def complete(self, model: str, system: str, user: str) -> str:
        """Call a model API with retry logic for infrastructure failures.

        Infrastructure failures (network, rate limits, server errors)
        are retried with exponential backoff. Capability failures (the
        model responds, but the response is wrong/empty) pass through.
        """
        provider = self._route(model)
        call_fn = {
            "anthropic": self._call_anthropic,
            "openai": self._call_openai,
            "google": self._call_google,
        }[provider]

        retries = 0
        t0 = time.monotonic()

        for attempt in range(self.max_retries + 1):
            try:
                text, input_tokens, output_tokens = call_fn(model, system, user)
                latency = time.monotonic() - t0
                self.calls.append(CallRecord(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_seconds=latency,
                    retries=retries,
                ))
                return text

            except InfrastructureError as e:
                retries += 1
                if attempt == self.max_retries:
                    logger.error(
                        "Infrastructure failure on %s after %d retries: %s",
                        model, retries, e,
                    )
                    raise
                delay = min(
                    self.backoff_base * (2 ** attempt),
                    self.backoff_max,
                )
                logger.warning(
                    "Infrastructure failure on %s (attempt %d/%d), "
                    "retrying in %.1fs: %s",
                    model, attempt + 1, self.max_retries + 1, delay, e,
                )
                time.sleep(delay)

        # Unreachable, but makes mypy happy
        raise RuntimeError("Retry loop exited unexpectedly")

    # ------------------------------------------------------------------
    # Usage summaries
    # ------------------------------------------------------------------

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    @property
    def total_retries(self) -> int:
        return sum(c.retries for c in self.calls)
