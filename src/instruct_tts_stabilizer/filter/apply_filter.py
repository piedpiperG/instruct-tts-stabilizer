from __future__ import annotations

import argparse
from pathlib import Path

from instruct_tts_stabilizer.io_utils import read_jsonl, write_jsonl


def should_keep(row: dict, *, threshold: int = 5) -> tuple[bool, str]:
    scores = row.get("scores")
    if isinstance(scores, list) and scores:
        bad_votes = sum(1 for s in scores if int(s) <= threshold)
        if bad_votes >= (len(scores) // 2 + 1):
            return False, f"majority_score_le_{threshold}"
    score = row.get("score")
    if score is None:
        raise ValueError("Scored row missing 'score'")
    if int(score) <= threshold:
        return False, f"score_le_{threshold}"
    return True, "kept"


def filter_rows(rows: list[dict], *, threshold: int = 5) -> tuple[list[dict], list[dict]]:
    kept: list[dict] = []
    rejected: list[dict] = []
    for row in rows:
        keep, reason = should_keep(row, threshold=threshold)
        annotated = {**row, "filter_threshold": threshold, "filter_reason": reason}
        if keep:
            kept.append(annotated)
        else:
            rejected.append(annotated)
    return kept, rejected


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Filter drifted instruction rewrites by verifier score.")
    parser.add_argument("--input", required=True, help="Scored candidates JSONL.")
    parser.add_argument("--output", required=True, help="Filtered output JSONL.")
    parser.add_argument("--rejected-output", default=None, help="Optional rejected rows JSONL.")
    parser.add_argument("--threshold", type=int, default=5)
    args = parser.parse_args(argv)

    rows = read_jsonl(args.input)
    kept, rejected = filter_rows(rows, threshold=args.threshold)
    write_jsonl(kept, Path(args.output))
    if args.rejected_output:
        write_jsonl(rejected, Path(args.rejected_output))
    print(f"kept {len(kept)} / {len(rows)} rows; rejected {len(rejected)}")


if __name__ == "__main__":
    main()

