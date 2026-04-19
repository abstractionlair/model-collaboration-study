"""Parser unit tests: _parse_score and _parse_pick.

The parsers extract structured signals from free-form model
responses. Earlier versions silently fell back to degenerate
values (0.5 and index 0) on parse failure, compounding with
positional bias in WeightedVote/PickOne to produce silent
systematic errors. The current parsers return None on failure
so the caller can log and fall back explicitly.
"""

from __future__ import annotations

from src.executor.interpreter import _parse_pick, _parse_score


# ----------------------------------------------------------------
# _parse_score
# ----------------------------------------------------------------


def test_parse_score_plain_float() -> None:
    assert _parse_score("0.7") == 0.7


def test_parse_score_with_prose() -> None:
    assert _parse_score("Confidence: 0.85") == 0.85
    assert _parse_score("Score: 0.8 (high confidence)") == 0.8


def test_parse_score_prefers_last_valid_float() -> None:
    """Models often echo a scale ("on a scale of 0.0-1.0") before
    the answer; we want the last float, not the first."""
    assert _parse_score("On a scale of 0.0 to 1.0, my answer is 0.9") == 0.9


def test_parse_score_out_of_10_pattern() -> None:
    assert _parse_score("I'd rate this 7 out of 10") == 0.7
    assert _parse_score("8/10") == 0.8


def test_parse_score_scale_echo_does_not_hijack_n_out_of_10() -> None:
    """Round-3 review (Codex, Gemini) catch: scale-echo responses
    that ALSO use an N/10 framing must parse to N/10, not to the
    echoed scale endpoints. Previously this returned 0.0 or 1.0."""
    assert _parse_score(
        "On a scale of 0.0-1.0, I'd rate this 7 out of 10"
    ) == 0.7
    assert _parse_score(
        "On a scale of 0.0 to 1.0, I'd rate this 7 out of 10"
    ) == 0.7
    assert _parse_score(
        "Using the 0.0-1.0 scale, my confidence is 8/10"
    ) == 0.8


def test_parse_score_labeled_pattern() -> None:
    """'Score: X' / 'Confidence = X' / 'Rating is X' patterns are
    high-signal and should be picked up before the generic
    last-float fallback."""
    assert _parse_score("Score: 0.7") == 0.7
    assert _parse_score("Confidence = 0.85") == 0.85
    assert _parse_score("Rating is 0.4") == 0.4


def test_parse_score_bare_number() -> None:
    """Compliant responses are bare numbers."""
    assert _parse_score("0.42") == 0.42
    assert _parse_score("0.42.") == 0.42  # trailing punctuation OK
    assert _parse_score("  0.42  ") == 0.42  # whitespace OK


def test_parse_score_returns_none_on_non_numeric() -> None:
    assert _parse_score("I think this is pretty good") is None
    assert _parse_score("High") is None
    assert _parse_score("") is None


def test_parse_score_returns_none_when_only_out_of_range_numbers() -> None:
    """If the response has numbers but none in [0,1] and no
    recognizable ratio pattern, we can't honestly extract a
    confidence."""
    # "42" by itself doesn't mean anything in [0,1]; return None.
    assert _parse_score("42") is None


def test_parse_score_handles_negatives() -> None:
    """Negative floats are not in [0,1] and not valid; return None."""
    assert _parse_score("-0.3") is None


# ----------------------------------------------------------------
# _parse_pick
# ----------------------------------------------------------------


def test_parse_pick_plain_integer() -> None:
    assert _parse_pick("2", n=3) == 1  # 1-indexed → 0-indexed
    assert _parse_pick("2.", n=3) == 1  # trailing punctuation OK
    assert _parse_pick("  2  ", n=3) == 1  # whitespace OK


def test_parse_pick_bare_candidate_response() -> None:
    """Compliant responses to 'respond with ONLY the candidate
    number' may include the 'Candidate' prefix."""
    assert _parse_pick("Candidate 3", n=3) == 2
    assert _parse_pick("Candidate 2.", n=3) == 1


def test_parse_pick_uses_pick_verb_not_negative_reference() -> None:
    """Round-3 review (Codex, Gemini) catch: when the response
    mentions multiple candidates, the parser must pick the one
    associated with a pick verb, not the one being rejected.

    Previously the parser grabbed the LAST in-range integer,
    which means 'I pick 2 because candidate 3 is incomplete'
    parsed as candidate 3 (wrong). Now the pick-verb pattern
    catches "I pick 2" first.
    """
    assert _parse_pick("I pick 2 because candidate 3 is incomplete", n=3) == 1
    assert _parse_pick("Choose candidate 1", n=3) == 0
    assert _parse_pick("I select 3", n=3) == 2
    assert _parse_pick("Winner: 2", n=3) == 1
    assert _parse_pick("The answer is 1", n=3) == 0


def test_parse_pick_returns_none_on_ambiguous() -> None:
    """When the response mentions candidates without a clear
    pick verb, prefer None over guessing — the runner falls back
    to seeded random with telemetry."""
    # Multiple candidates mentioned, no pick verb → ambiguous.
    assert _parse_pick(
        "Candidate 2 and Candidate 3 are both reasonable", n=3,
    ) is None
    # Just discussing candidates without selecting.
    assert _parse_pick("Between 1 and 3", n=3) is None


def test_parse_pick_returns_none_on_non_integer() -> None:
    assert _parse_pick("I like them all", n=3) is None


def test_parse_pick_returns_none_on_out_of_range() -> None:
    assert _parse_pick("42", n=3) is None
    assert _parse_pick("0", n=3) is None  # 1-indexed, 0 invalid
