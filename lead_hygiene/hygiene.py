"""Hygiene: quarantine FAIL rows, never delete without an audit log."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import glob
import json
import os
import sys
from collections import Counter

LOG = "./bank/hygiene_log.jsonl"


def log(entry: dict, log_file: str = LOG) -> None:
    entry["at"] = dt.datetime.now().isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, "a") as fh:
        fh.write(json.dumps(entry) + "\n")


def quarantine(path: str, dry: bool, log_file: str) -> tuple[int, int]:
    with open(path) as fh:
        rows = list(csv.DictReader(fh))
    if not rows or "qualify" not in rows[0]:
        return 0, len(rows)

    keep = [r for r in rows if (r.get("qualify") or "").upper() != "FAIL"]
    drop = [r for r in rows if (r.get("qualify") or "").upper() == "FAIL"]
    if not drop:
        return 0, len(keep)

    month = dt.date.today().isoformat()[:7]
    qpath = os.path.join(
        os.path.dirname(path), f"quarantine-{month}-{os.path.basename(path)}"
    )

    if dry:
        print(f"  [dry] would quarantine {len(drop)} of {len(rows)} from {path}")
        return len(drop), len(keep)

    exists = os.path.exists(qpath)
    with open(qpath, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        if not exists:
            w.writeheader()
        w.writerows(drop)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(keep)

    log(
        {
            "action": "quarantine",
            "file": os.path.basename(path),
            "quarantined": len(drop),
            "kept": len(keep),
            "to": os.path.basename(qpath),
            "reasons": dict(Counter(r.get("qualify_flags", "") for r in drop)),
        },
        log_file,
    )
    print(f"  quarantined {len(drop)} FAIL rows -> {qpath} (kept {len(keep)})")
    return len(drop), len(keep)


def main() -> int:
    ap = argparse.ArgumentParser(description="Quarantine FAIL rows with an audit log.")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--log-file", default=LOG)
    args = ap.parse_args()

    files = args.files or sorted(glob.glob("./bank/qualified*.csv"))
    if not files:
        print("no qualified files found")
        return 0

    total_drop = total_keep = 0
    for path in files:
        d, k = quarantine(path, args.dry_run, args.log_file)
        total_drop += d
        total_keep += k

    print(f"\nquarantined {total_drop} | active {total_keep}")
    if not args.dry_run:
        log(
            {"action": "run_summary", "files": len(files),
             "quarantined": total_drop, "active": total_keep},
            args.log_file,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
