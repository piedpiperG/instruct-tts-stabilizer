from __future__ import annotations

import argparse
from pathlib import Path

from instruct_tts_stabilizer.io_utils import read_jsonl, write_jsonl


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            curr.append(
                min(
                    prev[j] + 1,
                    curr[j - 1] + 1,
                    prev[j - 1] + (ca != cb),
                )
            )
        prev = curr
    return prev[-1]


def cer(reference: str, hypothesis: str) -> float:
    if not reference:
        return 0.0 if not hypothesis else 1.0
    return edit_distance(reference, hypothesis) / len(reference)


def score_text_rows(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        ref = row.get("reference_text") or row.get("text") or ""
        hyp = row.get("hypothesis_text") or row.get("asr_text") or ""
        out.append({**row, "cer": cer(ref, hyp)})
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compute CER for rows with reference/hypothesis text.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    rows = score_text_rows(read_jsonl(args.input))
    write_jsonl(rows, Path(args.output))
    if rows:
        avg = sum(row["cer"] for row in rows) / len(rows)
        print(f"wrote {len(rows)} rows; average CER={avg:.4f}")
    else:
        print("wrote 0 rows")


if __name__ == "__main__":
    main()

