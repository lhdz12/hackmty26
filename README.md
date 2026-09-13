# hackmty26 — cómo correr todo

## Estructura del proyecto (tal cual está, sin mover nada)

```
hackmty26/
├── .env                      # tus llaves reales (nunca se sube a git)
├── .env.example
├── requirements.txt
├── schema.sql                # tablas de Supabase
├── reset.sql                 # borra tablas si quedaron a medias
├── grant_permissions.sql     # arregla "permission denied" en Supabase
├── hackmty_common.py         # cliente de Supabase + utilidades compartidas
├── restaurant_data.py        # jala restaurantes reales de Google Places
├── seed_couriers.py          # crea couriers simulados
├── simulation.py             # genera pedidos (Poisson + exponencial)
├── routing.py                # Google Routes + caché en Supabase
├── weather.py                # snapshots de OpenWeather
├── scoring.py                # calcula el costo w_ko de cada pareja courier-pedido
├── assignment.py             # corre el algoritmo húngaro y explica cada match
├── api.py                    # API completa (dev/local) con todos los endpoints
└── app/
    ├── __init__.py
    └── main.py                # entry point que Render va a correr
```

## 1. Base de datos (una sola vez)

En Supabase → SQL Editor:
1. Corre `schema.sql` completo.
2. Si algo falla con "column does not exist", corre `reset.sql` y luego `schema.sql` de nuevo.
3. Si algo falla con "permission denied", corre `grant_permissions.sql`.

## 2. Entorno local

```bash
cd hackmty26
cp .env.example .env
# llena .env con tus llaves REALES (rotadas, nunca las que pegaste antes en el chat)
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

`.env` necesita:
```
SUPABASE_URL=...
SUPABASE_SECRET_KEY=...
GOOGLE_MAPS_API=...
OPENWEATHER_API_KEY=...
```

## 3. Poblar datos (en este orden, una vez)

```bash
python restaurant_data.py     # ~100-140 restaurantes reales de Monterrey
python seed_couriers.py       # 100 couriers simulados
python simulation.py --minutes 60 --seed 42   # genera ~2000 pedidos/hora simulados
python weather.py             # un snapshot del clima actual
```

## 4. Correr el algoritmo de asignación

```bash
python assignment.py
```

Esto imprime, por cada asignación:
- courier, tipo de vehículo, pedido
- tiempo real a la recogida y de la recogida a la entrega (Google Routes)
- tiempo total vs. el `time_budget_minutes` del courier
- payout y margen antes del deadline del restaurante

Al final muestra el total de couriers asignados y el payout total comprometido.

**Nota importante:** cada corrida asigna **un pedido por courier** (no hace bundling todavía). Si un courier fue asignado, cuenta como una entrega.

## 5. Levantar la API para el frontend

Para desarrollo local (todos los endpoints, incluyendo `/assignment/run`):
```bash
uvicorn api:app --reload --port 8000
```

Para lo que Render va a correr en producción:
```bash
uvicorn app.main:app --reload --port 8000
```

`app/main.py` importa y expone exactamente lo mismo que `api.py` (ver ese archivo
para la lista completa de endpoints). Ambos corren desde la carpeta `hackmty26/`
como directorio de trabajo — no cambies rutas ni muevas archivos.

## 6. Deploy en Render

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Root Directory:** `hackmty26`

**Environment Variables** (agrégalas en el dashboard de Render, NO en el repo):
```
SUPABASE_URL
SUPABASE_SECRET_KEY
GOOGLE_MAPS_API
OPENWEATHER_API_KEY
```

## Qué es real vs. simulado (para tu documentación del proyecto)

| Dato | Fuente |
|---|---|
| Nombre, ubicación, dirección, tipo, rating de restaurantes | Google Places (real) |
| Distancia y tiempo de ruta, tráfico | Google Routes (real) |
| Clima (temperatura, lluvia, viento, humedad) | OpenWeather (real) |
| Ubicación de couriers, tipo de vehículo | Simulado |
| Ubicación de clientes | Simulado (alrededor de restaurantes reales) |
| λ (llegada de pedidos) | Derivado de reviews reales + modelo documentado |
| μ (tiempo de preparación) | Derivado de un modelo por categoría de restaurante |
| Pedidos generados | Proceso de Poisson usando λ |
| Payout | Fórmula simulada (tarifa base + por km) |
