from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from instruct_tts_stabilizer.io_utils import load_config, read_jsonl, slug, write_jsonl
from instruct_tts_stabilizer.llm import make_client

from .prompts import build_generation_messages, render_offline_candidate


def load_personas(config: dict[str, Any]) -> list[dict[str, Any]]:
    personas = config.get("personas")
    if not isinstance(personas, list) or not personas:
        raise ValueError("personas config must contain a non-empty 'personas' list")
    return personas


def load_constraints(config: dict[str, Any]) -> list[dict[str, Any]]:
    constraints = config.get("constraints")
    if not isinstance(constraints, list) or not constraints:
        raise ValueError("constraints config must contain a non-empty 'constraints' list")
    return constraints


def generate_candidates(
    seeds: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    *,
    provider: str = "offline",
    model: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.2,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    client = make_client(provider, model=model, base_url=base_url)
    rows: list[dict[str, Any]] = []
    count = 0
    for seed in seeds:
        if "id" not in seed or "category" not in seed:
            raise ValueError("Each seed row must contain 'id' and 'category'")
        for persona in personas:
            for constraint in constraints:
                if limit is not None and count >= limit:
                    return rows
                persona_id = persona.get("id") or slug(persona["name"])
                constraint_id = constraint.get("id") or slug(constraint["name"])
                if provider.lower() in {"offline", "none", "heuristic"}:
                    sentence = render_offline_candidate(seed, persona, constraint)
                    prompt_messages = []
                else:
                    prompt_messages = build_generation_messages(seed, persona, constraint)
                    sentence = client.chat(prompt_messages, temperature=temperature)
                rows.append(
                    {
                        "id": f"{seed['id']}__{persona_id}__{constraint_id}",
                        "seed_id": seed["id"],
                        "category": seed["category"],
                        "sentence": sentence,
                        "persona": persona["name"],
                        "persona_id": persona_id,
                        "constraint": constraint["name"],
                        "constraint_id": constraint_id,
                        "slot_type": seed.get("slot_type"),
                        "attributes": seed.get("attributes", {}),
                        "required_terms": seed.get("required_terms", []),
                        "generator_provider": provider,
                        "generator_model": model or provider,
                    }
                )
                count += 1
    return rows


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate controllably diversified TTS instructions.")
    parser.add_argument("--seeds", required=True, help="Seed attributes JSONL.")
    parser.add_argument("--personas", required=True, help="Persona config JSON.")
    parser.add_argument("--constraints", required=True, help="Constraint config JSON.")
    parser.add_argument("--output", required=True, help="Output candidates JSONL.")
    parser.add_argument("--provider", default="offline", help="offline, openai, deepseek, qwen, or vllm.")
    parser.add_argument("--model", default=None, help="Model name for online providers.")
    parser.add_argument("--base-url", default=None, help="Override OpenAI-compatible base URL.")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--limit", type=int, default=None, help="Optional row limit for smoke tests.")
    args = parser.parse_args(argv)

    seeds = read_jsonl(args.seeds)
    personas = load_personas(load_config(args.personas))
    constraints = load_constraints(load_config(args.constraints))
    rows = generate_candidates(
        seeds,
        personas,
        constraints,
        provider=args.provider,
        model=args.model,
        base_url=args.base_url,
        temperature=args.temperature,
        limit=args.limit,
    )
    write_jsonl(rows, Path(args.output))
    print(f"wrote {len(rows)} candidates to {args.output}")


if __name__ == "__main__":
    main()

