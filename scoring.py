"""
Builds the w_ko score for a (courier, order) candidate pair by combining:
- real travel time from Google Routes (via routing.py's cache)
- a weather multiplier (from the latest weather_snapshots row)
- deadline feasibility (can the courier realistically make it in time?)
- payout (higher payout -> more attractive)

Lower w_ko = better match (this is set up as a COST to minimize).
Tune the weights (ALPHA, BETA, GAMMA) to match your project's priorities.
"""

from datetime import datetime, timezone

from hackmty_common import supabase
from routing import get_route

# Weight of travel time vs payout in the final cost. Tune these.
ALPHA_TIME = 1.0        # cost per second of travel time
BETA_PAYOUT = -0.5       # negative because higher payout should LOWER cost
INFEASIBLE_COST = 1e9    # sentinel for pairs that can't work at all

WEATHER_MULTIPLIERS = {
    # vehicle_type -> multiplier applied to travel time when it's raining
    "bicycle": 1.30,
    "motorcycle": 1.15,
    "car": 1.05,
}


def get_latest_weather():
    resp = (
        supabase.table("weather_snapshots")
        .select("*")
        .order("observed_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None


def weather_multiplier(vehicle_type, weather_row):
    if not weather_row or not weather_row.get("rain"):
        return 1.0
    return WEATHER_MULTIPLIERS.get(vehicle_type, 1.0)


def score_pair(courier, order, weather_row, now=None):
    """
    Returns (cost, details) for assigning `courier` to `order`.
    cost = INFEASIBLE_COST if the courier cannot make the deadline OR
    the delivery would exceed the courier's remaining time budget.

    `now` defaults to the order's own created_at timestamp, not the real
    wall clock. Orders are generated in bulk by simulation.py with
    timestamps from when that script ran, so comparing against the actual
    current time later would make every order look "already late" purely
    because real time moved on -- not because the assignment is bad.

    `details` is returned for BOTH feasible and infeasible pairs so the
    caller can print a plain-language reason either way.
    """
    if now is None:
        now = datetime.fromisoformat(order["created_at"])

    courier_pos = (courier["current_lat"], courier["current_lng"])
    pickup_pos = (order["pickup_lat"], order["pickup_lng"])
    dropoff_pos = (order["dropoff_lat"], order["dropoff_lng"])

    to_pickup = get_route(courier_pos, pickup_pos, courier["vehicle_type"])
    pickup_to_dropoff = get_route(pickup_pos, dropoff_pos, courier["vehicle_type"])

    mult = weather_multiplier(courier["vehicle_type"], weather_row)

    time_to_pickup = to_pickup["traffic_duration_seconds"] * mult
    time_pickup_to_dropoff = pickup_to_dropoff["traffic_duration_seconds"] * mult
    total_time_seconds = time_to_pickup + time_pickup_to_dropoff
    total_time_minutes = total_time_seconds / 60.0

    ready_at = datetime.fromisoformat(order["ready_at"])
    deadline = datetime.fromisoformat(order["restaurant_deadline"])

    arrival_at_restaurant = now.timestamp() + time_to_pickup
    pickup_time = max(arrival_at_restaurant, ready_at.timestamp())
    delivery_time = pickup_time + time_pickup_to_dropoff
    deadline_margin_seconds = deadline.timestamp() - delivery_time

    base_details = {
        "courier_id": courier["id"],
        "vehicle_type": courier["vehicle_type"],
        "order_id": order["id"],
        "time_to_pickup_min": round(time_to_pickup / 60.0, 1),
        "time_pickup_to_dropoff_min": round(time_pickup_to_dropoff / 60.0, 1),
        "total_time_min": round(total_time_minutes, 1),
        "weather_multiplier": mult,
        "payout": float(order["payout"]),
        "time_budget_minutes": courier["time_budget_minutes"],
        "deadline_margin_min": round(deadline_margin_seconds / 60.0, 1),
    }

    if delivery_time > deadline.timestamp():
        return INFEASIBLE_COST, {**base_details, "reason": "misses_deadline"}

    if total_time_minutes > courier["time_budget_minutes"]:
        return INFEASIBLE_COST, {**base_details, "reason": "exceeds_time_budget"}

    payout = float(order["payout"])
    cost = ALPHA_TIME * total_time_seconds + BETA_PAYOUT * payout

    return cost, {**base_details, "reason": "feasible"}
