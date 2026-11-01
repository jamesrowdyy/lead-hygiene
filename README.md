# Lead Hygiene

![Lead Hygiene pipeline](docs/hero.png)

# Up to 5,000 contactable leads a day. Zero dollars.

Every lead-gen tool charges you per contact — enrichment APIs, email finders,
"verified email" databases. This repo does the whole job with none of that:

1. **It finds businesses** — coffee shops, roofers, law firms, gyms — in any
   city, from free public map data. No account, no API key, no card.
2. **It checks every business is real** — the website is live, it belongs to
   that business, and their email system actually exists.
3. **It finds the contact email** — pulled from the business's *own* website,
   not a stale bought database.

Your only cost is electricity: run it overnight, wake up to a clean CSV.

## What you actually get

A real run — 96 coffee shops in Bristol, no keys, nothing paid:

```
$ lead-hygiene qualify leads.csv --out qualified.csv
{'total': 96, 'counts': {'PASS': 74, 'WEAK': 12, 'FAIL': 10}}   # 39 s, $0

$ lead-hygiene contacts qualified.csv --out contacts.csv
{'total': 96, 'with_email': 50}                                 # 101 s, $0

$ lead-hygiene hygiene contacts.csv
quarantined 10 FAIL rows -> quarantine-2026-11-contacts.csv (kept 86)
```

50 of 96 leads came back with a contact email — 45 of them the business's own
address. Sample rows (emails redacted here):

| company | domain | contact_email | qualify |
|---|---|---|---|
| Arnolfini Cafe Bar | arnolfini.org.uk | `i***@arnolfini.org.uk` | PASS |
| Mud Dock Cafe | mud-dock.co.uk | `c***@mud-dock.co.uk` | PASS |
| Starbucks | starbucks.com | `p***@starbucks.com` | PASS |
| The Bristol Loaf | thebristolloaf.co.uk | *(none found)* | PASS |

## How many leads a day?

One search covers one business type in one city. The full chain takes ~3
minutes per search — or ~20 minutes for 100 searches run in parallel.

| Searches per night | Businesses checked | Contact emails found | Cost |
|---|---|---|---|
| 10 | ~1,000 | ~500 | $0 |
| 50 | ~4,800 | ~2,500 | $0 |
| 100 | ~9,600 | ~5,000 | $0 |

Multiply by 30 for a working month. The ceiling isn't money — it's how many
city × business-type combinations you want to cover.

**Why is it free?** Because checking a business is just DNS lookups and opening
web pages — things your computer already does for free. The paid tools charge
for the same lookups plus their margin. Where they genuinely add value is
deeper email verification and richer firmographics; Lead Hygiene supports
those as optional paid providers (below), so you only pay when you decide you
need more.

**The honest footnote:** found emails are addresses published on the business's
own site. This tool proves their mail system exists — it does not promise the
specific inbox is monitored. That's the line most "verified email" marketing
blurs; here it's stated up front.

## Getting started

```bash
pip install -e .

# find coffee shops in Bristol, check them, get emails, quarantine the dead
lead-hygiene discover --query "coffee shop in Bristol" --out leads.csv
lead-hygiene qualify leads.csv --out qualified.csv
lead-hygiene contacts qualified.csv --out contacts.csv
lead-hygiene hygiene contacts.csv
```

Swap the query for any city and any business type. That's the whole product.

## What the verdicts mean

| Verdict | Evidence |
|---|---|
| **PASS** | Real mail system + live site + page matches the company name |
| **WEAK** | Partial evidence or contradictions (unresolvable DNS, dead site, social-page "website", title mismatch) |
| **FAIL** | Domain cannot receive mail (or does not exist) |

Every row carries its evidence columns: `mx_ok`, `site_live`, `http_status`,
`site_title`, `redirect_host`, `title_match`, plus a `qualify_flags` list
(`catch_all`, `no_linkedin`, `dns_error`, …). A catch-all domain accepts any
address, so a `CATCH_ALL` email is reported as such — never as verified.

## Providers

| Provider | Cost | Notes |
|---|---|---|
| `osm` (default) | free | OpenStreetMap via Overpass. No key. Coverage varies by region |
| `google_places` | ~$ per call | Your own Google Places API key (`GOOGLE_PLACES_API_KEY`) |

Keys go in your environment — nothing is hardcoded and no key is required for
the free path.

## Fair use & compliance

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
