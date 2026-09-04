"""
Client for a self-hosted OSRM (Open Source Routing Machine) server.

We request `alternatives=true` so OSRM gives us more than one geometrically
distinct candidate route between origin and destination. The risk engine
then scores each candidate and we present the best-by-time, best-by-risk,
and best-compromise options as Fastest / Balanced / Safest.

If fewer than 2 alternatives come back (common on sparse OSM extracts,
e.g. a small self-hosted area), we still return what we have — the API
degrades gracefully rather than failing the whole request.
"""
from __future__ import annotations

import httpx

from app.config import settings


class OSRMError(Exception):
    pass


async def get_candidate_routes(
    origin_lat: float, origin_lng: float,
    dest_lat: float, dest_lng: float,
    max_alternatives: int = 3,
) -> list[dict]:
    """
    Returns a list of route dicts, each containing:
      - geometry (encoded polyline, precision 6)
      - distance_m
      - duration_s
    """
    coords = f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
    url = f"{settings.osrm_base_url}/route/v1/driving/{coords}"
    params = {
        "alternatives": "true",
        "steps": "false",
        "geometries": "polyline6",
        "overview": "full",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise OSRMError(f"OSRM request failed: {e}") from e

    data = resp.json()
    if data.get("code") != "Ok":
        raise OSRMError(f"OSRM returned error code: {data.get('code')} — {data.get('message', '')}")

    routes = []
    for r in data.get("routes", [])[:max_alternatives]:
        routes.append({
            "geometry": r["geometry"],
            "distance_m": r["distance"],
            "duration_s": r["duration"],
        })
    return routes
