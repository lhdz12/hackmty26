import os
import requests
import googlemaps
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv()

api_key = os.getenv("GOOGLE_MAPS_API")

# Parámetros de la consulta
origen = "Monterrey,NL"
destino = "Cadereyta Jimenez,NL"

url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origen}&destinations={destino}&key={api_key}"

response = requests.get(url)
data = response.json()

# Extraer tiempo y distancia de la respuesta JSON
if data["status"] == "OK":
    element = data["rows"][0]["elements"][0]
    distancia = element["distance"]["text"]
    duracion = element["duration"]["text"]
    
    print(f"Distancia: {distancia}")
    print(f"Tiempo estimado: {duracion}")

# Inicializar cliente de Google Maps
gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API"))

# Obtener direcciones entre dos coordenadas o direcciones escritas
directions_result = gmaps.directions(
    "Tec de Monterrey, Monterrey, NL",
    "Parque Fundidora, Monterrey, NL",
    mode="driving"
)

# Extraer la distancia y duración de la primera ruta
leg = directions_result[0]["legs"][0]
print(f"De: {leg['start_address']}")
print(f"A: {leg['end_address']}")
print(f"Distancia: {leg['distance']['text']}")
print(f"Duración en tráfico: {leg['duration']['text']}")