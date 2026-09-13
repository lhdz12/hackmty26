const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getJSON(path) {
  const res = await fetch(`${BASE_URL}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`${path} respondio ${res.status}`);
  }
  return res.json();
}

export const api = {
  getState: () => getJSON("/state"),
  getOpenOrders: () => getJSON("/orders/open"),
  getCouriers: () => getJSON("/couriers"),
  getRestaurants: () => getJSON("/restaurants"),
  getActiveAssignments: () => getJSON("/assignments/active"),
  getWeather: () => getJSON("/weather/latest"),

  runAssignment: async () => {
    const res = await fetch(`${BASE_URL}/assignment/run`, { method: "POST" });
    if (!res.ok) {
      throw new Error(`assignment/run respondio ${res.status}`);
    }
    return res.json();
  },

  // El backend actual solo asigna por corrida global del algoritmo hungaro
  // (POST /assignment/run) -- no hay forma de decir "quiero ESTE pedido".
  // Intentamos un endpoint de aceptacion puntual por si ya lo agregaron;
  // si no existe, devolvemos { ok: false } y quien llama decide como
  // resolverlo (ver handleChooseOrder en pages/index.js).
  acceptOrder: async (orderId) => {
    try {
      const res = await fetch(`${BASE_URL}/orders/${orderId}/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error("endpoint no disponible todavia");
      return { ok: true, data: await res.json() };
    } catch (err) {
      return { ok: false };
    }
  },

  // El backend actual (ver README del repo) todavia no expone un endpoint
  // para mover una entrega entre pasos (llegue / recogi / entregue).
  // Intentamos llamarlo por si ya lo agregaron; si no existe, devolvemos
  // { ok: false, local: true } y la pantalla sigue funcionando con estado
  // guardado en el dispositivo para no bloquear la demo.
  updateAssignmentStatus: async (assignmentId, status) => {
    try {
      const res = await fetch(`${BASE_URL}/assignments/${assignmentId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error("endpoint no disponible todavia");
      return res.json();
    } catch (err) {
      return { ok: false, local: true };
    }
  },
};
