"""
Milestone 6: fetch current weather for Monterrey and store a snapshot.
Meant to be run every 5-10 minutes (cron, loop, or scheduled task), not
per-order.

Run once:
    python weather.py

Run continuously every 5 minutes:
    python weather.py --loop
"""

import argparse
import time
import requests
from datetime import datetime, timezone

from hackmty_common import supabase, OPENWEATHER_API_KEY

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

MONTERREY_CENTER = (25.6866, -100.3161)
RAIN_KEYWORDS = {"rain", "drizzle", "thunderstorm"}


def fetch_weather(lat, lng):
    params = {
        "lat": lat,
        "lon": lng,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    }
    resp = requests.get(WEATHER_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def store_snapshot(lat, lng, data):
    weather_main = data["weather"][0]["main"]
    weather_description = data["weather"][0]["description"]
    rain_mm = data.get("rain", {}).get("1h", 0.0)

    row = {
        "latitude": lat,
        "longitude": lng,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "temperature_c": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "wind_speed_mps": data["wind"]["speed"],
        "precipitation_mm": rain_mm,
        "weather_main": weather_main,
        "weather_description": weather_description,
        "rain": weather_main.lower() in RAIN_KEYWORDS,
    }
    supabase.table("weather_snapshots").insert(row).execute()
    print(f"Stored weather snapshot: {weather_main} ({weather_description}), "
          f"{row['temperature_c']}C, rain={row['rain']}")


def run_once():
    lat, lng = MONTERREY_CENTER
    data = fetch_weather(lat, lng)
    store_snapshot(lat, lng, data)


def run_loop(interval_seconds=300):
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"Weather fetch failed: {e}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true", help="Run continuously every 5 minutes")
    parser.add_argument("--interval", type=int, default=300, help="Loop interval in seconds")
    args = parser.parse_args()

    if args.loop:
        run_loop(args.interval)
    else:
        run_once()
