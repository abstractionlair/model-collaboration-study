"""Protocol IR — pretty printer.

One interpreter for the typed AST: render an expression as a
human-readable description. Other interpreters (executor, cost
estimator, linter) would follow the same pattern — walk the AST
and produce their own output.
"""

from __future__ import annotations

from typing import Any

from .ast import (
    Expr,
    Finalize,
    Gen,
    Let,
    ParGen,
    ParScore,
    QueryVar,
    Review,
    ReviseRound,
    Revise,
    Rounds,
    Var,
    WeightedVote,
)


def describe(expr: Expr[Any], indent: int = 0) -> str:
    """Render an Expr as indented prose-like text."""
    pad = "  " * indent

    match expr:
        case QueryVar(name=name):
            return f"{pad}{name} : Query"

        case Gen(model=model, query=query):
            q = describe(query, indent + 1)
            return f"{pad}Gen({model}) : Query -> Answer[Draft]\n{q}"

        case Review(model=model, target=target, context=ctx, visibility=vis):
            t = describe(target, indent + 1)
            return (
                f"{pad}Review({model}, ctx={ctx.value}, vis={vis.value}) "
                f": Answer[Draft] -> Critique[Answer[Draft]]\n{t}"
            )

        case Revise(model=model, draft=draft, critique=critique):
            d = describe(draft, indent + 1)
            c = describe(critique, indent + 1)
            return (
                f"{pad}Revise({model}) : Answer[Draft] x Critique -> Answer[Draft]\n"
                f"{d}\n{c}"
            )

        case Finalize(draft=draft):
            d = describe(draft, indent + 1)
            return f"{pad}Finalize : Answer[Draft] -> Answer[Final]\n{d}"

        case ParGen(models=models, query=query):
            q = describe(query, indent + 1)
            return (
                f"{pad}ParGen({models}) : Query -> [Answer[Draft]]\n{q}"
            )

        case ReviseRound(models=models, drafts=drafts, context=ctx, visibility=vis):
            d = describe(drafts, indent + 1)
            return (
                f"{pad}ReviseRound({models}, ctx={ctx.value}, vis={vis.value}) "
                f": [Answer[Draft]] -> [Answer[Draft]]\n{d}"
            )

        case Rounds(n=n, models=models, drafts=drafts, context=ctx, visibility=vis):
            d = describe(drafts, indent + 1)
            return (
                f"{pad}Rounds(n={n}, {models}, ctx={ctx.value}, vis={vis.value}) "
                f": [Answer[Draft]] -> [Answer[Draft]]\n{d}"
            )

        case ParScore(models=models, drafts=drafts):
            d = describe(drafts, indent + 1)
            return (
                f"{pad}ParScore({models}) "
                f": [Answer[Draft]] -> [Score[Answer[Draft]]]\n{d}"
            )

        case WeightedVote(drafts=drafts, scores=scores):
            d = describe(drafts, indent + 1)
            s = describe(scores, indent + 1)
            return (
                f"{pad}WeightedVote : [Answer[Draft]] x [Score] -> Answer[Draft]\n"
                f"{d}\n{s}"
            )

        case Var(name=name):
            return f"{pad}{name}"

        case Let(var_name=var_name, value=value, body=body):
            v = describe(value, indent + 1)
            b = describe(body, indent + 1)
            return f"{pad}let {var_name} =\n{v}\n{pad}in\n{b}"

        case _:
            return f"{pad}<unknown: {expr!r}>"
