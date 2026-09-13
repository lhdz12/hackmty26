import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api } from "../lib/api";
import OrderCard from "../components/OrderCard";

export default function Home({ courier }) {
  const [state, setState] = useState(null);
  const [error, setError] = useState(null);
  const [searching, setSearching] = useState(false);
  const [choosingId, setChoosingId] = useState(null);
  const [notice, setNotice] = useState(null);

  const refresh = useCallback(() => {
    api.getState().then(setState).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  async function handleSearch() {
    setSearching(true);
    setError(null);
    setNotice(null);
    try {
      await api.runAssignment();
      refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setSearching(false);
    }
  }

  // El courier eligio UN pedido puntual en su tarjeta. Primero intentamos
  // un endpoint de aceptacion directa; si el backend todavia no lo tiene,
  // caemos al algoritmo global (unica via real de asignacion hoy) y le
  // decimos, con honestidad, si le toco justo ese pedido o uno distinto --
  // asi la demo nunca miente sobre que se eligio.
  async function handleChooseOrder(order) {
    setChoosingId(order.id);
    setError(null);
    setNotice(null);
    try {
      const attempt = await api.acceptOrder(order.id);

      if (attempt.ok) {
        setNotice("¡Listo! Esa entrega ya es tuya.");
        refresh();
        return;
      }

      // Respaldo: el backend solo asigna via el algoritmo global.
      await api.runAssignment();
      const fresh = await api.getState();
      setState(fresh);

      const myAssignment = fresh.active_assignments.find(
        (a) => a.courier_id === courier.id
      );

      if (myAssignment?.order_id === order.id) {
        setNotice("¡Listo! Te tocó justo la ruta que elegiste.");
      } else if (myAssignment) {
        setNotice(
          "El algoritmo de asignación ya te dio otra ruta distinta a la que elegiste -- el backend todavía no soporta aceptar un pedido puntual, así que por ahora reparte por su cuenta."
        );
      } else {
        setNotice(
          "Se corrió la asignación pero no te tocó ninguna ruta esta vez. Intenta de nuevo en unos segundos."
        );
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setChoosingId(null);
    }
  }

  if (error) {
    return (
      <div className="empty-state">
        <h2>No se pudo conectar con el backend</h2>
        <p>{error}</p>
        <p className="empty-state-hint">
          Revisa que NEXT_PUBLIC_API_URL apunte a tu backend en Render.
        </p>
      </div>
    );
  }

  if (!state) {
    return <div className="empty-state">Buscando pedidos cerca de ti…</div>;
  }

  const myAssignment = state.active_assignments.find(
    (a) => a.courier_id === courier.id
  );
  const restaurantsById = Object.fromEntries(
    state.restaurants.map((r) => [r.id, r])
  );

  return (
    <div className="home-screen">
      {myAssignment && (
        <Link href={`/delivery/${myAssignment.id}`} className="active-banner">
          <div>
            <p className="active-banner-title">Tienes una entrega activa</p>
            <p className="active-banner-subtitle">
              Toca para ver la ruta y los pasos
            </p>
          </div>
          <span className="active-banner-arrow">›</span>
        </Link>
      )}

      <div className="home-header-row">
        <h1>Rutas disponibles ahora</h1>
        <button
          type="button"
          className="btn-primary"
          onClick={handleSearch}
          disabled={searching || Boolean(myAssignment)}
        >
          {searching ? "Buscando…" : "Buscar asignación"}
        </button>
      </div>

      {notice && <p className="home-notice">{notice}</p>}

      {state.open_orders.length === 0 && (
        <p className="empty-state-hint">No hay pedidos abiertos ahora mismo.</p>
      )}

      <div className="order-list">
        {state.open_orders.map((order) => (
          <OrderCard
            key={order.id}
            order={order}
            restaurant={restaurantsById[order.restaurant_id]}
            onChoose={myAssignment ? null : handleChooseOrder}
            choosing={choosingId === order.id}
          />
        ))}
      </div>
    </div>
  );
}
