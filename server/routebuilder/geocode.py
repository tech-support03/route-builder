"""Address -> coordinates via Nominatim (OpenStreetMap's geocoder).

Nominatim's usage policy asks for an identifying User-Agent and max 1 req/s;
fine for interactive personal use.
"""

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "route-builder/0.1 (personal running route tool)"}


class GeocodeError(Exception):
    pass


def geocode(query: str, limit: int = 5) -> list[dict]:
    """Return candidate matches: [{"label", "lat", "lon"}, ...] best first."""
    try:
        resp = httpx.get(
            NOMINATIM_URL,
            params={"q": query, "format": "jsonv2", "limit": limit},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise GeocodeError(f"Geocoding failed: {e}") from e
    return [
        {"label": r["display_name"], "lat": float(r["lat"]), "lon": float(r["lon"])}
        for r in resp.json()
    ]


def geocode_one(query: str) -> dict:
    results = geocode(query, limit=1)
    if not results:
        raise GeocodeError(f"No match found for address: {query!r}")
    return results[0]
