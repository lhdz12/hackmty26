"""
Thin API layer between Supabase/your Python logic and the frontend.
The frontend should call THIS, not Supabase directly (keeps your secret
key server-side only, and lets you shape the response for the map UI).

Run:
    uvicorn api:app --reload --port 8000

Endpoints:
    GET  /state                -> everything the map needs in one call
    GET  /orders/open          -> just open orders
    GET  /couriers             -> all couriers with current status
    GET  /assignments/active   -> active assignments (for drawing lines)
    POST /assignment/run       -> triggers assignment.py's logic once
    GET  /weather/latest       -> latest weather snapshot
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hackmty_common import supabase
from scoring import get_latest_weather
import assignment as assignment_module

app = FastAPI(title="hackmty26 API")

# Allow your frontend dev server to call this. Tighten this before deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/orders/open")
def get_open_orders():
    resp = supabase.table("orders").select("*").eq("status", "open").execute()
    return resp.data or []


@app.get("/couriers")
def get_couriers():
    resp = supabase.table("couriers").select("*").execute()
    return resp.data or []


@app.get("/restaurants")
def get_restaurants():
    resp = supabase.table("restaurants").select("*").execute()
    return resp.data or []


@app.get("/assignments/active")
def get_active_assignments():
    resp = supabase.table("assignments").select("*").eq("status", "active").execute()
    return resp.data or []


@app.get("/weather/latest")
def weather_latest():
    return get_latest_weather() or {}


@app.get("/state")
def get_state():
    """Single call the frontend can poll (e.g. every 5s) to redraw the map."""
    return {
        "restaurants": get_restaurants(),
        "couriers": get_couriers(),
        "open_orders": get_open_orders(),
        "active_assignments": get_active_assignments(),
        "weather": weather_latest(),
    }


@app.post("/assignment/run")
def run_assignment():
    orders = assignment_module.fetch_open_orders()
    couriers = assignment_module.fetch_available_couriers()

    if not orders or not couriers:
        return {"assigned": 0, "message": "No open orders or available couriers."}

    weather_row = get_latest_weather()
    cost_matrix, details_lookup = assignment_module.build_cost_matrix(couriers, orders, weather_row)
    pairs = assignment_module.solve_assignment(cost_matrix)
    assignment_module.commit_assignments(couriers, orders, pairs, details_lookup)

    return {
        "assigned": len(pairs),
        "details": [details_lookup[p] for p in pairs],
    }
