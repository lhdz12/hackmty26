import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { supabase } from "../lib/supabaseClient";

// Este componente ya NO es el flujo normal: _app.js intenta crear un
// courier propio automaticamente en cuanto alguien entra (ligado a su
// user_id, con el vehiculo que eligio al registrarse). Esta pantalla solo
// aparece como RESPALDO si ese intento automatico falla -- por ejemplo, si
// tu tabla `couriers` en Supabase pide alguna columna obligatoria que el
// insert automatico no esta mandando. Aqui el courier puede, a mano,
// tomar uno de los registros simulados que sigan sin dueño para no
// quedarse bloqueado mientras arreglas el insert automatico.
export default function CourierLinkGate({ userId, autoProvisionError, onLinked }) {
  const [couriers, setCouriers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [linkingId, setLinkingId] = useState(null);

  useEffect(() => {
    api
      .getCouriers()
      .then((list) => setCouriers(list.filter((c) => !c.user_id)))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleLink(courier) {
    setLinkingId(courier.id);
    setError(null);
    const { error: updateError } = await supabase
      .from("couriers")
      .update({ user_id: userId })
      .eq("id", courier.id);
    setLinkingId(null);

    if (updateError) {
      setError(updateError.message);
      return;
    }
    onLinked({ ...courier, user_id: userId });
  }

  return (
    <div className="picker-screen">
      <div className="picker-card">
        <h1>Vincula tu vehículo</h1>
        <p className="picker-subtitle">
          No pudimos crear tu courier automáticamente
          {autoProvisionError ? ` (${autoProvisionError})` : ""}. Como
          respaldo, elige uno de los registros simulados que sigan libres —
          tu cuenta queda ligada a ese vehículo.
        </p>

        {loading && <p className="picker-status">Cargando couriers…</p>}
        {error && (
          <p className="picker-status picker-status--error">{error}</p>
        )}
        {!loading && !error && couriers.length === 0 && (
          <p className="picker-status">
            No hay couriers simulados libres para vincular ahora mismo.
            Pídele al equipo de backend que agregue más filas en `couriers`,
            o revisa por qué falló la creación automática.
          </p>
        )}

        <ul className="picker-list">
          {couriers.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className="picker-item"
                disabled={linkingId === c.id}
                onClick={() => handleLink(c)}
              >
                <span className="picker-item-vehicle">{c.vehicle_type}</span>
                <span className="picker-item-id">#{c.id.slice(0, 8)}</span>
                <span className="picker-item-status">
                  {linkingId === c.id ? "vinculando…" : c.status}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
