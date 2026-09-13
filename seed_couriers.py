"""
Milestone 3: create simulated couriers, positioned near the real
restaurant distribution so the courier map looks like Monterrey rather
than a uniform random square.

Run:
    python seed_couriers.py
"""

import random
from datetime import datetime, timedelta, timezone

from hackmty_common import supabase

NUM_COURIERS = 100
VEHICLE_TYPES = ["bicycle", "motorcycle", "car"]
VEHICLE_WEIGHTS = [0.15, 0.55, 0.30]

# Jitter around the anchor restaurant, in degrees (~roughly 1-2 km)
JITTER_DEG = 0.015


def fetch_restaurant_coords():
    resp = supabase.table("restaurants").select("latitude, longitude").execute()
    rows = resp.data or []
    if not rows:
        raise RuntimeError(
            "No restaurants found. Run restaurant_data.py first so couriers "
            "can be distributed around real restaurant geography."
        )
    return [(r["latitude"], r["longitude"]) for r in rows]


def build_couriers(anchors):
    now = datetime.now(timezone.utc)
    shift_start = now
    shift_end = now + timedelta(hours=8)

    rows = []
    for _ in range(NUM_COURIERS):
        anchor_lat, anchor_lng = random.choice(anchors)
        lat = anchor_lat + random.uniform(-JITTER_DEG, JITTER_DEG)
        lng = anchor_lng + random.uniform(-JITTER_DEG, JITTER_DEG)
        vehicle_type = random.choices(VEHICLE_TYPES, weights=VEHICLE_WEIGHTS, k=1)[0]

        rows.append({
            "vehicle_type": vehicle_type,
            "current_lat": lat,
            "current_lng": lng,
            "shift_start": shift_start.isoformat(),
            "shift_end": shift_end.isoformat(),
            "time_budget_minutes": 480,
            "status": "available",
        })
    return rows


def main():
    anchors = fetch_restaurant_coords()
    rows = build_couriers(anchors)

    batch_size = 50
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        supabase.table("couriers").insert(batch).execute()
        print(f"Inserted couriers {i + 1}-{i + len(batch)}")

    print(f"Done. {len(rows)} couriers created.")


if __name__ == "__main__":
    main()
