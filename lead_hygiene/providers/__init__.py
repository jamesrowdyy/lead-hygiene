"""Discovery providers. The interface: search(query, country) -> list[dict].

Every provider returns rows with at least: company, domain, phone.
Optional: email, email_status, linkedin, headcount.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

UA = "lead-hygiene/0.1 (https://github.com/jamesrowdyy/lead-hygiene)"


class Provider:
    name = "base"

    def search(self, query: str, country: str = "US") -> list[dict]:
        raise NotImplementedError


class OSMProvider(Provider):
    """Free discovery via OpenStreetMap Overpass. No key, no cost.

    Honest limits: OSM coverage varies wildly by region and category, and OSM
    has no email or headcount data. Expect domains for maybe half the rows.
    """

    name = "osm"

    # plain-English term -> OSM tag filter (fallback: name regex)
    TAGS = {
        "coffee": '["amenity"="cafe"]', "cafe": '["amenity"="cafe"]',
        "restaurant": '["amenity"="restaurant"]', "bar": '["amenity"="bar"]',
        "pub": '["amenity"="pub"]', "bakery": '["shop"="bakery"]',
        "gym": '["leisure"="fitness_centre"]', "hairdresser": '["shop"="hairdresser"]',
        "plumber": '["craft"="plumber"]', "roofer": '["craft"="roofer"]',
        "electrician": '["craft"="electrician"]', "lawyer": '["office"="lawyer"]',
        "accountant": '["office"="accountant"]', "dentist": '["amenity"="dentist"]',
        "hotel": '["tourism"="hotel"]', "florist": '["shop"="florist"]',
    }

    def search(self, query: str, country: str = "US") -> list[dict]:
        term = query.split(" in ")[0].strip()
        area = query.split(" in ")[-1].strip() if " in " in query else country
        area_id = self._area_id(area)
        if not area_id:
            return []
        words = set(re.findall(r"\w+", term.lower()))
        tag = next((v for k, v in self.TAGS.items() if k in words),
                   f'["name"~"{re.escape(term)}",i]')
        q = (f'[out:json][timeout:60];area({area_id})->.a;'
             f'nwr{tag}[~"^($|contact:)website$"~"."](area.a);out center 200;')
        data = self._overpass(q)
        rows = []
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            website = tags.get("website") or tags.get("contact:website") or ""
            if not website:
                continue
            rows.append(
                {
                    "company": tags.get("name", ""),
                    "domain": urllib.parse.urlparse(
                        website if website.startswith("http") else "https://" + website
                    ).netloc,
                    "phone": tags.get("phone") or tags.get("contact:phone", ""),
                    "kind": tags.get("shop") or tags.get("office") or tags.get("amenity", ""),
                }
            )
        return rows

    def _area_id(self, area: str) -> int | None:
        """Geocode the area name via Nominatim, return an Overpass area id."""
        req = urllib.request.Request(
            "https://nominatim.openstreetmap.org/search?"
            + urllib.parse.urlencode({"q": area, "format": "json", "limit": 1}),
            headers={"User-Agent": UA},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            hits = json.loads(resp.read())
        if not hits:
            raise ValueError(f"no OSM area found for {area!r}")
        hit = hits[0]
        # Overpass area ids: relations 36e8+id, ways 24e8+id. Nodes are not areas.
        if hit["osm_type"] == "relation":
            return 3600000000 + int(hit["osm_id"])
        if hit["osm_type"] == "way":
            return 2400000000 + int(hit["osm_id"])
        raise ValueError(f"{area!r} resolved to a point, not an area; name it more precisely")

    MIRRORS = (
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    )

    def _overpass(self, ql: str) -> dict:
        last: Exception | None = None
        for url in self.MIRRORS:
            try:
                req = urllib.request.Request(
                    url,
                    data=urllib.parse.urlencode({"data": ql}).encode(),
                    headers={"User-Agent": UA},
                )
                with urllib.request.urlopen(req, timeout=90) as resp:
                    return json.loads(resp.read())
            except Exception as exc:  # try the next mirror
                last = exc
        raise last or RuntimeError("overpass failed")


class GooglePlacesProvider(Provider):
    """Your own Google Places API key. Text search, billed per call."""

    name = "google_places"

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GOOGLE_PLACES_API_KEY not set")
        self.key = api_key

    def search(self, query: str, country: str = "US") -> list[dict]:
        req = urllib.request.Request(
            "https://places.googleapis.com/v1/places:searchText",
            data=json.dumps(
                {"textQuery": query, "maxResultCount": 20}
            ).encode(),
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.key,
                "X-Goog-FieldMask": "places.displayName,places.websiteUri,"
                "places.internationalPhoneNumber",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        rows = []
        for p in data.get("places", []):
            site = p.get("websiteUri", "")
            rows.append(
                {
                    "company": p.get("displayName", {}).get("text", ""),
                    "domain": urllib.parse.urlparse(site).netloc if site else "",
                    "phone": p.get("internationalPhoneNumber", ""),
                }
            )
        return rows


PROVIDERS: dict[str, type[Provider]] = {
    OSMProvider.name: OSMProvider,
    GooglePlacesProvider.name: GooglePlacesProvider,
}


def get_provider(name: str, **creds) -> Provider:
    if name not in PROVIDERS:
        raise ValueError(f"unknown provider '{name}'. known: {', '.join(PROVIDERS)}")
    return PROVIDERS[name](**creds)
