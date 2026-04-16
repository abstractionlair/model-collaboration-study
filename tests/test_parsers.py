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


def test_parse_pick_candidate_prefix() -> None:
    assert _parse_pick("Candidate 3", n=3) == 2
    assert _parse_pick("I pick candidate 2.", n=3) == 1


def test_parse_pick_prefers_candidate_prefix_over_trailing_int() -> None:
    """If the response says 'Candidate 2' and also has a '5' in the
    rationale, we prefer the labeled selection."""
    assert _parse_pick("Candidate 2 because the 5 other drafts were wrong", n=3) == 1


def test_parse_pick_prefers_last_integer_in_range() -> None:
    """Without a 'Candidate N' label, prefer the last in-range
    integer (usually the final selection)."""
    assert _parse_pick("Between 1 and 3, I pick 3", n=3) == 2


def test_parse_pick_returns_none_on_non_integer() -> None:
    assert _parse_pick("I like them all", n=3) is None


def test_parse_pick_returns_none_on_out_of_range() -> None:
    assert _parse_pick("42", n=3) is None
    assert _parse_pick("0", n=3) is None  # 1-indexed, 0 invalid
