# Lead Hygiene

**Free lead discovery + honest lead qualification.** Discover businesses, check what
you actually found, and never call an unverified email "verified".

The valuable part of any lead pipeline is not the scraping — it is the hygiene:
checking that a domain can receive mail, that a live site exists, that the site
belongs to the company it claims to be, and grading the result honestly.

```
Discover  ->  Qualify  ->  Hygiene
(free or     (MX, site,     (quarantine,
 your key)    identity)      audit log)
```

## Honest limits (this repo's core idea)

Every verdict states its own evidence:

- MX proves the **domain** can receive mail, not that the mailbox exists.
- A live site proves a business operates, not that the person still works there.
- A catch-all domain accepts any address. A `CATCH_ALL` email is **never** called verified.
- The free discovery source provides **no emails and no LinkedIn profiles** — discovery
  and contact-finding are different problems. Paid providers can fill that gap.

If a tool promises "verified emails" without telling you what was actually verified,
it is lying to you. This tool tells you exactly what each check proved.

## Install

```bash
pip install -e .
```

## Quick start

```bash
# 1. Discover (free, no key required — OpenStreetMap)
lead-hygiene discover --query "coffee shop in Bristol" --out leads.csv

# 2. Qualify ($0: DNS + plain HTTP)
lead-hygiene qualify leads.csv --out qualified.csv

# 3. Quarantine FAIL rows, keep an audit log
lead-hygiene hygiene qualified.csv
```

## Verdicts

| Verdict | Evidence |
|---|---|
| **PASS** | Real MX record + live site answered |
| **WEAK** | Partial evidence, or contradicting identity (DNS unresolvable, dead site, social-page "website", title mismatch) |
| **FAIL** | Domain cannot receive mail (or does not exist) |

Each row carries its evidence columns: `mx_ok`, `site_live`, `http_status`,
`site_title`, `redirect_host`, `title_match`, plus a `qualify_flags` list
(`catch_all`, `no_linkedin`, `dns_error`, …).

## Providers

| Provider | Cost | Notes |
|---|---|---|
| `osm` (default) | free | OpenStreetMap via Overpass. No key. Coverage varies by region; no emails |
| `google_places` | ~$ per call | Your own Google Places API key (`GOOGLE_PLACES_API_KEY`) |

Keys go in your environment — nothing is hardcoded and no key is required for the
free path.

## Responsible use

- Respect [Nominatim's usage policy](https://operations.osmfoundation.org/policies/nominatim/)
  and Overpass fair-use: cache results, keep request rates low, attribute OpenStreetMap
  contributors (ODbL).
- Google Places has its own storage and caching terms — check them before storing results.
- Lead data is personal data in most jurisdictions. If you outreach, you own the
  compliance (GDPR, CAN-SPAM, PECR). This tool verifies data; it does not legalise contact.
- This is a local CLI. Don't wrap it in a public web service without adding input
  validation first — the site probe follows redirects.

## License

MIT
