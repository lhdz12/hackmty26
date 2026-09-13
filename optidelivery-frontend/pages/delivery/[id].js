import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/router";
import { api } from "../../lib/api";
import StatusStepper, { DELIVERY_STEPS } from "../../components/StatusStepper";
import RouteMap from "../../components/RouteMap";
import { addCompletedDelivery } from "../../lib/earnings";

const LOCAL_STATUS_KEY_PREFIX = "optidelivery_status_";

export default function DeliveryDetail({ courier }) {
  const router = useRouter();
  const { id } = router.query;

  const [assignment, setAssignment] = useState(null);
  const [order, setOrder] = useState(null);
  const [restaurant, setRestaurant] = useState(null);
  const [status, setStatus] = useState("assigned");
  const [error, setError] = useState(null);

  const refresh = useCallback(() => {
    if (!id) return;
    api
      .getState()
      .then((state) => {
        const found = state.active_assignments.find((a) => a.id === id);
        setAssignment(found || null);
        if (found) {
          const ord =
            state.open_orders.find((o) => o.id === found.order_id) || null;
          setOrder(ord);
          if (ord) {
            setRestaurant(
              state.restaurants.find((r) => r.id === ord.restaurant_id) || null
            );
          }
        }
      })
      .catch((err) => setError(err.message));
  }, [id]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  useEffect(() => {
    if (!id || typeof window === "undefined") return;
    const stored = window.localStorage.getItem(LOCAL_STATUS_KEY_PREFIX + id);
    if (stored) setStatus(stored);
  }, [id]);

  function persistStatus(next) {
    setStatus(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LOCAL_STATUS_KEY_PREFIX + id, next);
    }
  }

  async function handleAdvance() {
    const keys = DELIVERY_STEPS.map((s) => s.key);
    const nextIndex = keys.indexOf(status) + 1;
    const next = keys[nextIndex];
    if (!next) return;

    // Intenta avisarle al backend. Si el endpoint todavia no existe,
    // igual avanzamos localmente para no trabar la demo.
    await api.updateAssignmentStatus(id, next);
    persistStatus(next);

    if (next === "delivered" && order) {
      addCompletedDelivery({
        assignmentId: id,
        payout: order.payout,
        deliveredAt: new Date().toISOString(),
      });
      router.push("/summary");
    }
  }

  if (error) {
    return <div className="empty-state">Error: {error}</div>;
  }

  if (!assignment || !order) {
    return <div className="empty-state">Cargando tu entrega…</div>;
  }

  const goingToPickup = status === "assigned" || status === "at_restaurant";
  const destination = goingToPickup
    ? {
        lat: order.pickup_lat ?? restaurant?.latitude,
        lng: order.pickup_lng ?? restaurant?.longitude,
      }
    : { lat: order.dropoff_lat, lng: order.dropoff_lng };

  return (
    <div className="delivery-screen">
      <h1>{restaurant?.name || "Entrega en curso"}</h1>
      <p className="delivery-payout">Pagas ${order.payout.toFixed(0)}</p>

      <RouteMap
        origin={{ lat: courier.current_lat, lng: courier.current_lng }}
        destination={destination}
        apiKey={process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY}
      />

      <StatusStepper status={status} onAdvance={handleAdvance} />

      <p className="delivery-deadline">
        Deadline del restaurante:{" "}
        {new Date(order.restaurant_deadline).toLocaleTimeString("es-MX")}
      </p>
    </div>
  );
}
