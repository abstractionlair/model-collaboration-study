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
    Gen,
    Let,
    ParGen,
    ParScore,
    QueryVar,
    Review,
    Revise,
    ReviseRound,
    Rounds,
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

    def _review_and_revise_one(
        self,
        model: str,
        own: RAnswer,
        peers: list[RAnswer],
        context: ContextMode,
        visibility: Visibility,
    ) -> RAnswer:
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

    def _one_round(
        self,
        models: list[str],
        drafts: list[RAnswer],
        context: ContextMode,
        visibility: Visibility,
    ) -> list[RAnswer]:
        out: list[RAnswer] = []
        for i, m in enumerate(models):
            peers = [d for j, d in enumerate(drafts) if j != i]
            out.append(
                self._review_and_revise_one(
                    m, drafts[i], peers, context, visibility
                )
            )
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

            case ReviseRound(
                models=models, drafts=ds, context=context, visibility=vis
            ):
                current = self.evaluate(ds, env)
                return self._one_round(models, current, context, vis)

            case Rounds(
                n=n, models=models, drafts=ds, context=context, visibility=vis
            ):
                current = self.evaluate(ds, env)
                for _ in range(n):
                    current = self._one_round(models, current, context, vis)
                return current

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
