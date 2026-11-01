# Lead Hygiene

**Free lead discovery + honest lead qualification.** Discover businesses, qualify what
you actually found, and never call an unverified email "verified".

The valuable part of any lead pipeline is not the scraping — it is the hygiene:
checking that a domain can receive mail, that a live site exists, that the site
belongs to the company it claims to be, and tiering the result honestly.

```
Discover  ->  Qualify  ->  Tier  ->  Hygiene
(free or     (MX, site,   (A / A- / B)  (dedupe, suppress,
 your key)    identity)                 quarantine, log)
```

## Honest limits (this repo's core idea)

Every verdict states its own evidence:

- MX proves the **domain** can receive mail, not that the mailbox exists.
- A live site proves a business operates, not that the person still works there.
- A catch-all domain accepts any address. A `CATCH_ALL` email is **never** called verified.

If a tool promises "verified emails" without telling you what was actually verified,
it is lying to you. This tool tells you exactly what each check proved.

## Install

```bash
pip install -e .
```

## Quick start

```bash
# 1. Discover (free, no key required — OpenStreetMap)
lead-hygiene discover --query "roofing companies in Austin" --out leads.csv

# 2. Qualify ($0: DNS + plain HTTP)
lead-hygiene qualify leads.csv --out qualified.csv

# 3. Hygiene: quarantine FAILs, keep an audit log
lead-hygiene hygiene --bank-dir ./bank
```

## Providers

Discovery is pluggable. Bring your own keys; nothing is hardcoded.

| Provider | Cost | Notes |
|---|---|---|
| `osm` (default) | free | OpenStreetMap/Overpass. No key. Coverage varies by region |
| `google_places` | ~$ per call | Your Google Maps API key |
| `treg` | ~$0.0002/call | TREG catalog (`treg.google.serp.maps`) |
| `getleadsio` | free trial quota | 250 rows/call, includes `email_status` — the shortcut this repo replaces |

Configure via `.env` (see `.env.example`) or `config.toml`.

## Output tiers

| Tier | Meaning | Sendable? |
|---|---|---|
| **A** | VALID email + MX + live site | Yes |
| **A-** | CATCH_ALL email + MX + live site | Your call, never labelled verified |
| **B** | Unknown status or weak site evidence | No — quarantined or flagged |

## License

MIT
