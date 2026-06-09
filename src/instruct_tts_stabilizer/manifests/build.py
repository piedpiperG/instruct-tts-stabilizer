from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from instruct_tts_stabilizer.io_utils import read_jsonl, write_jsonl


def build_sft_manifest(
    audio_rows: list[dict[str, Any]],
    instruction_rows: list[dict[str, Any]],
    perturb_rows: list[dict[str, Any]] | None = None,
    *,
    output_format: str = "generic",
) -> list[dict[str, Any]]:
    by_seed: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in instruction_rows:
        seed_id = row.get("seed_id")
        if seed_id:
            by_seed[str(seed_id)].append(row)

    out: list[dict[str, Any]] = []
    for audio in audio_rows:
        seed_id = str(audio.get("seed_id") or audio.get("id"))
        matches = by_seed.get(seed_id, [])
        for inst in matches:
            out.append(format_sft_row(audio, inst.get("sentence", inst.get("instruction", "")), inst, output_format))

    for perturbed in perturb_rows or []:
        out.append(format_sft_row(perturbed, perturbed["instruction"], perturbed, output_format))
    return out


def format_sft_row(audio: dict[str, Any], instruction: str, meta: dict[str, Any], output_format: str) -> dict[str, Any]:
    row_id = f"{audio.get('id', 'audio')}__{meta.get('id', 'instruction')}"
    text = audio.get("text", "")
    audio_path = audio.get("audio_path")
    if not audio_path:
        raise ValueError("Audio row missing audio_path")

    if output_format == "cosyvoice2":
        return {
            "id": row_id,
            "text": text,
            "prompt_text": instruction,
            "audio": audio_path,
            "source": meta.get("id", ""),
            "meta": {
                "seed_id": audio.get("seed_id"),
                "instruction_source": meta.get("generator_model") or meta.get("source_id"),
            },
        }
    if output_format == "generic":
        return {
            "id": row_id,
            "text": text,
            "instruction": instruction,
            "audio_path": audio_path,
            "source": meta.get("id", ""),
            "seed_id": audio.get("seed_id"),
        }
    raise ValueError(f"Unsupported output format: {output_format}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build SFT manifests from filtered instructions and audio rows.")
    parser.add_argument("--audio", required=True, help="Base audio manifest JSONL.")
    parser.add_argument("--instructions", required=True, help="Filtered instruction JSONL.")
    parser.add_argument("--perturbed", default=None, help="Optional perturbation manifest JSONL.")
    parser.add_argument("--format", default="generic", choices=["generic", "cosyvoice2"])
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    audio_rows = read_jsonl(args.audio)
    instruction_rows = read_jsonl(args.instructions)
    perturb_rows = read_jsonl(args.perturbed) if args.perturbed else None
    rows = build_sft_manifest(audio_rows, instruction_rows, perturb_rows, output_format=args.format)
    write_jsonl(rows, Path(args.output))
    print(f"wrote {len(rows)} SFT rows to {args.output}")


if __name__ == "__main__":
    main()

