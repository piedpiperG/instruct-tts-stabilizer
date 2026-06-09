from __future__ import annotations

import argparse
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

from instruct_tts_stabilizer.io_utils import load_config, read_jsonl, slug, write_jsonl


def atempo_chain(factor: float) -> list[str]:
    if factor <= 0:
        raise ValueError("tempo factor must be positive")
    values: list[float] = []
    while factor > 2.0:
        values.append(2.0)
        factor /= 2.0
    while factor < 0.5:
        values.append(0.5)
        factor /= 0.5
    values.append(factor)
    return [f"atempo={value:.8f}" for value in values if abs(value - 1.0) > 1e-6]


def build_ffmpeg_filter(
    *,
    pitch_semitones: float = 0.0,
    speed_factor: float = 1.0,
    volume_db: float = 0.0,
    sample_rate: int = 16000,
) -> str:
    filters: list[str] = []
    if abs(pitch_semitones) > 1e-6:
        ratio = 2 ** (pitch_semitones / 12)
        filters.append(f"asetrate={sample_rate}*{ratio:.8f}")
        filters.append(f"aresample={sample_rate}")
        filters.extend(atempo_chain(1 / ratio))
    filters.extend(atempo_chain(speed_factor))
    if abs(volume_db) > 1e-6:
        filters.append(f"volume={volume_db:g}dB")
    return ",".join(filters) if filters else "anull"


def build_ffmpeg_command(
    input_path: Path,
    output_path: Path,
    *,
    pitch_semitones: float = 0.0,
    speed_factor: float = 1.0,
    volume_db: float = 0.0,
    sample_rate: int = 16000,
) -> list[str]:
    audio_filter = build_ffmpeg_filter(
        pitch_semitones=pitch_semitones,
        speed_factor=speed_factor,
        volume_db=volume_db,
        sample_rate=sample_rate,
    )
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-af",
        audio_filter,
        "-ar",
        str(sample_rate),
        str(output_path),
    ]


def prompt_for_variant(kind: str, value: float) -> str:
    if kind == "pitch":
        return "请用更高的音调说。" if value > 0 else "请用更低的音调说。"
    if kind == "speed":
        return "请加快语速说。" if value > 1 else "请放慢语速说。"
    if kind == "volume":
        return "请用更大的音量说。" if value > 0 else "请用更小的音量说。"
    raise ValueError(f"Unknown perturbation kind: {kind}")


def iter_variants(config: dict[str, Any]) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    for value in config.get("pitch_semitones", []):
        variants.append({"kind": "pitch", "value": float(value), "pitch_semitones": float(value)})
    for value in config.get("speed_factors", []):
        variants.append({"kind": "speed", "value": float(value), "speed_factor": float(value)})
    for value in config.get("volume_db", []):
        variants.append({"kind": "volume", "value": float(value), "volume_db": float(value)})
    return variants


def perturb_manifest(
    rows: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    output_dir: str | Path,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    output_dir = Path(output_dir)
    sample_rate = int(config.get("sample_rate", 16000))
    variants = iter_variants(config)
    if not variants:
        raise ValueError("No perturbation variants configured")
    if not dry_run and shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required for audio perturbation; rerun with --dry-run to preview")

    out_rows: list[dict[str, Any]] = []
    for row in rows:
        audio_path = Path(row["audio_path"])
        base_id = row.get("id") or audio_path.stem
        for variant in variants:
            suffix = f"{variant['kind']}_{variant['value']:g}".replace("-", "m").replace(".", "p")
            out_path = output_dir / str(base_id) / f"{suffix}.wav"
            params = {
                "pitch_semitones": float(variant.get("pitch_semitones", 0.0)),
                "speed_factor": float(variant.get("speed_factor", 1.0)),
                "volume_db": float(variant.get("volume_db", 0.0)),
                "sample_rate": sample_rate,
            }
            cmd = build_ffmpeg_command(audio_path, out_path, **params)
            if not dry_run:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out_rows.append(
                {
                    "id": f"{base_id}__{suffix}",
                    "source_id": base_id,
                    "text": row.get("text", ""),
                    "audio_path": str(out_path),
                    "source_audio_path": str(audio_path),
                    "instruction": prompt_for_variant(variant["kind"], variant["value"]),
                    "perturbation": variant,
                    "ffmpeg_filter": build_ffmpeg_filter(**params),
                    "dry_run": dry_run,
                    "seed_id": row.get("seed_id"),
                }
            )
    return out_rows


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create attribute-aligned pitch/speed/volume perturbation data.")
    parser.add_argument("--input", required=True, help="Input audio manifest JSONL with audio_path/text.")
    parser.add_argument("--config", required=True, help="Perturbation config JSON.")
    parser.add_argument("--output-dir", required=True, help="Directory for generated wav files.")
    parser.add_argument("--manifest-output", required=True, help="Output perturbation manifest JSONL.")
    parser.add_argument("--dry-run", action="store_true", help="Do not call ffmpeg; write the planned manifest only.")
    args = parser.parse_args(argv)

    rows = read_jsonl(args.input)
    config = load_config(args.config)
    out_rows = perturb_manifest(rows, config, output_dir=args.output_dir, dry_run=args.dry_run)
    write_jsonl(out_rows, Path(args.manifest_output))
    print(f"wrote {len(out_rows)} perturbation rows to {args.manifest_output}")


if __name__ == "__main__":
    main()

