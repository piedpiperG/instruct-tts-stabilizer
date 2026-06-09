from __future__ import annotations

import argparse
from pathlib import Path

from instruct_tts_stabilizer.io_utils import read_jsonl, write_jsonl
from instruct_tts_stabilizer.llm import make_client

from .drift import (
    aggregate_scores,
    build_classification_messages,
    build_scoring_messages,
    heuristic_score,
    parse_drift_type,
    parse_score,
)


def score_rows(
    rows: list[dict],
    *,
    provider: str = "heuristic",
    model: str | None = None,
    base_url: str | None = None,
    vote_times: int = 1,
    temperature: float = 0.0,
) -> list[dict]:
    if vote_times < 1:
        raise ValueError("vote_times must be >= 1")
    client = make_client(provider, model=model, base_url=base_url)
    out: list[dict] = []
    for row in rows:
        category = row.get("category")
        sentence = row.get("sentence")
        if not category or not sentence:
            raise ValueError("Each candidate row must contain 'category' and 'sentence'")
        required_terms = row.get("required_terms") or []
        if provider.lower() in {"heuristic", "offline", "none"}:
            score, drift_type = heuristic_score(category, sentence, required_terms)
            scored = {**row, **aggregate_scores([score]), "drift_type": drift_type}
        else:
            scores = []
            for _ in range(vote_times):
                reply = client.chat(
                    build_scoring_messages(category, sentence, required_terms),
                    temperature=temperature,
                )
                scores.append(parse_score(reply))
            drift_reply = client.chat(
                build_classification_messages(category, sentence, required_terms),
                temperature=0.0,
            )
            scored = {
                **row,
                **aggregate_scores(scores),
                "drift_type": parse_drift_type(drift_reply),
            }
        scored["verifier_provider"] = provider
        scored["verifier_model"] = model or provider
        out.append(scored)
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Score candidate instruction rewrites for semantic drift.")
    parser.add_argument("--input", required=True, help="Candidate JSONL.")
    parser.add_argument("--output", required=True, help="Scored JSONL.")
    parser.add_argument("--provider", default="heuristic", help="heuristic, openai, deepseek, qwen, or vllm.")
    parser.add_argument("--model", default=None, help="Model name for online providers.")
    parser.add_argument("--base-url", default=None, help="Override OpenAI-compatible base URL.")
    parser.add_argument("--vote-times", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=0.0)
    args = parser.parse_args(argv)

    rows = read_jsonl(args.input)
    scored = score_rows(
        rows,
        provider=args.provider,
        model=args.model,
        base_url=args.base_url,
        vote_times=args.vote_times,
        temperature=args.temperature,
    )
    write_jsonl(scored, Path(args.output))
    print(f"wrote {len(scored)} scored rows to {args.output}")


if __name__ == "__main__":
    main()

