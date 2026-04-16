"""Tree-walking interpreter for the protocol IR.

Walks an Expr and produces the runtime value of type determined by
the expression's result_type. Uses structural pattern matching on
the AST node classes.

Prompt templates are supplied via PromptTemplates from the
experiment-spec layer. If omitted, DEFAULT_PROMPTS (structured-
critique format) is used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.experiment.prompts import DEFAULT_PROMPTS
from src.experiment.spec import PromptTemplates
from src.ir.ast import (
    Expr,
    Finalize,
    Fuse,
    FuseWithCritiques,
    Gen,
    Let,
    ParGen,
    ParPeerReview,
    ParScore,
    PeerReviseRound,
    PeerRounds,
    PickOne,
    QueryVar,
    Review,
    Revise,
    SelfReviseRound,
    SelfRounds,
    Var,
    WeightedVote,
)
from src.ir.types import ContextMode, Draft, Final, Visibility

from .client import ModelClient
from .runtime import RAnswer, RCritique, RQuery, RScore


@dataclass(frozen=True)
class Env:
    """Immutable binding environment for Let/Var."""
    bindings: dict[str, Any] = field(default_factory=dict)

    def extend(self, name: str, value: Any) -> "Env":
        new = dict(self.bindings)
        new[name] = value
        return Env(bindings=new)

    def lookup(self, name: str) -> Any:
        return self.bindings[name]


class Interpreter:
    def __init__(
        self,
        client: ModelClient,
        query_text: str,
        prompts: PromptTemplates | None = None,
    ) -> None:
        self.client = client
        self.query_text = query_text
        self.prompts = prompts or DEFAULT_PROMPTS
        # Identity-based memoization: a shared sub-expression must
        # evaluate to the same runtime value every time it's referenced
        # in a single run. In CCR, for example, `d = gen(...)` is used
        # in both the review and the revise step — they must see the
        # same draft, not two independent model calls.
        self._cache: dict[int, Any] = {}

    def _system_for(self, context: ContextMode) -> str:
        if context is ContextMode.FRESH:
            return self.prompts.gen_system
        return self.prompts.accumulated_system

    def _review_prompt(
        self,
        target: RAnswer,
        peers: list[RAnswer],
        visibility: Visibility,
    ) -> str:
        """Build the self-review prompt for a SelfReviseRound step.

        Used when the reviewer IS the writer (target.text is the
        reviewer's own draft).
        """
        peers_text = "\n---\n".join(p.text for p in peers) if peers else ""
        match visibility:
            case Visibility.ARTIFACT_ONLY:
                return self.prompts.review_artifact.format(draft=target.text)
            case Visibility.WITH_PRODUCTION:
                return self.prompts.review_with_production.format(
                    query=target.production_query, draft=target.text
                )
            case Visibility.PEERS_GROUPED:
                return self.prompts.review_peers.format(
                    draft=target.text, peers=peers_text
                )
            case Visibility.ALL:
                return self.prompts.review_all.format(
                    query=target.production_query,
                    draft=target.text,
                    peers=peers_text,
                )
        raise ValueError(f"Unknown visibility: {visibility}")

    def _peer_review_prompt(
        self,
        target: RAnswer,
        other_drafts: list[RAnswer],
        visibility: Visibility,
    ) -> str:
        """Build the peer-review prompt for a PeerReviseRound step.

        Used when the reviewer is NOT the writer. `other_drafts`
        contains every draft except the target; under blinding,
        the reviewer's own draft (which appears in this list for
        N >= 2) is indistinguishable from the others.
        """
        peers_text = (
            "\n---\n".join(p.text for p in other_drafts) if other_drafts else ""
        )
        match visibility:
            case Visibility.ARTIFACT_ONLY:
                return self.prompts.peer_review_artifact.format(draft=target.text)
            case Visibility.WITH_PRODUCTION:
                return self.prompts.peer_review_with_production.format(
                    query=target.production_query, draft=target.text
                )
            case Visibility.PEERS_GROUPED:
                return self.prompts.peer_review_peers.format(
                    draft=target.text, peers=peers_text
                )
            case Visibility.ALL:
                return self.prompts.peer_review_all.format(
                    query=target.production_query,
                    draft=target.text,
                    peers=peers_text,
                )
        raise ValueError(f"Unknown visibility: {visibility}")

    def _self_review_and_revise_one(
        self,
        model: str,
        own: RAnswer,
        peers: list[RAnswer],
        context: ContextMode,
        visibility: Visibility,
    ) -> RAnswer:
        """Self-review semantics: `model` is both reviewer and reviser.

        The reviewer (= writer) sees its own draft and produces a
        critique, then revises its own draft from that critique.
        Peer drafts may be visible per the visibility annotation
        but are context for self-reflection, not the artifact under
        review. The peer-review sibling will live in
        `_peer_review_and_revise_one` once added.
        """
        system = self._system_for(context)
        crit_text = self.client.complete(
            model, system, self._review_prompt(own, peers, visibility)
        )
        revised_text = self.client.complete(
            model,
            system,
            self.prompts.revise_user.format(
                critique=crit_text, draft=own.text
            ),
        )
        return RAnswer(
            text=revised_text, stage=Draft, production_query=own.production_query
        )

    def _one_self_round(
        self,
        models: list[str],
        drafts: list[RAnswer],
        context: ContextMode,
        visibility: Visibility,
    ) -> list[RAnswer]:
        """One round of self-review-and-revise across `models`.

        For each draft d_i, model m_i = models[i] reviews and
        revises its OWN draft (peers visible per the visibility
        annotation). This is the SelfReviseRound semantics. The
        peer-review version is in `_one_peer_round`.
        """
        out: list[RAnswer] = []
        for i, m in enumerate(models):
            peers = [d for j, d in enumerate(drafts) if j != i]
            out.append(
                self._self_review_and_revise_one(
                    m, drafts[i], peers, context, visibility
                )
            )
        return out

    def _peer_review_and_revise_one(
        self,
        reviewer: str,
        writer: str,
        target: RAnswer,
        other_drafts: list[RAnswer],
        context: ContextMode,
        visibility: Visibility,
    ) -> RAnswer:
        """Peer-review semantics: `reviewer` ≠ `writer`.

        The peer reviewer produces a critique of `target` (the
        writer's draft); the original writer then revises its
        own draft from the peer critique. Identity is blinded in
        the prompt — the reviewer is told the draft comes from
        "a peer AI," not from a specific vendor.
        """
        system = self._system_for(context)
        crit_text = self.client.complete(
            reviewer,
            system,
            self._peer_review_prompt(target, other_drafts, visibility),
        )
        revised_text = self.client.complete(
            writer,
            system,
            self.prompts.revise_user.format(
                critique=crit_text, draft=target.text
            ),
        )
        return RAnswer(
            text=revised_text,
            stage=Draft,
            production_query=target.production_query,
        )

    def _one_peer_round(
        self,
        models: list[str],
        drafts: list[RAnswer],
        context: ContextMode,
        visibility: Visibility,
    ) -> list[RAnswer]:
        """One round of peer-review-and-revise across `models`.

        Reviewer assignment: cyclic shift by one. For each draft
        d_i (writer m_i = models[i]), the reviewer is
        models[(i+1) % N]. This gives 1 peer per draft (lower
        bound of the design's "1–2 peers" wording). Requires N >= 2.
        """
        n = len(models)
        if n < 2:
            raise ValueError(
                "PeerReviseRound requires at least 2 models; "
                f"got {n}. Use SelfReviseRound for single-model pools."
            )
        out: list[RAnswer] = []
        for i in range(n):
            writer = models[i]
            reviewer = models[(i + 1) % n]
            target = drafts[i]
            other_drafts = [d for j, d in enumerate(drafts) if j != i]
            out.append(
                self._peer_review_and_revise_one(
                    reviewer, writer, target, other_drafts, context, visibility
                )
            )
        return out

    def _par_peer_review(
        self,
        models: list[str],
        drafts: list[RAnswer],
        context: ContextMode,
        visibility: Visibility,
    ) -> list[RCritique]:
        """Peer review across drafts producing critiques only.

        Reviewer assignment: cyclic shift by one (same as
        PeerReviseRound). For each draft d_i, the reviewer
        models[(i+1) % N] produces a critique. Returns critiques
        aligned with the input drafts. Requires N >= 2.
        """
        n = len(models)
        if n < 2:
            raise ValueError(
                "ParPeerReview requires at least 2 models; "
                f"got {n}. Use Review nodes directly for single-model setups."
            )
        system = self._system_for(context)
        out: list[RCritique] = []
        for i in range(n):
            reviewer = models[(i + 1) % n]
            target = drafts[i]
            other_drafts = [d for j, d in enumerate(drafts) if j != i]
            crit_text = self.client.complete(
                reviewer,
                system,
                self._peer_review_prompt(target, other_drafts, visibility),
            )
            out.append(RCritique(text=crit_text))
        return out

    def evaluate(self, expr: Expr[Any], env: Env) -> Any:
        key = id(expr)
        if key in self._cache:
            return self._cache[key]
        result = self._evaluate_uncached(expr, env)
        self._cache[key] = result
        return result

    def _evaluate_uncached(self, expr: Expr[Any], env: Env) -> Any:
        match expr:
            case QueryVar():
                return RQuery(text=self.query_text)

            case Gen(model=model, query=q):
                rq = self.evaluate(q, env)
                text = self.client.complete(
                    model,
                    self.prompts.gen_system,
                    self.prompts.gen_user.format(query=rq.text),
                )
                return RAnswer(
                    text=text, stage=Draft, production_query=rq.text
                )

            case Review(
                model=model, target=target, context=context, visibility=vis
            ):
                ans = self.evaluate(target, env)
                system = self._system_for(context)
                prompt = self._review_prompt(ans, peers=[], visibility=vis)
                text = self.client.complete(model, system, prompt)
                return RCritique(text=text)

            case Revise(model=model, draft=d, critique=c):
                ans = self.evaluate(d, env)
                crit = self.evaluate(c, env)
                text = self.client.complete(
                    model,
                    self.prompts.gen_system,
                    self.prompts.revise_user.format(
                        critique=crit.text, draft=ans.text
                    ),
                )
                return RAnswer(
                    text=text, stage=Draft, production_query=ans.production_query
                )

            case Finalize(draft=d):
                ans = self.evaluate(d, env)
                return RAnswer(
                    text=ans.text,
                    stage=Final,
                    production_query=ans.production_query,
                )

            case Fuse(model=model, drafts=ds, query=q):
                rq = self.evaluate(q, env)
                answers = self.evaluate(ds, env)
                drafts_text = "\n---\n".join(
                    f"Draft {i+1}:\n{a.text}" for i, a in enumerate(answers)
                )
                text = self.client.complete(
                    model,
                    self.prompts.gen_system,
                    self.prompts.fuse_user.format(
                        query=rq.text, drafts=drafts_text
                    ),
                )
                return RAnswer(
                    text=text, stage=Draft, production_query=rq.text
                )

            case FuseWithCritiques(
                model=model, drafts=ds, critiques=cs, query=q
            ):
                rq = self.evaluate(q, env)
                answers = self.evaluate(ds, env)
                crits = self.evaluate(cs, env)
                drafts_with_critiques = "\n---\n".join(
                    f"Draft {i+1}:\n{a.text}\n\nCritique of Draft {i+1}:\n{c.text}"
                    for i, (a, c) in enumerate(zip(answers, crits))
                )
                text = self.client.complete(
                    model,
                    self.prompts.gen_system,
                    self.prompts.fuse_with_critiques_user.format(
                        query=rq.text,
                        drafts_with_critiques=drafts_with_critiques,
                    ),
                )
                return RAnswer(
                    text=text, stage=Draft, production_query=rq.text
                )

            case ParGen(models=models, query=q):
                rq = self.evaluate(q, env)
                results: list[RAnswer] = []
                for m in models:
                    text = self.client.complete(
                        m,
                        self.prompts.gen_system,
                        self.prompts.gen_user.format(query=rq.text),
                    )
                    results.append(
                        RAnswer(text=text, stage=Draft, production_query=rq.text)
                    )
                return results

            case SelfReviseRound(
                models=models, drafts=ds, context=context, visibility=vis
            ):
                current = self.evaluate(ds, env)
                return self._one_self_round(models, current, context, vis)

            case SelfRounds(
                n=n, models=models, drafts=ds, context=context, visibility=vis
            ):
                current = self.evaluate(ds, env)
                for _ in range(n):
                    current = self._one_self_round(models, current, context, vis)
                return current

            case PeerReviseRound(
                models=models, drafts=ds, context=context, visibility=vis
            ):
                current = self.evaluate(ds, env)
                return self._one_peer_round(models, current, context, vis)

            case PeerRounds(
                n=n, models=models, drafts=ds, context=context, visibility=vis
            ):
                current = self.evaluate(ds, env)
                for _ in range(n):
                    current = self._one_peer_round(models, current, context, vis)
                return current

            case ParPeerReview(
                models=models, drafts=ds, context=context, visibility=vis
            ):
                drafts_resolved = self.evaluate(ds, env)
                return self._par_peer_review(
                    models, drafts_resolved, context, vis
                )

            case ParScore(models=models, drafts=ds):
                answers = self.evaluate(ds, env)
                scores: list[RScore] = []
                for m, ans in zip(models, answers):
                    text = self.client.complete(
                        m,
                        self.prompts.gen_system,
                        self.prompts.score_user.format(draft=ans.text),
                    )
                    scores.append(RScore(value=_parse_score(text)))
                return scores

            case WeightedVote(drafts=ds, scores=ss):
                answers = self.evaluate(ds, env)
                scores = self.evaluate(ss, env)
                best_idx = max(
                    range(len(answers)), key=lambda i: scores[i].value
                )
                return answers[best_idx]

            case PickOne(judge=judge, drafts=ds):
                answers = self.evaluate(ds, env)
                candidates_text = "\n---\n".join(
                    f"Candidate {i+1}:\n{a.text}"
                    for i, a in enumerate(answers)
                )
                text = self.client.complete(
                    judge,
                    self.prompts.gen_system,
                    self.prompts.pick_one_user.format(
                        candidates=candidates_text
                    ),
                )
                idx = _parse_pick(text, n=len(answers))
                return answers[idx]

            case Var(name=name):
                return env.lookup(name)

            case Let(var_name=var_name, value=value, body=body):
                val = self.evaluate(value, env)
                return self.evaluate(body, env.extend(var_name, val))

        raise NotImplementedError(f"Unhandled node: {type(expr).__name__}")


def _parse_score(text: str) -> float:
    for tok in text.replace(",", " ").split():
        try:
            v = float(tok)
        except ValueError:
            continue
        return max(0.0, min(1.0, v))
    return 0.5


def _parse_pick(text: str, n: int) -> int:
    """Parse a 1-indexed candidate selection from a judge's response.

    Returns a 0-indexed candidate position in [0, n). Falls back
    to 0 (first candidate) if no valid integer in [1, n] is
    found, mirroring the position-bias behavior of WeightedVote
    on ties; the silent fallback is a known issue tracked
    alongside _parse_score in the broader implementation-bugs
    item (see status.md).
    """
    for tok in text.replace(",", " ").replace(".", " ").split():
        try:
            v = int(tok)
        except ValueError:
            continue
        if 1 <= v <= n:
            return v - 1
    return 0


def run(
    expr: Expr[Any],
    client: ModelClient,
    query_text: str,
    prompts: PromptTemplates | None = None,
) -> Any:
    """Evaluate an expression against a client and a query string.

    If prompts is None, DEFAULT_PROMPTS (structured-critique format
    from the experiment-spec layer) is used.
    """
    return Interpreter(client, query_text, prompts).evaluate(expr, Env())
