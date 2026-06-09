from __future__ import annotations

from typing import Any


GENERATION_SYSTEM = """You are a Chinese TTS instruction rewriting expert.
Rewrite the source instruction into the requested user persona and sentence
pattern while preserving the original control intent exactly.

Hard rules:
1. The output must still be an instruction to the TTS system.
2. Do not perform the target style, emotion, accent, or role yourself.
3. Do not silently change entities, labels, accents, emotions, or speaker roles.
4. Return only one rewritten instruction, with no explanation.
"""


def build_generation_messages(
    seed: dict[str, Any],
    persona: dict[str, Any],
    constraint: dict[str, Any],
) -> list[dict[str, str]]:
    category = seed["category"]
    required_terms = seed.get("required_terms") or []
    required_line = "、".join(required_terms) if required_terms else "None"
    persona_prompt = persona.get("prompt", persona.get("description", persona["name"]))
    constraint_text = constraint.get("instruction", constraint.get("name", ""))
    user = f"""Source instruction:
{category}

Persona/style requirement:
{persona_prompt}

Sentence-pattern constraint:
{constraint_text}

Required terms that must be preserved if present:
{required_line}

Rewrite the source instruction now."""
    return [
        {"role": "system", "content": GENERATION_SYSTEM},
        {"role": "user", "content": user},
    ]


def render_offline_candidate(seed: dict[str, Any], persona: dict[str, Any], constraint: dict[str, Any]) -> str:
    instruction = seed["category"]
    template = persona.get("offline_template", "{instruction}")
    sentence = template.format(instruction=instruction)
    max_chars = constraint.get("max_chars")
    if max_chars and len(sentence) > int(max_chars):
        # Keep the semantic anchor in short offline examples.
        sentence = f"{instruction}。"
    return sentence.strip()

