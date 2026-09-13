"""
Milestone 4: generate orders using a per-restaurant Poisson arrival
process and exponential prep times, anchored to real restaurant
locations with synthetic customer locations.

This models each restaurant i as an M/M/1-style queue:
    arrivals ~ Poisson(lambda_i * dt)
    prep time ~ Exponential(mu_i)

Run:
    python simulation.py --minutes 60
"""

import argparse
import random
import uuid
from datetime import datetime, timedelta, timezone

import numpy as np

from hackmty_common import supabase, sample_customer_location

BASE_FARE = 25.0          # MXN, flat component
PER_KM_RATE = 6.0         # MXN per km (straight-line proxy; refine with Routes later)
DEADLINE_BUFFER_MINUTES = 12  # time allowed after food is ready before it's "late"


def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lng2 - lng1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlambda / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def fetch_restaurants():
    resp = supabase.table("restaurants").select(
        "id, latitude, longitude, lambda_per_hour, mu_per_hour"
    ).execute()
    rows = resp.data or []
    if not rows:
        raise RuntimeError("No restaurants found. Run restaurant_data.py first.")
    return rows


def make_order(restaurant, created_at, simulation_id):
    rest_lat, rest_lng = restaurant["latitude"], restaurant["longitude"]
    mu = restaurant["mu_per_hour"]

    customer_lat, customer_lng = sample_customer_location(rest_lat, rest_lng)

    # Prep time ~ Exponential(mu), mu is orders/hour -> mean prep = 60/mu minutes
    prep_minutes = float(np.random.exponential(60.0 / mu))
    ready_at = created_at + timedelta(minutes=prep_minutes)
    deadline = ready_at + timedelta(minutes=DEADLINE_BUFFER_MINUTES)

    distance_km = float(haversine_km(rest_lat, rest_lng, customer_lat, customer_lng))
    payout = round(BASE_FARE + PER_KM_RATE * distance_km, 2)

    return {
        "restaurant_id": restaurant["id"],
        "pickup_lat": rest_lat,
        "pickup_lng": rest_lng,
        "dropoff_lat": customer_lat,
        "dropoff_lng": customer_lng,
        "created_at": created_at.isoformat(),
        "ready_at": ready_at.isoformat(),
        "restaurant_deadline": deadline.isoformat(),
        "payout": payout,
        "estimated_prep_minutes": round(prep_minutes, 2),
        "status": "open",
        "created_simulation_id": simulation_id,
    }


def run_simulation(duration_minutes, seed=None):
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    restaurants = fetch_restaurants()
    target_total_lambda = sum(r["lambda_per_hour"] for r in restaurants)

    simulation_start = datetime.now(timezone.utc)
    simulation_id = str(uuid.uuid4())

    supabase.table("simulations").insert({
        "id": simulation_id,
        "simulation_start": simulation_start.isoformat(),
        "duration_minutes": duration_minutes,
        "number_of_couriers": len(supabase.table("couriers").select("id").execute().data or []),
        "number_of_restaurants": len(restaurants),
        "target_orders_per_hour": target_total_lambda,
        "random_seed": seed,
    }).execute()

    all_orders = []
    for minute in range(duration_minutes):
        timestamp = simulation_start + timedelta(minutes=minute)
        minute_total = 0
        for restaurant in restaurants:
            lam = restaurant["lambda_per_hour"] / 60.0  # per-minute rate
            n_orders = np.random.poisson(lam)
            minute_total += n_orders
            for _ in range(n_orders):
                all_orders.append(make_order(restaurant, timestamp, simulation_id))
        print(f"minute {minute:02d} -> {minute_total} orders (running total {len(all_orders)})")

    # Insert in batches
    batch_size = 200
    for i in range(0, len(all_orders), batch_size):
        batch = all_orders[i:i + batch_size]
        supabase.table("orders").insert(batch).execute()
        print(f"Inserted orders {i + 1}-{i + len(batch)}")

    print(f"Done. Simulation {simulation_id} generated {len(all_orders)} orders "
          f"over {duration_minutes} minutes (target rate {target_total_lambda:.1f}/hour).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=int, default=60, help="Simulation duration in minutes")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = parser.parse_args()

    run_simulation(args.minutes, args.seed)
