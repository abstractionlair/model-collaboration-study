"""Real model client backed by Anthropic, OpenAI, Google, and xAI APIs.

Routes model IDs to the appropriate provider SDK, retries
infrastructure failures with exponential backoff, and tracks
token usage for cost accounting.

Provider routing is by model-ID prefix:
  - "claude-*"  → Anthropic
  - "gpt-*"     → OpenAI
  - "gemini-*"  → Google
  - "grok-*"    → xAI (OpenAI-compatible API)

API keys are read from environment variables:
  - ANTHROPIC_API_KEY
  - OPENAI_API_KEY
  - GOOGLE_API_KEY  (or GEMINI_API_KEY)
  - XAI_API_KEY

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
import httpx
import openai


logger = logging.getLogger(__name__)


# ============================================================================
# Call record — what we track per API call
# ============================================================================

@dataclass(frozen=True)
class CallRecord:
    """One model API attempt with usage and cost metadata.

    `status` is one of:
      - "success": call succeeded, text returned normally
      - "capability_failure": call returned (tokens billed) but
        the response is unusable (e.g., empty or whitespace-only)
      - "infra_failure": infrastructure error exhausted retries;
        token counts will typically be zero since no successful
        response was produced

    Capability failures still record their tokens because they
    count against the dollar budget (the macro-model did spend
    money to produce zero-length output). Infra failures do not
    count against the budget per the design's failure-handling
    policy; they're logged here purely as diagnostic telemetry.
    """
    model: str
    input_tokens: int
    output_tokens: int
    latency_seconds: float
    retries: int
    status: str = "success"
    error: str | None = None


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


class CapabilityFailure(Exception):
    """Non-retryable capability failure (e.g., empty response).

    Raised when a call completes successfully at the API level
    but the macro-model's function-from-context-to-response is
    broken for that input (per the design: zero-length output
    is a capability failure, not infrastructure). Tokens have
    already been billed by the time this is raised; the
    corresponding CallRecord is appended with status =
    "capability_failure" before the raise.
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

# Google SDK: ServerError covers 5xx; ClientError covers ALL 4xx
# (including 400 Bad Request, 401/403 auth, 404 not-found), most
# of which are NOT retryable. The helper below filters to only
# the retryable subset. httpx connection / timeout errors are
# also treated as infra.
_GOOGLE_RETRYABLE_HTTP_CODES = frozenset({408, 429})


def _is_google_infra(exc: BaseException) -> bool:
    """Identify Google SDK exceptions that deserve retry as infra.

    - ServerError (5xx) — retry
    - ClientError with status 408 Request Timeout or 429 Too
      Many Requests — retry
    - ClientError with other 4xx (400, 401, 403, 404, 422, ...)
      — do NOT retry (these are config or capability issues;
      retrying burns quota and masks the underlying problem).
    - httpx network/timeout errors — retry (transport-level).
    """
    if isinstance(exc, google.genai.errors.ServerError):
        return True
    if isinstance(exc, google.genai.errors.ClientError):
        return exc.code in _GOOGLE_RETRYABLE_HTTP_CODES
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    return False


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
        temperature: float | None = None,
        max_tokens: int = 4096,
    ) -> None:
        """Construct the client.

        `temperature=None` (the default) means "use each vendor's
        default." Modern models are tuned for their defaults;
        forcing `temperature=0` causes mode collapse on
        homogeneous pools and picking a non-default number is
        guessing against the vendor's tuning. Override explicitly
        for reproducibility testing or for temperature
        ablations — not as a blanket "same-across-providers"
        guard. See `docs/decisions.md` 2026-04-16 for the policy.

        `max_tokens` stays pinned because all vendors need some
        limit and bounding it protects the dollar budget.
        """
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
        self._xai: openai.OpenAI | None = None

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

    def _get_xai(self) -> openai.OpenAI:
        if self._xai is None:
            api_key = os.environ.get("XAI_API_KEY")
            if not api_key:
                raise ValueError("Set XAI_API_KEY to use Grok models")
            self._xai = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.x.ai/v1",
            )
        return self._xai

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
        if model.startswith("grok"):
            return "xai"
        raise ValueError(
            f"Unknown model prefix: {model!r}. "
            "Expected 'claude-*', 'gpt-*', 'gemini-*', or 'grok-*'."
        )

    # ------------------------------------------------------------------
    # Provider-specific calls
    # ------------------------------------------------------------------

    def _call_anthropic(
        self, model: str, system: str, user: str
    ) -> tuple[str, int, int]:
        """Call Anthropic API. Returns (text, input_tokens, output_tokens)."""
        client = self._get_anthropic()
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        try:
            response = client.messages.create(**kwargs)
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
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        try:
            response = client.chat.completions.create(**kwargs)
        except _OPENAI_INFRA as e:
            raise InfrastructureError(str(e)) from e

        text = response.choices[0].message.content or "" if response.choices else ""
        usage = response.usage
        return (
            text,
            usage.prompt_tokens if usage else 0,
            usage.completion_tokens if usage else 0,
        )

    def _call_xai(
        self, model: str, system: str, user: str
    ) -> tuple[str, int, int]:
        """Call xAI API (OpenAI-compatible). Returns (text, input_tokens, output_tokens)."""
        client = self._get_xai()
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        try:
            response = client.chat.completions.create(**kwargs)
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
        config_kwargs: dict[str, Any] = {
            "system_instruction": system,
            "max_output_tokens": self.max_tokens,
        }
        if self.temperature is not None:
            config_kwargs["temperature"] = self.temperature
        try:
            response = client.models.generate_content(
                model=model,
                contents=user,
                config=google.genai.types.GenerateContentConfig(**config_kwargs),
            )
        except google.genai.errors.APIError as e:
            if _is_google_infra(e):
                raise InfrastructureError(str(e)) from e
            raise  # 400/401/403/404/etc. — capability/config, not infra
        except (httpx.TimeoutException, httpx.NetworkError) as e:
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

        Infrastructure failures (network, rate limits, 5xx, narrowly
        scoped 4xx like 408/429) are retried with exponential
        backoff. Other 4xx (400/401/403/404/...) pass through as
        regular exceptions — they're config/capability issues and
        retrying burns quota without helping.

        Empty or whitespace-only responses at the API layer are
        treated as capability failures per the design's failure-
        handling policy: the macro-model's function-from-context-
        to-response is broken for that input. Tokens are recorded
        (cost was spent) and a CapabilityFailure is raised.

        Every attempt — success, exhausted-infra, and capability
        failure — produces a CallRecord with an appropriate
        status field. Success records carry full tokens;
        exhausted-infra records carry zero tokens and the last
        error message; capability-failure records carry full
        tokens and the failure message.
        """
        provider = self._route(model)
        call_fn = {
            "anthropic": self._call_anthropic,
            "openai": self._call_openai,
            "google": self._call_google,
            "xai": self._call_xai,
        }[provider]

        retries = 0
        t0 = time.monotonic()

        for attempt in range(self.max_retries + 1):
            try:
                text, input_tokens, output_tokens = call_fn(model, system, user)
                latency = time.monotonic() - t0
                if not text.strip():
                    err = (
                        f"empty/whitespace-only response from {model} "
                        f"(tokens billed; treated as capability failure)"
                    )
                    self.calls.append(CallRecord(
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        latency_seconds=latency,
                        retries=retries,
                        status="capability_failure",
                        error=err,
                    ))
                    logger.warning(err)
                    raise CapabilityFailure(err)
                self.calls.append(CallRecord(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_seconds=latency,
                    retries=retries,
                    status="success",
                ))
                return text

            except InfrastructureError as e:
                retries += 1
                if attempt == self.max_retries:
                    latency = time.monotonic() - t0
                    err = str(e)
                    self.calls.append(CallRecord(
                        model=model,
                        input_tokens=0,
                        output_tokens=0,
                        latency_seconds=latency,
                        retries=retries,
                        status="infra_failure",
                        error=err,
                    ))
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

    @property
    def successful_calls(self) -> int:
        return sum(1 for c in self.calls if c.status == "success")

    @property
    def infra_failures(self) -> int:
        return sum(1 for c in self.calls if c.status == "infra_failure")

    @property
    def capability_failures(self) -> int:
        return sum(1 for c in self.calls if c.status == "capability_failure")
