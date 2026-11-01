"""Find contact emails from qualified leads' own websites. $0.

For each PASS row: fetch the homepage plus common contact pages, extract
email addresses, and prefer ones on the lead's own domain with a role prefix
(contact@, info@, hello@...). These are found addresses, not verified
mailboxes — MX was already proven by qualify; a per-address SMTP probe is a
separate decision and not done here.
"""
from __future__ import annotations

import csv
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from .qualify import UA

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)
BAD_EMAIL = re.compile(
    r"(?i)^(noreply|no-reply|donotreply|postmaster|abuse|webmaster|"
    r"sentry|wixpress|example|test|user|email)@|"
    r"\.(png|jpe?g|gif|webp|svg|css|js)$"
)
ROLE_PREFIXES = ("info", "contact", "hello", "office", "sales", "admin",
                 "enquiries", "enquiry", "bookings", "team", "mail")
CONTACT_PATHS = ("", "contact", "contact-us", "contact/", "about",
                 "about-us", "about/", "impressum")

CACHE: dict[str, list[str]] = {}


def _fetch(url: str, timeout: int = 10) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(300_000).decode("utf-8", "ignore")
    except Exception:
        return ""


def _score(email: str, domain: str) -> tuple[int, int]:
    local = email.split("@")[0].lower()
    own = domain and email.lower().endswith("@" + domain)
    role = 1 if local in ROLE_PREFIXES else 0
    return (1 if own else 0, role)


def find_emails(domain: str) -> list[str]:
    """Return candidate contact emails for a domain, best first. Cached per domain."""
    if not domain:
        return []
    if domain in CACHE:
        return CACHE[domain]

    found: set[str] = set()
    for path in CONTACT_PATHS:
        body = _fetch(f"https://{domain}/{path}")
        if body:
            for m in EMAIL_RE.finditer(body.replace("mailto:", " ")):
                e = m.group(0).strip(".").lower()
                if not BAD_EMAIL.search(e):
                    found.add(e)
        if found and path == "":  # homepage hit is good enough to stop early
            break

    ranked = sorted(found, key=lambda e: _score(e, domain), reverse=True)
    CACHE[domain] = ranked
    return ranked


def add_contacts(path: str, out: str | None = None, workers: int = 8) -> dict:
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return {"total": 0}

    targets = [r for r in rows if r.get("qualify") == "PASS" and r.get("domain")]
    with ThreadPoolExecutor(workers) as ex:
        results = dict(zip(
            [r["domain"] for r in targets],
            ex.map(find_emails, [r["domain"] for r in targets]),
        ))

    for r in rows:
        emails = results.get(r.get("domain") or "", [])
        r["contact_email"] = emails[0] if emails else ""
        r["contact_source"] = "site_crawl" if emails else ""

    with_email = sum(1 for r in rows if r["contact_email"])
    if not out:
        root, ext = os.path.splitext(path)
        out = f"{root}.contacts{ext or '.csv'}"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    return {"total": len(rows), "with_email": with_email, "out": out}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m lead_hygiene.contacts <qualified.csv>")
        sys.exit(1)
    print(add_contacts(sys.argv[1]))
