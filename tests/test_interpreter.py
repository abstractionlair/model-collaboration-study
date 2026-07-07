"""Executor unit tests with FakeClient.

Verifies the invariants the architecture doc claims but that
were not checked in committed form:

- Identity memoization: a shared sub-expression evaluates once.
- ParGen and ParScore alignment with the models list.
- SelfReviseRound and PeerReviseRound call-count math.
- PeerReviseRound cyclic 1-peer assignment (reviewer ≠ writer).
- Rounds(N) applies single-round N times.
- WeightedVote selects argmax; tie-break is non-positional.
- PickOne selects the parsed candidate; parse-failure fallback
  is non-positional.
- FuseWithCritiques receives drafts aligned with critiques.
- ParPeerReview returns critiques aligned with the input drafts.

These are the behaviors most likely to silently regress under
future refactors. FakeClient is deterministic, so the tests
pin exact call counts and sequences.
"""

from __future__ import annotations

import pytest

from src.executor import FakeClient, Interpreter, ParseFailure, run
from src.ir.surface import (
    FRESH,
    PEERS_GROUPED,
    bind,
    fuse,
    fuse_with_critiques,
    gen,
    par_gen,
    par_peer_review,
    par_score,
    peer_revise_round,
    peer_rounds,
    pick_one,
    query,
    review,
    revise,
    self_revise_round,
    self_rounds,
    weighted_vote,
)
from src.ir.ast import Finalize
from src.ir.types import ParseFailurePolicy, TieBreakPolicy
from src.protocols.ccr import ccr
from src.protocols.conditions import (
    condition_a,
    condition_b,
    condition_c,
    condition_d_prime,
    condition_e,
    condition_e_writers_revise_then_fuse,
)
from src.protocols.reconcile import reconcile


# ----------------------------------------------------------------
# Identity memoization
# ----------------------------------------------------------------


def test_ccr_makes_three_calls_not_four() -> None:
    """CCR's draft is shared between review and revise; without
    identity memoization it'd be generated twice (4 calls)."""
    client = FakeClient()
    run(ccr("m1"), client, "q")
    assert len(client.calls) == 3, (
        "CCR should issue 3 calls (gen, review, revise) via shared draft; "
        f"got {len(client.calls)}"
    )


def test_shared_subtree_via_bind_evaluates_once() -> None:
    """bind()'s Var body may reference the bound value multiple
    times; each reference should hit the memoization cache."""
    q = query()
    drafts = par_gen(["m1", "m2"], q)
    protocol = bind(
        drafts,
        lambda ds: weighted_vote(ds, par_score(["m1", "m2"], ds)),
    )
    client = FakeClient()
    run(Finalize(draft=protocol), client, "q")
    # 2 gens + 2 scores = 4 calls. If memoization failed, ParScore
    # would re-trigger ParGen for another 2 calls (6 total).
    assert len(client.calls) == 4


# ----------------------------------------------------------------
# ParGen / ParScore alignment
# ----------------------------------------------------------------


def test_pargen_models_align_with_call_sequence() -> None:
    """par_gen(['m1', 'm2', 'm3']) issues calls in that model order."""
    q = query()
    drafts = par_gen(["m1", "m2", "m3"], q)
    client = FakeClient()
    run(Finalize(draft=bind(drafts, lambda ds: fuse("m1", ds, q))), client, "q")
    gen_models = [c[0] for c in client.calls if "Provide your answer" in c[2]]
    assert gen_models == ["m1", "m2", "m3"]


def test_parscore_aligns_model_i_with_draft_i() -> None:
    """par_score scores drafts[i] using models[i]; the i-th score
    call's model matches the i-th model in the list."""
    q = query()
    drafts = par_gen(["m1", "m2", "m3"], q)
    protocol = bind(
        drafts,
        lambda ds: weighted_vote(ds, par_score(["m1", "m2", "m3"], ds)),
    )
    client = FakeClient()
    run(Finalize(draft=protocol), client, "q")
    # Identify the 3 score calls by prompt shape (confidence request).
    score_calls = [c for c in client.calls if "Rate your confidence" in c[2]]
    assert len(score_calls) == 3
    assert [c[0] for c in score_calls] == ["m1", "m2", "m3"]


def test_parscore_model_draft_count_mismatch_raises() -> None:
    """A ParScore whose scorer list is shorter than its draft list
    must fail loudly. The typed IR does not encode list lengths, so
    without a runtime guard `zip` would silently truncate and a
    malformed protocol could aggregate over partially scored
    candidates."""
    q = query()
    drafts = par_gen(["m1", "m2", "m3"], q)
    protocol = bind(
        drafts,
        # 2 scorers for 3 drafts: malformed.
        lambda ds: weighted_vote(ds, par_score(["m1", "m2"], ds)),
    )
    client = FakeClient()
    with pytest.raises(ValueError, match="ParScore"):
        run(Finalize(draft=protocol), client, "q")


# ----------------------------------------------------------------
# Rounds(N) call count math
# ----------------------------------------------------------------


def test_self_rounds_multiplies_by_n() -> None:
    """self_rounds(N, ...) is N applications of self_revise_round."""
    pool = ["m1", "m2", "m3"]
    q = query()
    drafts = par_gen(pool, q)
    one_round = self_revise_round(pool, drafts, FRESH, PEERS_GROUPED)
    three_rounds = self_rounds(3, pool, drafts, FRESH, PEERS_GROUPED)

    c1 = FakeClient()
    run(Finalize(draft=fuse("m1", one_round, q)), c1, "q")
    c3 = FakeClient()
    run(Finalize(draft=fuse("m1", three_rounds, q)), c3, "q")

    # each self-round: N reviews + N revises = 2N; plus 1 gen each + 1 fuse
    per_round = 2 * len(pool)
    assert len(c1.calls) == len(pool) + per_round + 1
    assert len(c3.calls) == len(pool) + 3 * per_round + 1


# ----------------------------------------------------------------
# PeerReviseRound cyclic assignment
# ----------------------------------------------------------------


def test_peer_revise_round_reviewer_is_next_in_cycle() -> None:
    """In PeerReviseRound with models [m1, m2, m3], the reviewer
    of draft i is models[(i+1) % N]. Verified by inspecting which
    model made each review call."""
    pool = ["m1", "m2", "m3"]
    q = query()
    drafts = par_gen(pool, q)
    revised = peer_revise_round(pool, drafts, FRESH, PEERS_GROUPED)
    client = FakeClient()
    run(Finalize(draft=fuse("m1", revised, q)), client, "q")

    # Review calls are those whose prompt starts with "Review the
    # following draft answer, produced by a peer AI" (the new
    # peer-review prompt).
    review_calls = [
        c for c in client.calls
        if c[2].startswith("Review the following draft answer, produced by a peer AI")
    ]
    assert len(review_calls) == 3, f"expected 3 peer reviews; got {len(review_calls)}"
    # Draft 0 reviewed by m2, draft 1 by m3, draft 2 by m1.
    assert [c[0] for c in review_calls] == ["m2", "m3", "m1"]


def test_peer_revise_round_revise_is_original_writer() -> None:
    """After peer review, the writer m_i (not the reviewer) revises
    draft i. Verifies reviewer/writer split."""
    pool = ["m1", "m2", "m3"]
    q = query()
    drafts = par_gen(pool, q)
    revised = peer_revise_round(pool, drafts, FRESH, PEERS_GROUPED)
    client = FakeClient()
    run(Finalize(draft=fuse("m1", revised, q)), client, "q")

    revise_calls = [c for c in client.calls if "Revise the draft" in c[2]]
    assert len(revise_calls) == 3
    # Writers m1, m2, m3 revise in order.
    assert [c[0] for c in revise_calls] == ["m1", "m2", "m3"]


def test_peer_revise_round_raises_on_single_model() -> None:
    """N=1 makes cyclic peer assignment degenerate to self-review;
    the executor refuses rather than silently collapsing."""
    import pytest

    q = query()
    drafts = par_gen(["m1"], q)
    revised = peer_revise_round(["m1"], drafts, FRESH, PEERS_GROUPED)
    with pytest.raises(ValueError, match="at least 2 models"):
        run(Finalize(draft=fuse("m1", revised, q)), FakeClient(), "q")


# ----------------------------------------------------------------
# WeightedVote / PickOne
# ----------------------------------------------------------------


def test_weighted_vote_picks_argmax() -> None:
    """WeightedVote selects the draft with the highest score."""
    # Craft a responder that returns different scores per model.
    def responder(model: str, system: str, user: str) -> str:
        if "Rate your confidence" in user:
            # m1 scores 0.2, m2 scores 0.9, m3 scores 0.5
            return {"m1": "0.2", "m2": "0.9", "m3": "0.5"}[model]
        return f"draft-from-{model}"

    client = FakeClient(responder=responder)
    q = query()
    drafts = par_gen(["m1", "m2", "m3"], q)
    protocol = bind(
        drafts,
        lambda ds: weighted_vote(ds, par_score(["m1", "m2", "m3"], ds)),
    )
    result, _ = run(Finalize(draft=protocol), client, "q")
    assert result.text == "draft-from-m2", (
        f"expected m2's draft (score 0.9) to win; got {result.text!r}"
    )


def test_weighted_vote_tie_break_is_not_positional() -> None:
    """When all scores tie, WeightedVote picks randomly (with the
    seed), not always the first candidate. Run with different
    seeds and confirm both 'm1' and 'm3' can win. Also verify
    the tie is recorded in telemetry."""
    def responder(model: str, system: str, user: str) -> str:
        if "Rate your confidence" in user:
            return "0.5"  # all tie
        return f"draft-from-{model}"

    winners = set()
    last_telemetry = None
    for seed in range(10):
        client = FakeClient(responder=responder)
        q = query()
        drafts = par_gen(["m1", "m2", "m3"], q)
        protocol = bind(
            drafts,
            lambda ds: weighted_vote(ds, par_score(["m1", "m2", "m3"], ds)),
        )
        result, telemetry = run(Finalize(draft=protocol), client, "q", seed=seed)
        winners.add(result.text)
        last_telemetry = telemetry

    # With 10 different seeds, we should see at least 2 distinct winners.
    assert len(winners) >= 2, (
        f"tie-break appears positional; only saw winners {winners}"
    )
    # Telemetry should record the tie that triggered the random fallback.
    assert last_telemetry is not None
    assert last_telemetry.weighted_vote_ties == 1


def test_pick_one_selects_parsed_candidate() -> None:
    """PickOne parses the judge's 1-indexed response and returns
    that candidate."""
    def responder(model: str, system: str, user: str) -> str:
        if "pick the single best one" in user.lower():
            return "Candidate 2"
        return f"draft-from-{model}"

    client = FakeClient(responder=responder)
    q = query()
    drafts = par_gen(["m1", "m2", "m3"], q)
    result, _ = run(Finalize(draft=pick_one("m1", drafts)), client, "q")
    assert result.text == "draft-from-m2"


def test_pick_one_parse_failure_is_random_not_positional() -> None:
    """If the judge's response can't be parsed, PickOne falls back
    randomly (with seed), not to candidate 1. Telemetry records
    the parse failure."""
    def responder(model: str, system: str, user: str) -> str:
        if "pick the single best one" in user.lower():
            return "I think they're all great!"  # no parseable integer
        return f"draft-from-{model}"

    winners = set()
    last_telemetry = None
    for seed in range(10):
        client = FakeClient(responder=responder)
        q = query()
        drafts = par_gen(["m1", "m2", "m3"], q)
        result, telemetry = run(
            Finalize(draft=pick_one("m1", drafts)), client, "q", seed=seed,
        )
        winners.add(result.text)
        last_telemetry = telemetry

    assert len(winners) >= 2, (
        f"parse-failure fallback appears positional; only saw winners {winners}"
    )
    assert last_telemetry is not None
    assert last_telemetry.pick_parse_failures == 1


# ----------------------------------------------------------------
# FuseWithCritiques alignment
# ----------------------------------------------------------------


def test_fuse_with_critiques_pairs_drafts_with_critiques() -> None:
    """The FuseWithCritiques prompt contains each draft paired
    with its corresponding critique by index."""
    call_prompts: list[tuple[str, str]] = []

    def responder(model: str, system: str, user: str) -> str:
        call_prompts.append((model, user))
        if "Review the following draft answer, produced by a peer AI" in user:
            # Return a distinctive critique per review call.
            return f"critique-call-{len(call_prompts)}"
        if "Synthesize a final response" in user:
            return "final-synthesis"
        if "Provide your answer" in user:
            return f"draft-from-{model}"
        return "unknown"

    client = FakeClient(responder=responder)
    q = query()
    drafts = par_gen(["m1", "m2", "m3"], q)
    critiques = par_peer_review(["m1", "m2", "m3"], drafts, FRESH, PEERS_GROUPED)
    result, _ = run(
        Finalize(draft=fuse_with_critiques("m1", drafts, critiques, q)),
        client, "q",
    )
    assert result.text == "final-synthesis"

    # Find the fuse call and verify it has 3 drafts paired with 3 critiques.
    fuse_calls = [p for (m, p) in call_prompts if "Synthesize" in p]
    assert len(fuse_calls) == 1
    fp = fuse_calls[0]
    for i in range(1, 4):
        assert f"Draft {i}:" in fp
        assert f"Critique of Draft {i}:" in fp


def test_par_peer_review_aligns_with_input_drafts() -> None:
    """ParPeerReview produces one critique per draft; critiques[i]
    is the critique on drafts[i] (produced by peer reviewer
    models[(i+1) % N])."""
    call_models: list[str] = []

    def responder(model: str, system: str, user: str) -> str:
        if "Review the following draft answer, produced by a peer AI" in user:
            call_models.append(model)
            return f"critique-from-{model}"
        if "Provide your answer" in user:
            return f"draft-from-{model}"
        if "Synthesize" in user:
            return "fused"
        return "unknown"

    client = FakeClient(responder=responder)
    q = query()
    drafts = par_gen(["m1", "m2", "m3"], q)
    critiques = par_peer_review(["m1", "m2", "m3"], drafts, FRESH, PEERS_GROUPED)
    run(
        Finalize(draft=fuse_with_critiques("meta", drafts, critiques, q)),
        client, "q",
    )
    # Cyclic shift by one: critique_0 by m2, critique_1 by m3, critique_2 by m1.
    assert call_models == ["m2", "m3", "m1"]


# ----------------------------------------------------------------
# Phase 1 condition call-count contracts
# ----------------------------------------------------------------


def test_phase1_condition_call_counts() -> None:
    """Pins the call-count contract for each condition at the
    configurations documented in system-architecture.md."""
    cases = [
        ("A",             condition_a("m1"),                             1),
        ("B(N=3)",        condition_b("m1", 3),                          4),
        ("C",             condition_c(["m1", "m2", "m3"], "m1"),         4),
        ("D@3,1",         reconcile(["m1", "m2", "m3"], n_rounds=1),    12),
        ("D'@3,1",        condition_d_prime("m1", 3, n_rounds=1),       12),
        ("E@3",           condition_e(["m1", "m2", "m3"], "m1"),         7),
        ("E_WRTF@3",      condition_e_writers_revise_then_fuse(
                              ["m1", "m2", "m3"], "m1"),                10),
    ]
    for name, expr, expected in cases:
        client = FakeClient()
        run(expr, client, "q")
        assert len(client.calls) == expected, (
            f"{name}: expected {expected} calls, got {len(client.calls)}"
        )


# ----------------------------------------------------------------
# run() returns telemetry
# ----------------------------------------------------------------


def test_run_returns_telemetry_visible_to_caller() -> None:
    """The `run()` convenience function returns a `(result,
    telemetry)` tuple. Round-3 review (Gemini) flagged the
    previous single-value return as a structural blind spot:
    the runner had no way to access parse-failure or tie counts.
    """
    client = FakeClient()
    result, telemetry = run(condition_a("m1"), client, "q")
    # The result is the final RAnswer; telemetry is a fresh
    # InterpreterTelemetry with all counters at zero (Condition A
    # has no parsing or aggregation).
    assert result.text.startswith("[gen|m1|")
    assert telemetry.score_parse_failures == 0
    assert telemetry.pick_parse_failures == 0
    assert telemetry.weighted_vote_ties == 0


def test_run_telemetry_records_parse_failures() -> None:
    """A response that the score parser can't extract a number
    from triggers the silent-fallback path; telemetry records it."""
    def garbage_responder(model: str, system: str, user: str) -> str:
        if "Rate your confidence" in user:
            return "I think this is pretty good"  # no parseable number
        return f"draft-from-{model}"

    client = FakeClient(responder=garbage_responder)
    q = query()
    drafts = par_gen(["m1", "m2", "m3"], q)
    protocol = bind(
        drafts,
        lambda ds: weighted_vote(ds, par_score(["m1", "m2", "m3"], ds)),
    )
    _, telemetry = run(Finalize(draft=protocol), client, "q", seed=0)
    # Three score calls all failed to parse.
    assert telemetry.score_parse_failures == 3


# ----------------------------------------------------------------
# Tie-break and parse-failure policy dispatch (AST-level)
# ----------------------------------------------------------------


def _all_tied_responder(model: str, system: str, user: str) -> str:
    if "Rate your confidence" in user:
        return "0.5"
    return f"draft-from-{model}"


def test_weighted_vote_tie_break_first() -> None:
    """TieBreakPolicy.FIRST picks the lowest-index tied candidate
    deterministically. Useful when reproducibility matters more
    than avoiding position bias."""
    client = FakeClient(responder=_all_tied_responder)
    q = query()
    drafts = par_gen(["m1", "m2", "m3"], q)
    protocol = bind(
        drafts,
        lambda ds: weighted_vote(
            ds, par_score(["m1", "m2", "m3"], ds),
            tie_break=TieBreakPolicy.FIRST,
        ),
    )
    # With FIRST, position 0 wins every time regardless of seed.
    for seed in range(5):
        client.calls.clear()
        result, _ = run(Finalize(draft=protocol), client, "q", seed=seed)
        assert result.text == "draft-from-m1"


def test_weighted_vote_tie_break_last() -> None:
    """TieBreakPolicy.LAST picks the highest-index tied candidate
    deterministically."""
    client = FakeClient(responder=_all_tied_responder)
    q = query()
    drafts = par_gen(["m1", "m2", "m3"], q)
    protocol = bind(
        drafts,
        lambda ds: weighted_vote(
            ds, par_score(["m1", "m2", "m3"], ds),
            tie_break=TieBreakPolicy.LAST,
        ),
    )
    for seed in range(5):
        client.calls.clear()
        result, _ = run(Finalize(draft=protocol), client, "q", seed=seed)
        assert result.text == "draft-from-m3"


def test_weighted_vote_tie_break_default_is_random() -> None:
    """The default WeightedVote (no tie_break kwarg) uses RANDOM —
    same as passing TieBreakPolicy.RANDOM explicitly."""
    default_q = query()
    default_drafts = par_gen(["m1", "m2", "m3"], default_q)
    default_protocol = Finalize(draft=bind(
        default_drafts,
        lambda ds: weighted_vote(
            ds, par_score(["m1", "m2", "m3"], ds),
        ),
    ))

    random_q = query()
    random_drafts = par_gen(["m1", "m2", "m3"], random_q)
    random_protocol = Finalize(draft=bind(
        random_drafts,
        lambda ds: weighted_vote(
            ds, par_score(["m1", "m2", "m3"], ds),
            tie_break=TieBreakPolicy.RANDOM,
        ),
    ))

    # Under the same seed, default and RANDOM must land on the
    # same winner — confirms the default is RANDOM.
    default_client = FakeClient(responder=_all_tied_responder)
    default_result, _ = run(default_protocol, default_client, "q", seed=42)

    random_client = FakeClient(responder=_all_tied_responder)
    random_result, _ = run(random_protocol, random_client, "q", seed=42)

    assert default_result.text == random_result.text


def _garbage_pick_responder(model: str, system: str, user: str) -> str:
    if "pick the single best one" in user.lower():
        return "I can't decide"  # no parseable integer
    return f"draft-from-{model}"


def test_pick_one_on_parse_failure_raise() -> None:
    """ParseFailurePolicy.RAISE surfaces a ParseFailure when the
    judge response can't be parsed. Useful for dry runs where
    the goal is to catch parse failures rather than absorb them."""
    client = FakeClient(responder=_garbage_pick_responder)
    q = query()
    drafts = par_gen(["m1", "m2", "m3"], q)
    protocol = Finalize(draft=pick_one(
        "m1", drafts, on_parse_failure=ParseFailurePolicy.RAISE,
    ))
    with pytest.raises(ParseFailure, match="parse failure"):
        run(protocol, client, "q")


def test_pick_one_default_on_parse_failure_is_random() -> None:
    """The default PickOne (no on_parse_failure kwarg) uses
    RANDOM and falls back via the interpreter's seeded RNG."""
    client = FakeClient(responder=_garbage_pick_responder)
    q = query()
    drafts = par_gen(["m1", "m2", "m3"], q)
    # No kwarg: default is RANDOM. Does NOT raise.
    result, telemetry = run(
        Finalize(draft=pick_one("m1", drafts)), client, "q", seed=0,
    )
    assert result.text.startswith("draft-from-")
    assert telemetry.pick_parse_failures == 1
