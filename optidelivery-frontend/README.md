# OptiDelivery — frontend

App del courier para el proyecto de HackMTY. Next.js + JavaScript plano,
mobile-first, paleta azul según `FRONTEND_BRIEF.md`. Pensada para verse en
un celular en la calle: botones grandes, poco texto, cero formularios.

## Estructura

```
optidelivery-frontend/
├── components/
│   ├── Header.jsx          # barra superior: marca, clima, chip de courier
│   ├── WeatherBadge.jsx     # badge de clima (sin llamar a un endpoint extra)
│   ├── CourierPicker.jsx    # selector de courier simulado (no hay login real aún)
│   ├── BottomNav.jsx        # tabs inferiores: Pedidos / Ganancias
│   ├── OrderCard.jsx        # tarjeta de pedido abierto
│   ├── StatusStepper.jsx    # pasos de la entrega activa
│   └── RouteMap.jsx         # mapa embebido o link a Google Maps
├── lib/
│   ├── api.js               # cliente para el backend FastAPI
│   ├── courier.js           # localStorage: courier seleccionado
│   └── earnings.js          # localStorage: historial de entregas completadas
├── pages/
│   ├── _app.js              # shell de la app + selector de courier
│   ├── _document.js         # fuente Inter
│   ├── index.js             # Home: pedidos abiertos + banner de entrega activa
│   ├── summary.js           # Ganancias
│   └── delivery/[id].js     # Entrega activa: mapa + pasos
└── styles/globals.css
```

## Cómo correr en local

```bash
cd optidelivery-frontend
cp .env.local.example .env.local
# edita .env.local con la URL de tu backend
npm install
npm run dev
```

Abre `http://localhost:3000`. Necesitas el backend (`hackmty26`) corriendo
en paralelo, normalmente en `http://localhost:8000` con:

```bash
uvicorn api:app --reload --port 8000
```

## Login

El login es real, con **Supabase Auth** (email + contraseña) y la tabla
`user_profiles` de `login_schema.sql`. Flujo:

1. `AuthGate` (pantalla de "Entrar" / "Crear cuenta") — al crear cuenta pide
   nombre, apellido, edad y **tipo de vehículo** (bici/moto/carro), y los
   manda como `user metadata` en `supabase.auth.signUp(...)`. El trigger
   `handle_new_user` (ya en tu SQL) crea la fila en `user_profiles` solo.
2. En cuanto hay sesión, `_app.js` busca en `GET /couriers` (el backend) una
   fila con `user_id` igual al usuario logueado.
   - **Si no existe todavía, la crea automáticamente** — inserta una fila
     nueva en `couriers` con `user_id`, el `vehicle_type` elegido al
     registrarse, `status: "available"` y una ubicación inicial (Monterrey).
     Así tu vehículo y tu `courier_id` quedan ligados a tu correo desde el
     primer login, sin tener que elegir de una lista.
   - Si ese insert falla por algo (p. ej. tu tabla `couriers` real exige
     alguna columna extra que no le mandamos), cae como respaldo a
     `CourierLinkGate`: una pantalla que muestra el error y deja elegir a
     mano un courier simulado que siga sin dueño, para no bloquear la demo.
3. `summary.js` trae `total_earnings`, `completed_deliveries`,
   `total_minutes_worked` y `late_deliveries` directo de `user_profiles`,
   actualizados automáticamente por el trigger
   `handle_assignment_completed` de tu SQL cuando una asignación pasa a
   `completed`.
4. El botón de "Salir" en el header hace `supabase.auth.signOut()`.

**Una cosa que te toca a ti, no al frontend:** el backend necesita
**incluir `user_id` en la respuesta de `GET /couriers`** (y en `GET
/state`) para que `_app.js` pueda reconocer, en logins futuros, cuál
courier ya está ligado a cada usuario. Si esa columna no viaja en el JSON,
la creación automática funciona, pero el frontend va a intentar crear un
courier nuevo cada vez que entres (deja duplicados). Revisa esto antes de
la demo final.

También ten en cuenta: `couriers` no tiene RLS habilitado en
`login_schema.sql` (solo `user_profiles` lo tiene). Eso significa que,
tal como está, cualquier usuario logueado con la anon key podría escribir
sobre cualquier fila de `couriers` — para el hackatón está bien, pero antes
de producción real conviene una policy que solo permita `insert`/`update`
cuando la fila es la propia (`user_id = auth.uid()` o `user_id is null`).

## Elegir una ruta puntual

En Home, cada tarjeta de pedido abierto (solo aparecen los que siguen
**disponibles en ese momento** — `open_orders` ya viene filtrado así desde
`GET /state`) tiene un botón "Elegir esta ruta". Al tocarlo:

1. Primero intenta `POST /orders/{id}/accept` (aceptación puntual), por si
   ya lo agregaste al backend.
2. Si ese endpoint no existe todavía, cae al único mecanismo real de hoy —
   `POST /assignment/run` (el algoritmo húngaro global) — y le avisa con
   honestidad al courier si le tocó justo la ruta que eligió o una
   distinta. Esto es intencional: el frontend nunca finge que "elegiste"
   algo que el backend no te dio.
3. Mientras el courier ya tiene una entrega activa, los botones de elegir
   ruta y "Buscar asignación" se deshabilitan (el backend solo asigna un
   pedido por courier a la vez).

Cuando exista un endpoint real de aceptación puntual, el paso 2 deja de
usarse solo — no hay que tocar nada más de la pantalla.

## Variables de entorno

| Variable | Requerida | Qué hace |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Sí | URL base del backend FastAPI (local o Render). |
| `NEXT_PUBLIC_SUPABASE_URL` | Sí | URL de tu proyecto de Supabase (Project Settings → API). |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Sí | La `anon public` key de ese mismo proyecto — no la `service_role`, esa nunca va en el frontend. |
| `NEXT_PUBLIC_GOOGLE_MAPS_KEY` | No | Si la defines, la pantalla de entrega muestra un mapa embebido (Google Maps Embed API). Si la dejas vacía, muestra un botón "Abrir ruta en Google Maps" que funciona igual de bien para la demo y no depende de billing configurado. Puede ser la misma key que ya usa el backend (`GOOGLE_MAPS_API`), solo con el nombre distinto — ver más abajo. |

### Sobre `NEXT_PUBLIC_GOOGLE_MAPS_KEY` vs `GOOGLE_MAPS_API`

Es, muy probablemente, **la misma key de Google Maps Platform**, solo que:

- El backend (Python) la puede llamar como quiera (`GOOGLE_MAPS_API`, algo
  interno, nunca llega al navegador).
- El frontend (Next.js) **tiene que** usar un nombre que empiece con
  `NEXT_PUBLIC_` para que el navegador la pueda leer — es una regla de
  Next.js, no algo que se pueda evitar. No hay que "cambiar" la key en sí,
  solo agregar una variable de entorno nueva (`NEXT_PUBLIC_GOOGLE_MAPS_KEY`)
  con el mismo valor.
- Ojo: esa key necesita tener **"Maps Embed API" habilitada** en Google
  Cloud Console para que el `<iframe>` de `RouteMap.jsx` funcione. Si la
  sacaste para Places/Routes (lo que usa el backend), es probable que esa
  API en particular no esté prendida todavía — revísalo en
  **APIs & Services → Library** antes de asumir que ya funciona.

## Deploy en Render

Este frontend va como un **segundo Web Service** de Node, separado del
backend (que ya corre el suyo). Pasos:

1. Sube esta carpeta a tu repo de GitHub (puede ser el mismo repo del
   backend, en una carpeta hermana a `hackmty26/`, o un repo aparte —
   cualquiera funciona).
2. En Render: **New → Web Service** → conecta el repo.
3. Configura:
   - **Root Directory:** `optidelivery-frontend` (o donde haya quedado esta carpeta)
   - **Environment:** `Node`
   - **Build Command:** `npm install && npm run build`
   - **Start Command:** `npm run start`
4. En **Environment Variables** agrega:
   - `NEXT_PUBLIC_API_URL` = la URL pública que Render le dio a tu backend
     (ej. `https://hackmty26-backend.onrender.com`)
   - `NEXT_PUBLIC_GOOGLE_MAPS_KEY` = tu key, si decides usar el mapa embebido
5. Deploy. Render te da una URL pública para el frontend — esa es la que
   presentas en la demo.

**Antes de la demo final**, pide que se actualice el CORS del backend
(`api.py` / `app/main.py`) para permitir el dominio real de este frontend en
vez de `*`, como ya dice el pendiente en `FRONTEND_BRIEF.md`.

## Decisiones tomadas para que esto compile hoy (y qué falta en el backend)

El backend actual (ver `README.md` del repo principal) no expone todavía
algunos endpoints que el brief de frontend asumía. Para no bloquear el
desarrollo, el frontend toma estos atajos, documentados aquí para que sepas
exactamente qué reemplazar cuando el backend los agregue:

1. ~~**Login**~~ — Ya resuelto. Ver sección "Login" arriba: es Supabase Auth
   real + `user_profiles`, no `localStorage`. `CourierPicker.jsx` y
   `lib/courier.js` ya se eliminaron del proyecto.
2. **Aceptar un pedido puntual**: ya tiene UI (botón "Elegir esta ruta" por
   tarjeta, ver sección de arriba) que intenta un endpoint real primero y
   cae al algoritmo global si no existe. Sigue faltando el endpoint mismo
   del lado del backend (`POST /orders/{id}/accept` o como se llame) para
   que "elegir" garantice esa ruta y no solo lo intente.
3. **Avanzar el estado de una entrega** ("llegué", "recogí", "entregado"):
   no existe un endpoint para esto todavía. `lib/api.js` intenta llamar a
   `POST /assignments/{id}/status` por si ya se agregó; si responde error,
   el paso se guarda solo en `localStorage` (`pages/delivery/[id].js`) para
   que la demo no se trabe. Apenas exista el endpoint real, esto se conecta
   solo — no hay que tocar el resto de la pantalla.
4. **Historial de ganancias**: las cifras *acumuladas* (total ganado,
   entregas completadas, tiempo promedio, entregas tarde) ya son reales —
   viven en `user_profiles` y las actualiza el trigger de tu SQL. Lo que
   sigue siendo local es el detalle *entrega por entrega* (la listita con
   hora y payout de cada una), porque no hay endpoint para eso todavía;
   sigue en `localStorage` vía `lib/earnings.js`. Si el backend agrega un
   historial línea por línea, esa lista en `summary.js` se puede reemplazar
   por un `fetch`.
5. **Mapa**: se usa Google Maps Embed API si defines
   `NEXT_PUBLIC_GOOGLE_MAPS_KEY`; si no, un link directo a Google Maps.
   Ninguna de las dos formas requiere agregar una librería de mapas pesada
   al frontend (nada de Google Maps JS SDK ni Mapbox), lo cual mantiene el
   build rápido para hoy.

Ninguno de estos atajos rompe nada del lado del backend — son solo
compensaciones del lado del frontend mientras esos endpoints no existen.
