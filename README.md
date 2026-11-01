# Lead Hygiene

![Lead Hygiene pipeline](docs/hero.png)

**Lead Hygiene is the qualification layer for lead generation pipelines.** It
takes raw business leads from any source and grades every row on hard evidence —
DNS, HTTP and page identity — then finds contact emails from each business's own
website. All of it runs on DNS and plain HTTP: **the whole pipeline costs $0**.

Scrapers are a solved problem. What separates a working pipeline from a wasted
one is what happens after the scrape: dead domains, parked pages, social-media
placeholders pretending to be websites, and unverified emails. Lead Hygiene
removes those before they reach your CRM.

## Measured on a real run

96 real coffee shops discovered in Bristol (free OpenStreetMap, no key):

```
$ lead-hygiene qualify leads.csv --out qualified.csv
{'total': 96, 'counts': {'PASS': 74, 'WEAK': 12, 'FAIL': 10}}   # 39 s, $0

$ lead-hygiene contacts qualified.csv --out contacts.csv
{'total': 96, 'with_email': 50}                                 # 101 s, $0

$ lead-hygiene hygiene contacts.csv
quarantined 10 FAIL rows -> quarantine-2026-11-contacts.csv (kept 86)
```

50 of 96 leads (52%) came back with a contact email, 45 of them on the
business's own domain. Sample rows (email local-parts redacted here):

| company | domain | contact_email | qualify | title_match |
|---|---|---|---|---|
| Arnolfini Cafe Bar | arnolfini.org.uk | `i***@arnolfini.org.uk` | PASS | yes |
| Mud Dock Cafe | mud-dock.co.uk | `c***@mud-dock.co.uk` | PASS | yes |
| Starbucks | starbucks.com | `p***@starbucks.com` | PASS | yes |
| The Bristol Loaf | thebristolloaf.co.uk | *(none found)* | PASS | yes |

## What it costs vs the alternatives

For the same job — find a business and a usable contact email:

| Approach | Cost per contact |
|---|---|
| **Lead Hygiene** (discovery + qualify + contacts) | **$0** (bandwidth only) |
| Typical enrichment APIs | ~$0.03–0.10 per contact |
| Email verification APIs | ~$0.008 per address checked |

That gap is the point: the qualification logic is pure DNS and HTTP, so it
scales to thousands of rows without a meter running.

## What it checks

| Verdict | Evidence |
|---|---|
| **PASS** | Real MX record + live site answered + page identity consistent with the company name |
| **WEAK** | Partial evidence or contradictions: DNS unresolvable, dead site, social-page "website", title mismatch |
| **FAIL** | Domain cannot receive mail (or does not exist) |

Every row carries its evidence columns: `mx_ok`, `site_live`, `http_status`,
`site_title`, `redirect_host`, `title_match`, plus a `qualify_flags` list
(`catch_all`, `no_linkedin`, `dns_error`, …). A catch-all domain accepts any
address, so a `CATCH_ALL` email is reported as such — never as verified.

Found emails are addresses that appear on the business's own site. The MX check
proves the domain receives mail; a per-address SMTP probe is a separate decision
and intentionally not automatic.

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

# 3. Find contact emails from each PASS lead's own website ($0)
lead-hygiene contacts qualified.csv --out contacts.csv

# 4. Quarantine FAIL rows, keep an audit log
lead-hygiene hygiene contacts.csv
```

## Providers

| Provider | Cost | Notes |
|---|---|---|
| `osm` (default) | free | OpenStreetMap via Overpass. No key. Coverage varies by region |
| `google_places` | ~$ per call | Your own Google Places API key (`GOOGLE_PLACES_API_KEY`) |

Keys go in your environment — nothing is hardcoded and no key is required for
the free path.

## Compliance notes

- Respect [Nominatim's usage policy](https://operations.osmfoundation.org/policies/nominatim/)
  and Overpass fair-use: cache results, keep request rates low, attribute
  OpenStreetMap contributors (ODbL).
- Google Places has its own storage and caching terms — check them before
  storing results.
- Lead data is personal data in most jurisdictions. If you outreach, you own
  the compliance (GDPR, CAN-SPAM, PECR).
- This is a local CLI. Don't wrap it in a public web service without adding
  input validation first — the site probe follows redirects.

## License

MIT
