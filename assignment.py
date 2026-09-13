"""
Milestone 7: the actual assignment step.

1. Fetch open orders and available couriers.
2. Cheaply filter candidates (straight-line distance) before calling
   Google Routes, so we don't compute the full couriers x orders matrix.
3. Score remaining candidates with scoring.score_pair (real travel time +
   weather + deadline feasibility + payout).
4. Solve the assignment with the Hungarian algorithm (scipy).
5. Write results to `assignments`, flip order/courier status.

Run:
    python assignment.py
"""

import math
from datetime import datetime, timezone

import numpy as np
from scipy.optimize import linear_sum_assignment

from hackmty_common import supabase
from scoring import score_pair, get_latest_weather, INFEASIBLE_COST

MAX_CANDIDATES_PER_COURIER = 8   # pre-filter cutoff before calling Routes (was 20 — too many API calls)
PREFILTER_RADIUS_KM = 6.0        # ignore orders way outside this straight-line range
MAX_OPEN_ORDERS_TO_CONSIDER = 150  # cap for a single assignment run; raise once things are fast


def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def fetch_open_orders():
    # Order by soonest deadline first and cap the count -- with hundreds/
    # thousands of open orders, scoring all of them against every courier
    # means thousands of real Google Routes calls per run.
    resp = (
        supabase.table("orders")
        .select("*")
        .eq("status", "open")
        .order("restaurant_deadline")
        .limit(MAX_OPEN_ORDERS_TO_CONSIDER)
        .execute()
    )
    return resp.data or []


def fetch_available_couriers():
    resp = supabase.table("couriers").select("*").eq("status", "available").execute()
    return resp.data or []


def prefilter_candidates(courier, orders):
    """Cheap straight-line distance filter before spending Routes API calls."""
    scored = []
    for order in orders:
        d = haversine_km(
            courier["current_lat"], courier["current_lng"],
            order["pickup_lat"], order["pickup_lng"],
        )
        if d <= PREFILTER_RADIUS_KM:
            scored.append((d, order))
    scored.sort(key=lambda x: x[0])
    return [o for _, o in scored[:MAX_CANDIDATES_PER_COURIER]]


def build_cost_matrix(couriers, orders, weather_row):
    """
    Returns:
    - cost_matrix: (num_couriers x num_orders) matrix for the Hungarian solver
    - details_lookup: {(courier_idx, order_idx): details_dict} for EVERY
      candidate pair considered, so committed assignments can be explained
      afterward without recomputing anything.
    """
    cost_matrix = np.full((len(couriers), len(orders)), INFEASIBLE_COST)
    details_lookup = {}
    order_index = {order["id"]: j for j, order in enumerate(orders)}

    for i, courier in enumerate(couriers):
        candidates = prefilter_candidates(courier, orders)
        for order in candidates:
            j = order_index[order["id"]]
            # now=None -> score_pair anchors to this order's own created_at
            cost, details = score_pair(courier, order, weather_row, now=None)
            cost_matrix[i, j] = cost
            details_lookup[(i, j)] = details
        print(f"  scored courier {i + 1}/{len(couriers)} "
              f"({len(candidates)} candidates)", flush=True)

    return cost_matrix, details_lookup


def solve_assignment(cost_matrix):
    """Hungarian algorithm. Returns list of (courier_idx, order_idx) pairs
    that are actually feasible (cost < INFEASIBLE_COST)."""
    row_idx, col_idx = linear_sum_assignment(cost_matrix)
    pairs = []
    for i, j in zip(row_idx, col_idx):
        if cost_matrix[i, j] < INFEASIBLE_COST:
            pairs.append((i, j))
    return pairs


def commit_assignments(couriers, orders, pairs, details_lookup):
    print("\n" + "=" * 70)
    print(f"{'COURIER':<10}{'VEHICLE':<12}{'ORDER':<10}{'TO PICKUP':<12}"
          f"{'PICKUP->DROP':<14}{'TOTAL':<10}{'BUDGET':<10}{'PAYOUT':<10}{'MARGIN'}")
    print("=" * 70)

    for courier_idx, order_idx in pairs:
        courier = couriers[courier_idx]
        order = orders[order_idx]
        d = details_lookup[(courier_idx, order_idx)]

        print(
            f"{courier['id'][:8]:<10}"
            f"{d['vehicle_type']:<12}"
            f"{order['id'][:8]:<10}"
            f"{d['time_to_pickup_min']:>6.1f} min "
            f"{d['time_pickup_to_dropoff_min']:>8.1f} min "
            f"{d['total_time_min']:>6.1f} min "
            f"{d['time_budget_minutes']:>6} min "
            f"${d['payout']:>6.2f} "
            f"{d['deadline_margin_min']:>6.1f} min"
        )

        supabase.table("assignments").insert({
            "order_id": order["id"],
            "courier_id": courier["id"],
            "sequence": 1,
            "status": "active",
        }).execute()

        supabase.table("orders").update({"status": "claimed"}).eq("id", order["id"]).execute()
        supabase.table("couriers").update({"status": "busy"}).eq("id", courier["id"]).execute()

    print("=" * 70)
    print(f"TOTAL: {len(pairs)} couriers assigned -> {len(pairs)} deliveries committed "
          f"(1 order per courier per run).")
    if pairs:
        total_payout = sum(details_lookup[p]["payout"] for p in pairs)
        avg_time = sum(details_lookup[p]["total_time_min"] for p in pairs) / len(pairs)
        print(f"Total payout committed: ${total_payout:.2f} | "
              f"Average delivery time: {avg_time:.1f} min")
    print("=" * 70 + "\n")


def main():
    orders = fetch_open_orders()
    couriers = fetch_available_couriers()

    print(f"{len(orders)} open orders, {len(couriers)} available couriers.")
    if not orders or not couriers:
        print("Nothing to assign right now.")
        return

    weather_row = get_latest_weather()
    cost_matrix, details_lookup = build_cost_matrix(couriers, orders, weather_row)

    pairs = solve_assignment(cost_matrix)
    print(f"Found {len(pairs)} feasible assignments out of "
          f"{min(len(couriers), len(orders))} possible.")

    commit_assignments(couriers, orders, pairs, details_lookup)


if __name__ == "__main__":
    main()
