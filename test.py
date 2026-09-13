import os
import requests
from dotenv import load_dotenv
from supabase import create_client


# Load variables from .env
load_dotenv()

def test_supabase():
    try:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SECRET_KEY")

        if not url or not key:
            print("Supabase: ❌ missing credentials")
            return

        url = url.rstrip("/")

        if url.endswith("/rest/v1"):
            url = url[:-8]

        supabase = create_client(url, key)

        print("Supabase: works :)")

    except Exception as e:
        print(f"Supabase: ❌ {e}")

def test_google_maps():
    try:
        api_key = os.getenv("GOOGLE_MAPS_API")

        if not api_key:
            print("Google Maps: ❌ missing API key")
            return

        # Test Directions API with two locations.
        url = "https://maps.googleapis.com/maps/api/directions/json"

        params = {
            "origin": "Monterrey, Mexico",
            "destination": "San Pedro Garza Garcia, Mexico",
            "key": api_key,
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get("status") == "OK":
            print("Google Maps: works :)")
        else:
            print(f"Google Maps: ❌ {data.get('status')}")
            print(f"Details: {data.get('error_message', 'No additional information')}")

    except Exception as e:
        print(f"Google Maps: ❌ {e}")


def test_openweather():
    try:
        api_key = os.getenv("OPENWEATHER_API_KEY")

        if not api_key:
            print("OpenWeather: ❌ missing API key")
            return

        # Monterrey coordinates
        url = "https://api.openweathermap.org/data/2.5/weather"

        params = {
            "lat": 25.6866,
            "lon": -100.3161,
            "appid": api_key,
            "units": "metric",
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if response.status_code == 200:
            print("OpenWeather: works :)")
        else:
            print(f"OpenWeather: ❌ {response.status_code}")
            print(f"Details: {data}")

    except Exception as e:
        print(f"OpenWeather: ❌ {e}")


print("\n==============================")
print("   API CONNECTION TEST")
print("==============================\n")

test_supabase()
test_google_maps()
test_openweather()

print("\n==============================")