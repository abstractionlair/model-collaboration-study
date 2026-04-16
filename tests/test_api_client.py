"""Tests for ApiClient failure classification and CallRecord telemetry.

Focuses on the boundary decisions that matter for the design's
infra-vs-capability failure policy:

- Google's ClientError covers ALL 4xx; we need to narrow to
  only 408/429 as retryable. Other 4xx should propagate as
  regular exceptions (not InfrastructureError).
- Empty/whitespace-only responses are capability failures, not
  successes.
- CallRecord.status distinguishes success / capability_failure /
  infra_failure so the runner can audit what happened.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import google.genai.errors
import pytest

from src.executor.api_client import (
    ApiClient,
    CapabilityFailure,
    InfrastructureError,
    _is_google_infra,
)


# ----------------------------------------------------------------
# Google retry classification
# ----------------------------------------------------------------


def _make_google_client_error(code: int) -> google.genai.errors.ClientError:
    """Construct a ClientError directly (bypasses __init__'s JSON
    parsing) to simulate different HTTP status codes."""
    exc = google.genai.errors.ClientError.__new__(google.genai.errors.ClientError)
    exc.code = code
    exc.status = f"HTTP {code}"
    exc.details = {}
    exc.response = None
    exc.message = None
    return exc


def _make_google_server_error(code: int) -> google.genai.errors.ServerError:
    exc = google.genai.errors.ServerError.__new__(google.genai.errors.ServerError)
    exc.code = code
    exc.status = f"HTTP {code}"
    exc.details = {}
    exc.response = None
    exc.message = None
    return exc


def test_google_server_errors_are_infra() -> None:
    """All 5xx should retry."""
    for code in (500, 502, 503, 504):
        assert _is_google_infra(_make_google_server_error(code)), (
            f"5xx code {code} should be classified infra"
        )


def test_google_retryable_4xx_are_infra() -> None:
    """408 (Request Timeout) and 429 (Too Many Requests) should retry."""
    assert _is_google_infra(_make_google_client_error(408))
    assert _is_google_infra(_make_google_client_error(429))


def test_google_non_retryable_4xx_are_not_infra() -> None:
    """400/401/403/404/422 are config/capability issues; retrying
    them burns quota and masks real problems."""
    for code in (400, 401, 403, 404, 422):
        assert not _is_google_infra(_make_google_client_error(code)), (
            f"4xx code {code} should NOT be classified infra"
        )


def test_google_unrelated_exception_not_infra() -> None:
    assert not _is_google_infra(ValueError("unrelated"))


# ----------------------------------------------------------------
# Empty-response → CapabilityFailure
# ----------------------------------------------------------------


def test_empty_response_raises_capability_failure() -> None:
    """Empty or whitespace-only responses should not silently
    propagate as successful calls; they're capability failures
    per the design."""
    client = ApiClient(max_retries=1)
    # Stub the route + call_fn to return empty text
    client._route = lambda model: "anthropic"  # type: ignore[method-assign]
    fake_call = MagicMock(return_value=("   \n  ", 100, 0))
    client._call_anthropic = fake_call  # type: ignore[method-assign]

    with pytest.raises(CapabilityFailure):
        client.complete("claude-test", "sys", "user")

    assert len(client.calls) == 1
    assert client.calls[0].status == "capability_failure"
    assert client.calls[0].input_tokens == 100  # tokens billed
    assert "empty" in (client.calls[0].error or "")


def test_successful_call_records_status_success() -> None:
    client = ApiClient(max_retries=1)
    client._route = lambda model: "anthropic"  # type: ignore[method-assign]
    client._call_anthropic = MagicMock(  # type: ignore[method-assign]
        return_value=("hello", 50, 20),
    )

    text = client.complete("claude-test", "sys", "user")
    assert text == "hello"
    assert len(client.calls) == 1
    assert client.calls[0].status == "success"
    assert client.calls[0].error is None


# ----------------------------------------------------------------
# Exhausted infra retries recorded
# ----------------------------------------------------------------


def test_exhausted_infra_retries_record_call() -> None:
    """After max_retries on infra failure, the last attempt
    appends a CallRecord with status='infra_failure' before
    re-raising. Previously no record was made."""
    client = ApiClient(max_retries=1, backoff_base=0, backoff_max=0)
    client._route = lambda model: "anthropic"  # type: ignore[method-assign]

    def always_fail(*args: object, **kwargs: object) -> tuple[str, int, int]:
        raise InfrastructureError("boom")

    client._call_anthropic = always_fail  # type: ignore[method-assign]

    with pytest.raises(InfrastructureError):
        client.complete("claude-test", "sys", "user")

    # max_retries=1 → 2 total attempts → 1 CallRecord for the final exhausted one
    assert len(client.calls) == 1
    assert client.calls[0].status == "infra_failure"
    assert client.calls[0].retries == 2  # both attempts counted
    assert "boom" in (client.calls[0].error or "")


# ----------------------------------------------------------------
# Status counts properties
# ----------------------------------------------------------------


def test_status_count_properties() -> None:
    """ApiClient exposes convenience properties for counting by
    status."""
    client = ApiClient(max_retries=0, backoff_base=0, backoff_max=0)
    client._route = lambda model: "anthropic"  # type: ignore[method-assign]

    calls: list[tuple[str, int, int]] = [
        ("ok", 10, 5),
        ("", 8, 0),  # capability failure
        ("ok", 10, 5),
    ]
    call_iter = iter(calls)
    client._call_anthropic = lambda *a, **k: next(call_iter)  # type: ignore[method-assign]

    client.complete("claude-test", "sys", "1")
    with pytest.raises(CapabilityFailure):
        client.complete("claude-test", "sys", "2")
    client.complete("claude-test", "sys", "3")

    assert client.successful_calls == 2
    assert client.capability_failures == 1
    assert client.infra_failures == 0


# ----------------------------------------------------------------
# Temperature omission
# ----------------------------------------------------------------


def test_temperature_none_omits_kwarg() -> None:
    """When temperature=None (the default), the ApiClient does
    not pass `temperature` to the provider — vendor defaults
    take over. Captured via kwargs inspection on a mocked SDK."""
    client = ApiClient()  # default temperature=None
    fake_sdk = MagicMock()
    fake_sdk.messages.create.return_value = MagicMock(
        content=[MagicMock(text="ok")],
        usage=MagicMock(input_tokens=10, output_tokens=2),
    )
    client._anthropic = fake_sdk
    client.complete("claude-test", "sys", "user")

    kwargs = fake_sdk.messages.create.call_args.kwargs
    assert "temperature" not in kwargs, (
        f"expected temperature omitted; got kwargs={kwargs}"
    )


def test_temperature_explicit_is_passed() -> None:
    """Explicit temperature override reaches the provider."""
    client = ApiClient(temperature=0.5)
    fake_sdk = MagicMock()
    fake_sdk.messages.create.return_value = MagicMock(
        content=[MagicMock(text="ok")],
        usage=MagicMock(input_tokens=10, output_tokens=2),
    )
    client._anthropic = fake_sdk
    client.complete("claude-test", "sys", "user")

    kwargs = fake_sdk.messages.create.call_args.kwargs
    assert kwargs["temperature"] == 0.5
