from __future__ import annotations

import re
from statistics import median
from typing import Any


DRIFT_TAXONOMY = {
    "instruction_to_execution": "The rewrite performs the style or says target content instead of giving a TTS control instruction.",
    "role_assumption": "The rewrite speaks as the requested role/persona instead of asking the TTS system to imitate/control it.",
    "entity_label": "The rewrite changes or drops required entities, labels, accents, emotions, or speaker roles.",
    "none": "No supervision-corrupting drift is detected.",
}


SCORING_SYSTEM_PROMPT = """You are a strict TTS instruction-supervision verifier.
You receive a source control instruction and a rewritten instruction.
Score whether the rewrite preserves the source instruction's control meaning.

Reject rewrites that:
1. perform the requested style/emotion/accent instead of instructing it;
2. assume the requested role/persona instead of requesting that role/persona;
3. change or drop required entities, labels, accent names, emotions, or speaker roles.

Return only one integer from 0 to 10.
10 means perfectly faithful. 0 means the source control meaning is lost.
"""


CLASSIFY_SYSTEM_PROMPT = """You are a strict TTS instruction-supervision verifier.
Classify the drift type between a source control instruction and a rewrite.
Return exactly one label:
instruction_to_execution
role_assumption
entity_label
none
"""


def build_scoring_messages(category: str, sentence: str, required_terms: list[str] | None = None) -> list[dict[str, str]]:
    required = "、".join(required_terms or []) or "None"
    user = f"""Source control instruction:
{category}

Rewritten instruction:
{sentence}

Required terms:
{required}

Return only one integer score."""
    return [
        {"role": "system", "content": SCORING_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def build_classification_messages(category: str, sentence: str, required_terms: list[str] | None = None) -> list[dict[str, str]]:
    required = "、".join(required_terms or []) or "None"
    user = f"""Source control instruction:
{category}

Rewritten instruction:
{sentence}

Required terms:
{required}

Labels:
{DRIFT_TAXONOMY}"""
    return [
        {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def parse_score(text: str) -> int:
    match = re.search(r"\b(10|[0-9])\b", text.strip())
    if not match:
        raise ValueError(f"Could not parse integer score from: {text!r}")
    return int(match.group(1))


def parse_drift_type(text: str) -> str:
    text = text.strip().lower()
    for label in DRIFT_TAXONOMY:
        if label in text:
            return label
    return "none"


def _target_after_prefix(category: str, prefixes: list[str]) -> str:
    for prefix in prefixes:
        if category.startswith(prefix):
            return category[len(prefix):].strip(" ，。,.")
    return ""


def heuristic_score(category: str, sentence: str, required_terms: list[str] | None = None) -> tuple[int, str]:
    """Lightweight offline drift heuristic for examples.

    This is not a replacement for the paper's LLM verifier; it keeps the
    repository runnable without API keys and catches common drift patterns.
    """

    required_terms = required_terms or []
    score = 8
    drift_type = "none"
    control_markers = ["用", "说", "讲", "模仿", "语气", "声音", "风格", "腔", "表达", "请"]

    if required_terms:
        dropped = [term for term in required_terms if term and term not in sentence]
        if dropped:
            score -= 4
            drift_type = "entity_label"

    mimic_target = _target_after_prefix(category, ["模仿"])
    if mimic_target and mimic_target not in sentence:
        score -= 4
        drift_type = "role_assumption"
    elif mimic_target and "模仿" not in sentence and "像" not in sentence:
        score -= 2
        drift_type = "role_assumption"

    dialect_target = ""
    if category.startswith("用") and ("说" in category or "讲" in category):
        dialect_target = category[1:].replace("说", "").replace("讲", "").strip()
    if dialect_target and dialect_target not in sentence:
        aliases = {"台湾话": ["台语", "台湾腔"], "东北话": ["东北腔"], "北京话": ["京腔"]}
        if not any(alias in sentence for alias in aliases.get(dialect_target, [])):
            score -= 3
            drift_type = "entity_label"

    if "语气" in category or "情绪" in category:
        emotion_terms = ["开心", "难过", "生气", "惊讶", "安慰", "抱歉"]
        expected = [term for term in emotion_terms if term in category]
        if expected and not any(term in sentence for term in expected):
            score -= 3
            drift_type = "instruction_to_execution"

    if not any(marker in sentence for marker in control_markers):
        score -= 2
        if drift_type == "none":
            drift_type = "instruction_to_execution"

    if len(sentence) <= 4 and category not in sentence:
        score -= 2
        if drift_type == "none":
            drift_type = "instruction_to_execution"

    return max(0, min(10, score)), drift_type


def aggregate_scores(scores: list[int]) -> dict[str, Any]:
    if not scores:
        raise ValueError("scores must be non-empty")
    return {
        "scores": scores,
        "score": int(round(median(scores))),
        "score_mean": sum(scores) / len(scores),
        "score_min": min(scores),
        "score_max": max(scores),
    }

