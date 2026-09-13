"""
Shared helpers used by every script in this project:
- one Supabase client
- the 10 Monterrey zones used to spatially distribute restaurant search
- small geo utilities used by the simulation (sampling a customer point
  at some distance/direction from a restaurant)
"""

import os
import math
import random
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
GOOGLE_MAPS_API = os.getenv("GOOGLE_MAPS_API")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise RuntimeError(
        "Missing SUPABASE_URL / SUPABASE_SECRET_KEY. "
        "Copy .env.example to .env and fill in your (rotated) keys."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

# Approximate centers of 10 Monterrey zones (lat, lng).
# Good enough to spatially spread Nearby Search calls; not survey-grade.
MONTERREY_ZONES = {
    "Centro":        (25.6714, -100.3097),
    "Obispado":      (25.6822, -100.3401),
    "San Jeronimo":  (25.6377, -100.3706),
    "San Pedro":     (25.6510, -100.4029),
    "Valle Oriente": (25.6187, -100.3559),
    "Del Valle":     (25.6522, -100.3833),
    "Tec":           (25.6514, -100.2895),
    "Contry":        (25.6289, -100.2814),
    "Cumbres":       (25.7346, -100.3661),
    "Mitras":        (25.6889, -100.3475),
}

# Rough prep-time ranges (minutes) by restaurant category, used only to
# derive a *model* mu, not claimed as measured real data.
PREP_TIME_MINUTES_BY_TYPE = {
    "fast_food_restaurant": (5, 10),
    "cafe": (4, 8),
    "coffee_shop": (4, 8),
    "bakery": (4, 8),
    "pizza_restaurant": (10, 20),
    "mexican_restaurant": (10, 20),
    "fine_dining_restaurant": (20, 35),
    "restaurant": (8, 18),  # generic fallback bucket
}
DEFAULT_PREP_RANGE = (8, 18)


def prep_time_minutes_for_type(restaurant_type: str) -> float:
    """Sample an expected prep time (minutes) for a restaurant category."""
    lo, hi = PREP_TIME_MINUTES_BY_TYPE.get(restaurant_type, DEFAULT_PREP_RANGE)
    return random.uniform(lo, hi)


def offset_latlng(lat, lng, distance_km, bearing_deg):
    """
    Move (lat, lng) by distance_km in direction bearing_deg (0 = north,
    clockwise). Used to sample a synthetic customer location around a
    real restaurant.
    """
    R = 6371.0  # Earth radius km
    bearing = math.radians(bearing_deg)
    lat1 = math.radians(lat)
    lng1 = math.radians(lng)

    lat2 = math.asin(
        math.sin(lat1) * math.cos(distance_km / R)
        + math.cos(lat1) * math.sin(distance_km / R) * math.cos(bearing)
    )
    lng2 = lng1 + math.atan2(
        math.sin(bearing) * math.sin(distance_km / R) * math.cos(lat1),
        math.cos(distance_km / R) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lng2)


def sample_customer_location(rest_lat, rest_lng):
    """Sample a synthetic customer location within a plausible delivery radius."""
    bucket = random.choices(
        ["short", "medium", "long"], weights=[0.5, 0.35, 0.15], k=1
    )[0]
    ranges = {"short": (1, 3), "medium": (3, 7), "long": (7, 12)}
    lo, hi = ranges[bucket]
    distance_km = random.uniform(lo, hi)
    bearing_deg = random.uniform(0, 360)
    return offset_latlng(rest_lat, rest_lng, distance_km, bearing_deg)
