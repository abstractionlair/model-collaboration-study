# Decision Log

Significant choices and their rationale. See WORKFLOW.md for format guidance.

---

## 2026-04-08 Use API models for the study, not self-hosted

**Decision:** Run all experiments via commercial APIs (frontier lab small
models as subjects, frontier large models as judges) rather than
self-hosting open-weight models.

**Alternatives considered:** Self-hosting open models on rented GPUs
(explored in detail in the initial GPT conversation).

**Rationale:** The research question is about multi-model protocol design,
not about specific models. APIs remove confounds from quantization,
serving configuration, and deployment instability. They also give genuine
training-lineage diversity (Claude, GPT, Gemini) that open models often
lack. Self-hosted open models are a valid follow-up to test whether
results transfer.

**Status:** Active

---

## 2026-04-08 Small models as subjects, frontier models as judges

**Decision:** Use small/mid-tier models (e.g. Haiku, GPT mini, Gemini
Flash class) as the models under study, with frontier models as automated
judges.

**Alternatives considered:** Testing frontier models against each other
(stronger contribution but harder to judge automatically); testing only
open models (cheaper but less lineage diversity).

**Rationale:** Calibrating tasks so small models succeed ~40-60% one-shot
means those tasks should be easy for frontier judges, avoiding the main
failure mode of LLM-as-judge (judging at or above the judge's own
capability). This enables a mostly-automated evaluation pipeline. The
capability gap is a feature, not a limitation — it simulates the
weak-overseer-strong-agent dynamic the oversight literature cares about.

**Status:** Active
