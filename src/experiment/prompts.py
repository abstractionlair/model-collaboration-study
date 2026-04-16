"""Default prompt templates for Phase 1.

These replace the placeholder strings in src/executor/interpreter.py.
The structured-critique format is the Phase 1 default; the
critique-format axis (free-form vs structured flags vs flag-only)
is a follow-on ablation on the winning protocol family.

Template variables use str.format() syntax:
  {query}    — the task text
  {draft}    — an answer draft
  {critique} — a review critique
  {peers}    — peer drafts, joined with separators
"""

from __future__ import annotations

from .spec import PromptTemplates

# System prompts
_GEN_SYSTEM = "You are an assistant answering a task in isolation."
_ACCUMULATED_SYSTEM = "You are an assistant continuing a conversation."

# Generation
_GEN_USER = "Task:\n{query}\n\nProvide your answer."

# Review (structured critique — Phase 1 default)
_REVIEW_ARTIFACT = (
    "Review the following draft answer. For each of these dimensions, "
    "note any issues you find:\n"
    "- Correctness\n"
    "- Completeness\n"
    "- Unnecessary assumptions\n"
    "- Tool-use correctness\n"
    "- Code safety / likely test failures\n"
    "- Confidence (high / medium / low)\n"
    "\nDraft:\n{draft}"
)

_REVIEW_WITH_PRODUCTION = (
    "The original task was:\n{query}\n\n"
    "Review the following draft answer. For each of these dimensions, "
    "note any issues you find:\n"
    "- Correctness\n"
    "- Completeness\n"
    "- Unnecessary assumptions\n"
    "- Tool-use correctness\n"
    "- Code safety / likely test failures\n"
    "- Confidence (high / medium / low)\n"
    "\nDraft:\n{draft}"
)

_REVIEW_PEERS = (
    "Review your draft answer in light of the peer drafts below. "
    "For each of these dimensions, note any issues you find:\n"
    "- Correctness\n"
    "- Completeness\n"
    "- Unnecessary assumptions\n"
    "- Tool-use correctness\n"
    "- Code safety / likely test failures\n"
    "- Confidence (high / medium / low)\n"
    "\nYour draft:\n{draft}\n\nPeer drafts:\n{peers}"
)

_REVIEW_ALL = (
    "The original task was:\n{query}\n\n"
    "Peer drafts:\n{peers}\n\n"
    "Review your draft answer. For each of these dimensions, "
    "note any issues you find:\n"
    "- Correctness\n"
    "- Completeness\n"
    "- Unnecessary assumptions\n"
    "- Tool-use correctness\n"
    "- Code safety / likely test failures\n"
    "- Confidence (high / medium / low)\n"
    "\nYour draft:\n{draft}"
)

# Peer review (different model critiques the target draft; identity blinded)
_PEER_REVIEW_ARTIFACT = (
    "Review the following draft answer, produced by a peer AI. "
    "For each of these dimensions, note any issues you find:\n"
    "- Correctness\n"
    "- Completeness\n"
    "- Unnecessary assumptions\n"
    "- Tool-use correctness\n"
    "- Code safety / likely test failures\n"
    "- Confidence (high / medium / low)\n"
    "\nDraft under review:\n{draft}"
)

_PEER_REVIEW_WITH_PRODUCTION = (
    "The original task was:\n{query}\n\n"
    "Review the following draft answer, produced by a peer AI. "
    "For each of these dimensions, note any issues you find:\n"
    "- Correctness\n"
    "- Completeness\n"
    "- Unnecessary assumptions\n"
    "- Tool-use correctness\n"
    "- Code safety / likely test failures\n"
    "- Confidence (high / medium / low)\n"
    "\nDraft under review:\n{draft}"
)

_PEER_REVIEW_PEERS = (
    "Review the following draft answer, produced by a peer AI, "
    "considering the other peer drafts below as context. "
    "For each of these dimensions, note any issues you find:\n"
    "- Correctness\n"
    "- Completeness\n"
    "- Unnecessary assumptions\n"
    "- Tool-use correctness\n"
    "- Code safety / likely test failures\n"
    "- Confidence (high / medium / low)\n"
    "\nDraft under review:\n{draft}\n\nOther peer drafts:\n{peers}"
)

_PEER_REVIEW_ALL = (
    "The original task was:\n{query}\n\n"
    "Other peer drafts:\n{peers}\n\n"
    "Review the following draft answer, produced by a peer AI. "
    "For each of these dimensions, note any issues you find:\n"
    "- Correctness\n"
    "- Completeness\n"
    "- Unnecessary assumptions\n"
    "- Tool-use correctness\n"
    "- Code safety / likely test failures\n"
    "- Confidence (high / medium / low)\n"
    "\nDraft under review:\n{draft}"
)

# Revision
_REVISE_USER = (
    "Given this critique:\n{critique}\n\n"
    "Revise the draft below and return only the revised answer.\n\n"
    "Draft:\n{draft}"
)

# Fusion (meta-reviewer reads peer drafts and writes fresh)
_FUSE_USER = (
    "Task:\n{query}\n\n"
    "The following peer drafts were produced by different models "
    "working on this task:\n\n{drafts}\n\n"
    "Write your own response to the task, informed by but not "
    "constrained to the peer drafts above."
)

# Fusion with critiques (meta-reviewer reads drafts paired with critiques)
_FUSE_WITH_CRITIQUES_USER = (
    "Task:\n{query}\n\n"
    "The following peer drafts were produced by different AIs, "
    "each accompanied by a critique from another peer:\n\n"
    "{drafts_with_critiques}\n\n"
    "Synthesize a final response to the task. You may draw on "
    "the drafts and the critiques, but write your own response "
    "— do not just pick one or paraphrase a single draft."
)

# Confidence scoring
_SCORE_USER = (
    "Rate your confidence (0.0-1.0) that the following answer is "
    "correct. Return only the number.\n\nAnswer:\n{draft}"
)

# Comparative selection — judge sees all candidates and picks one
_PICK_ONE_USER = (
    "The following are candidate answers to a task, produced by "
    "different peer AIs. Read each carefully, compare them, then "
    "pick the single best one. Respond with ONLY the candidate "
    "number (1-indexed), nothing else.\n\n{candidates}"
)


DEFAULT_PROMPTS = PromptTemplates(
    gen_system=_GEN_SYSTEM,
    accumulated_system=_ACCUMULATED_SYSTEM,
    gen_user=_GEN_USER,
    review_artifact=_REVIEW_ARTIFACT,
    review_with_production=_REVIEW_WITH_PRODUCTION,
    review_peers=_REVIEW_PEERS,
    review_all=_REVIEW_ALL,
    peer_review_artifact=_PEER_REVIEW_ARTIFACT,
    peer_review_with_production=_PEER_REVIEW_WITH_PRODUCTION,
    peer_review_peers=_PEER_REVIEW_PEERS,
    peer_review_all=_PEER_REVIEW_ALL,
    revise_user=_REVISE_USER,
    fuse_user=_FUSE_USER,
    fuse_with_critiques_user=_FUSE_WITH_CRITIQUES_USER,
    score_user=_SCORE_USER,
    pick_one_user=_PICK_ONE_USER,
)
