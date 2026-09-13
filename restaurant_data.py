"""
Milestone 2: pull real Monterrey restaurants from Google Places (New) API,
deduplicate by place id, derive lambda_per_hour (demand) and mu_per_hour
(service rate) from real signals + a documented model, then upsert into
the Supabase `restaurants` table.

Run:
    python restaurant_data.py
"""

import math
import time
import requests

from hackmty_common import (
    supabase,
    GOOGLE_MAPS_API,
    MONTERREY_ZONES,
    prep_time_minutes_for_type,
)

PLACES_URL = "https://places.googleapis.com/v1/places:searchNearby"
FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.location,"
    "places.formattedAddress,"
    "places.primaryType,"
    "places.rating,"
    "places.userRatingCount,"
    "places.currentOpeningHours.openNow"
)

TARGET_TOTAL_LAMBDA = 2000.0  # sum of lambda_i across all restaurants, orders/hour
RADIUS_METERS = 3000
MAX_RESULTS_PER_ZONE = 20  # Google's Nearby Search cap


def fetch_zone(lat, lng):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    payload = {
        "includedTypes": ["restaurant"],
        "maxResultCount": MAX_RESULTS_PER_ZONE,
        "rankPreference": "POPULARITY",
        "locationRestriction": {
            "circle": {"center": {"latitude": lat, "longitude": lng}, "radius": RADIUS_METERS}
        },
        "regionCode": "MX",
    }
    resp = requests.post(PLACES_URL, headers=headers, json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json().get("places", [])


def collect_all_restaurants():
    by_place_id = {}
    for zone_name, (lat, lng) in MONTERREY_ZONES.items():
        print(f"Searching zone: {zone_name} ...")
        try:
            places = fetch_zone(lat, lng)
        except requests.HTTPError as e:
            print(f"  Zone {zone_name} failed: {e}")
            continue
        for place in places:
            by_place_id[place["id"]] = place  # dedupe across zones
        time.sleep(0.2)  # be gentle with the API
    return list(by_place_id.values())


def build_rows(places):
    # Popularity proxy: log(1 + review_count), normalized to sum to 1
    popularity = []
    for p in places:
        reviews = p.get("userRatingCount", 0) or 0
        popularity.append(math.log(1 + reviews))

    total_pop = sum(popularity) or 1.0

    rows = []
    for place, pop in zip(places, popularity):
        location = place["location"]
        restaurant_type = place.get("primaryType", "restaurant")

        share = pop / total_pop
        lambda_i = max(TARGET_TOTAL_LAMBDA * share, 1.0)  # floor so nobody gets 0

        prep_minutes = prep_time_minutes_for_type(restaurant_type)
        mu_i = 60.0 / prep_minutes

        rows.append({
            "google_place_id": place["id"],
            "name": place["displayName"]["text"],
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "address": place.get("formattedAddress"),
            "restaurant_type": restaurant_type,
            "rating": place.get("rating"),
            "user_rating_count": place.get("userRatingCount"),
            "is_open_now": place.get("currentOpeningHours", {}).get("openNow"),
            "lambda_per_hour": round(lambda_i, 4),
            "mu_per_hour": round(mu_i, 4),
        })
    return rows


def main():
    places = collect_all_restaurants()
    print(f"Collected {len(places)} unique restaurants across all zones.")

    if not places:
        print("No restaurants found. Check your Google Maps API key/quota.")
        return

    rows = build_rows(places)

    # Supabase upsert in batches to stay well under request size limits
    batch_size = 50
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        supabase.table("restaurants").upsert(batch, on_conflict="google_place_id").execute()
        print(f"Upserted restaurants {i + 1}-{i + len(batch)}")

    total_lambda = sum(r["lambda_per_hour"] for r in rows)
    print(f"Done. {len(rows)} restaurants inserted/updated. "
          f"Sum of lambda_per_hour = {total_lambda:.1f} (target {TARGET_TOTAL_LAMBDA}).")


if __name__ == "__main__":
    main()
