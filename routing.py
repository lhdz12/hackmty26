"""
Milestone 5: real road distance/duration via Google Routes API, backed
by the route_cache table so repeated courier-order pairs don't re-bill.

Use get_route(origin, destination, vehicle_type) from your assignment
code. Running this file directly does a small self-test.
"""

import requests
from datetime import datetime, timezone

from hackmty_common import supabase, GOOGLE_MAPS_API

ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

# Reuse one TCP/TLS connection across all calls instead of reconnecting
# from scratch every time (that reconnect overhead is what made this look
# like it was hanging).
_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
_session.mount("https://", _adapter)

# Google Routes travel modes
VEHICLE_TO_TRAVEL_MODE = {
    "bicycle": "BICYCLE",
    "motorcycle": "TWO_WHEELER",
    "car": "DRIVE",
}

CACHE_LOOKUP_TOLERANCE = 0.0003  # ~30m, treat near-identical coords as cache hits


def _cache_lookup(origin_lat, origin_lng, dest_lat, dest_lng, vehicle_type):
    resp = (
        supabase.table("route_cache")
        .select("*")
        .eq("vehicle_type", vehicle_type)
        .gte("origin_lat", origin_lat - CACHE_LOOKUP_TOLERANCE)
        .lte("origin_lat", origin_lat + CACHE_LOOKUP_TOLERANCE)
        .gte("origin_lng", origin_lng - CACHE_LOOKUP_TOLERANCE)
        .lte("origin_lng", origin_lng + CACHE_LOOKUP_TOLERANCE)
        .gte("destination_lat", dest_lat - CACHE_LOOKUP_TOLERANCE)
        .lte("destination_lat", dest_lat + CACHE_LOOKUP_TOLERANCE)
        .gte("destination_lng", dest_lng - CACHE_LOOKUP_TOLERANCE)
        .lte("destination_lng", dest_lng + CACHE_LOOKUP_TOLERANCE)
        .order("calculated_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None


# routingPreference (traffic-aware routing) is only valid for DRIVE and
# TWO_WHEELER. Sending it with BICYCLE or WALK returns a 400 from Google.
TRAVEL_MODES_SUPPORTING_TRAFFIC = {"DRIVE", "TWO_WHEELER"}


def _call_google_routes(origin_lat, origin_lng, dest_lat, dest_lng, vehicle_type):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.staticDuration",
    }
    travel_mode = VEHICLE_TO_TRAVEL_MODE.get(vehicle_type, "DRIVE")

    payload = {
        "origin": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lng}}},
        "destination": {"location": {"latLng": {"latitude": dest_lat, "longitude": dest_lng}}},
        "travelMode": travel_mode,
    }
    if travel_mode in TRAVEL_MODES_SUPPORTING_TRAFFIC:
        payload["routingPreference"] = "TRAFFIC_AWARE"

    resp = _session.post(ROUTES_URL, headers=headers, json=payload, timeout=10)
    if not resp.ok:
        # Surface Google's actual error message instead of a bare 400
        print(f"Routes API error ({resp.status_code}) for vehicle_type={vehicle_type}: {resp.text}")
    resp.raise_for_status()
    data = resp.json()
    route = data["routes"][0]

    def parse_duration(s):
        # Google returns durations like "123s"
        return float(s.rstrip("s")) if s else None

    base_duration = parse_duration(route.get("duration"))
    static_duration = parse_duration(route.get("staticDuration"))

    # For non-traffic modes (e.g. bicycle) Google only returns "duration" and
    # omits "staticDuration" entirely. Fall back so both fields are populated.
    return {
        "distance_meters": route.get("distanceMeters"),
        "duration_seconds": static_duration if static_duration is not None else base_duration,
        "traffic_duration_seconds": base_duration,
    }


def get_route(origin, destination, vehicle_type="motorcycle"):
    """
    origin, destination: (lat, lng) tuples
    Returns dict: distance_meters, duration_seconds, traffic_duration_seconds
    Checks route_cache first; calls Google Routes and stores the result on a miss.
    """
    origin_lat, origin_lng = origin
    dest_lat, dest_lng = destination

    cached = _cache_lookup(origin_lat, origin_lng, dest_lat, dest_lng, vehicle_type)
    if cached:
        return {
            "distance_meters": cached["distance_meters"],
            "duration_seconds": cached["duration_seconds"],
            "traffic_duration_seconds": cached["traffic_duration_seconds"],
            "source": "cache",
        }

    result = _call_google_routes(origin_lat, origin_lng, dest_lat, dest_lng, vehicle_type)

    supabase.table("route_cache").insert({
        "origin_lat": origin_lat,
        "origin_lng": origin_lng,
        "destination_lat": dest_lat,
        "destination_lng": dest_lng,
        "vehicle_type": vehicle_type,
        "distance_meters": result["distance_meters"],
        "duration_seconds": result["duration_seconds"],
        "traffic_duration_seconds": result["traffic_duration_seconds"],
        "provider": "google_routes",
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    result["source"] = "google_routes"
    return result


if __name__ == "__main__":
    # Self-test: two points in Centro, Monterrey
    origin = (25.6714, -100.3097)
    destination = (25.6822, -100.3401)
    print(get_route(origin, destination, "motorcycle"))
    print(get_route(origin, destination, "motorcycle"))  # second call should hit cache
