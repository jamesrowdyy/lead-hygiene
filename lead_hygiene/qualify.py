"""Qualify lead rows: MX, live site, identity, tier.

$0 to run: DNS + plain HTTP only, no API spend.

Verdicts state their own evidence:
  PASS  = domain has a real MX record AND a live site answered
  WEAK  = partial evidence, or evidence that contradicts identity
          (DNS unresolvable, dead site, social-page "website", title mismatch)
  FAIL  = domain cannot receive mail (or does not exist)
"""
from __future__ import annotations

import csv
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

try:
    import dns.resolver

    def has_mx(domain: str):
        """True/False = proven; None = could not resolve (treated as unknown)."""
        if not domain:
            return False
        try:
            answers = dns.resolver.resolve(domain, "MX", lifetime=8)
            # RFC 7505 null MX: the domain explicitly accepts no mail
            return bool(answers) and not all(str(r.exchange) == "." for r in answers)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            return False
        except Exception:
            return None

except ImportError:  # pragma: no cover - dig fallback
    import subprocess

    def has_mx(domain: str):
        if not domain:
            return False
        try:
            out = subprocess.run(
                ["dig", "+short", "+time=3", "+tries=1", "MX", domain],
                capture_output=True, text=True, timeout=8,
            ).stdout
            if not out.strip():
                return False
            return None if "communications error" in out.lower() else True
        except Exception:
            return None


UA = "lead-hygiene/0.1 (free lead hygiene checker; +https://github.com/jamesrowdyy/lead-hygiene)"

# crude public-suffix handling for registered-domain matching (good enough for redirects)
_MULTIPART_SUFFIXES = {"co.uk", "org.uk", "com.au", "co.nz", "co.jp", "com.sg", "com.br"}


def registered_domain(host: str) -> str:
    host = (host or "").strip().lower().removeprefix("www.")
    parts = host.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in _MULTIPART_SUFFIXES:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def site_probe(domain: str) -> tuple[bool, int, str, str]:
    """-> (live, status, final_host, title)"""
    if not domain:
        return False, 0, "", ""
    for scheme in ("https", "http"):
        try:
            req = urllib.request.Request(
                f"{scheme}://{domain}", headers={"User-Agent": UA}, method="GET"
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw = resp.read(120_000).decode("utf-8", "ignore")
                m = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
                title = re.sub(r"\s+", " ", m.group(1)).strip()[:120] if m else ""
                host = re.sub(r"^https?://", "", resp.geturl()).split("/")[0].lower()
                return True, resp.status, host, title
        except urllib.error.HTTPError as exc:
            # 403/410/5xx still prove a server answered on that host; 404 on / is
            # weaker evidence, but a live server exists either way
            return True, exc.code, domain, ""
        except Exception:
            continue
    return False, 0, "", ""


def linkedin_ok(url: str) -> bool:
    return bool(re.search(r"linkedin\.com/in/[A-Za-z0-9\-_%]+", url or "", re.I))


def title_matches(title: str, company: str) -> bool | None:
    """Shared-word identity check. None = no evidence either way."""
    stop = {"the", "and", "of", "for", "in", "inc", "llc", "ltd", "co", "group", "home"}
    tw = {w for w in re.findall(r"[a-z0-9]+", (company or "").lower()) if w not in stop}
    ti = {w for w in re.findall(r"[a-z0-9]+", (title or "").lower()) if w not in stop}
    if not tw or not ti:
        return None
    return bool(tw & ti)


def normalize_domain(domain: str) -> str:
    d = (domain or "").strip().lower()
    for p in ("https://", "http://"):
        if d.startswith(p):
            d = d[len(p):]
    return d.split("/")[0].removeprefix("www.")


_SOCIAL_DOMAINS = {"facebook.com", "instagram.com", "linktr.ee", "x.com",
                   "twitter.com", "tiktok.com", "wixsite.com", "business.site"}


def _is_social(domain: str) -> bool:
    return any(domain == s or domain.endswith("." + s) for s in _SOCIAL_DOMAINS)


def qualify_row(row: dict) -> dict:
    domain = normalize_domain(row.get("domain"))
    row["domain"] = domain
    company = row.get("company") or row.get("name") or ""
    mx = has_mx(domain)
    live, status, final_host, title = site_probe(domain) if mx else (False, 0, "", "")
    li = linkedin_ok(row.get("linkedin") or "")

    flags = []
    if _is_social(domain):
        flags.append("social_page")  # not the company's own site
    if mx is None:
        flags.append("dns_error")
    elif mx is False:
        flags.append("no_mx")
    if mx and not live:
        flags.append("site_dead")
    if live and final_host and registered_domain(final_host) != registered_domain(domain):
        flags.append(f"redirects:{final_host}")
    if (row.get("email_status") or "").upper() == "CATCH_ALL":
        flags.append("catch_all")
    if not li:
        flags.append("no_linkedin")

    identity = title_matches(title, company)
    if identity is True:
        flags.append("title_match")
    elif identity is False:
        flags.append("title_mismatch")

    if mx is True and live and "social_page" not in flags:
        verdict = "PASS"
    elif mx is not False:
        # DNS unknown, live-only, or a contradicting identity flag
        verdict = "WEAK"
    else:
        verdict = "FAIL"
    if verdict == "PASS" and "title_mismatch" in flags:
        verdict = "WEAK"

    row.update(
        {
            "mx_ok": "" if mx is None else ("yes" if mx else "no"),
            "site_live": "yes" if live else "no",
            "http_status": status or "",
            "site_title": title,
            "redirect_host": final_host if final_host and final_host != domain else "",
            "title_match": {True: "yes", False: "no", None: ""}[identity],
            "linkedin_ok": "yes" if li else "no",
            "qualify": verdict,
            "qualify_flags": ";".join(flags),
        }
    )
    return row


def qualify_csv(path: str, out: str | None = None, workers: int = 12) -> dict:
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return {"total": 0}

    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(qualify_row, rows))

    counts = {"PASS": 0, "WEAK": 0, "FAIL": 0}
    for r in rows:
        counts[r["qualify"]] += 1
    mails = sum(1 for r in rows if "@" in (r.get("email") or ""))
    pass_mail = sum(
        1 for r in rows if r["qualify"] == "PASS" and "@" in (r.get("email") or "")
    )

    if not out:
        root, ext = os.path.splitext(path)
        out = f"{root}.qualified{ext or '.csv'}"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    return {"total": len(rows), "counts": counts, "emails": mails,
            "sendable": pass_mail, "out": out}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m lead_hygiene.qualify <leads.csv>")
        sys.exit(1)
    s = qualify_csv(sys.argv[1])
    print(s)
