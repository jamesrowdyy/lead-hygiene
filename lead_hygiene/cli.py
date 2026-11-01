"""CLI: lead-hygiene discover|qualify|hygiene"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import urllib.error

from . import __version__
from .providers import get_provider


def cmd_discover(args) -> int:
    creds = {}
    key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if args.provider == "google_places" and key:
        creds["api_key"] = key
    try:
        rows = get_provider(args.provider, **creds).search(args.query, args.country)
    except (ValueError, OSError, urllib.error.URLError) as exc:
        print(f"discover failed: {exc}", file=sys.stderr)
        return 1
    if not rows:
        print("no rows found")
        return 2
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows -> {args.out}")
    return 0


def cmd_qualify(args) -> int:
    from .qualify import qualify_csv

    s = qualify_csv(args.file, out=args.out, workers=args.workers)
    print(s)
    return 0


def cmd_contacts(args) -> int:
    from .contacts import add_contacts

    print(add_contacts(args.file, out=args.out, workers=args.workers))
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "hygiene":
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        from . import hygiene

        return hygiene.main()

    ap = argparse.ArgumentParser(prog="lead-hygiene")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("discover", help="discover leads (free OSM default)")
    d.add_argument("--query", required=True)
    d.add_argument("--provider", default="osm")
    d.add_argument("--country", default="US")
    d.add_argument("--out", default="leads.csv")
    d.set_defaults(func=cmd_discover)

    q = sub.add_parser("qualify", help="qualify a leads CSV ($0)")
    q.add_argument("file")
    q.add_argument("--out")
    q.add_argument("--workers", type=int, default=12)
    q.set_defaults(func=cmd_qualify)

    c = sub.add_parser("contacts", help="find contact emails from PASS leads' own sites ($0)")
    c.add_argument("file")
    c.add_argument("--out")
    c.add_argument("--workers", type=int, default=8)
    c.set_defaults(func=cmd_contacts)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
