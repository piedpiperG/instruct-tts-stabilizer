from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from instruct_tts_stabilizer.io_utils import read_jsonl, write_jsonl


def copy_demo_assets(
    *,
    list_jsonl: str | Path,
    system_dirs: list[str],
    tasks: list[str],
    output_dir: str | Path,
) -> dict[str, int]:
    rows = read_jsonl(list_jsonl)
    ids = [row["id"] for row in rows]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(rows, output_dir / "list.jsonl")

    copied = 0
    missing = 0
    for system_dir in system_dirs:
        src_system = Path(system_dir)
        system_name = src_system.name
        for task in tasks:
            dst_task = output_dir / system_name / task
            dst_task.mkdir(parents=True, exist_ok=True)
            for sample_id in ids:
                src = src_system / task / f"{sample_id}.wav"
                dst = dst_task / f"{sample_id}.wav"
                if src.exists():
                    shutil.copy2(src, dst)
                    copied += 1
                else:
                    missing += 1
    return {"samples": len(ids), "copied": copied, "missing": missing}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Copy evaluation outputs into a demopage asset directory.")
    parser.add_argument("--list", required=True, help="Demo list JSONL.")
    parser.add_argument("--system-dir", action="append", required=True, help="System output dir; repeatable.")
    parser.add_argument("--tasks", default="APS,DSD,RP")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    stats = copy_demo_assets(
        list_jsonl=args.list,
        system_dirs=args.system_dir,
        tasks=[t.strip() for t in args.tasks.split(",") if t.strip()],
        output_dir=args.output_dir,
    )
    print(stats)


if __name__ == "__main__":
    main()

