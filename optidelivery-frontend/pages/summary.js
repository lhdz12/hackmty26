import { useEffect, useState } from "react";
import { supabase } from "../lib/supabaseClient";
import { getCompletedDeliveries } from "../lib/earnings";

export default function Summary({ profile: initialProfile }) {
  const [profile, setProfile] = useState(initialProfile || null);
  const [deliveries, setDeliveries] = useState([]);

  useEffect(() => {
    setDeliveries(getCompletedDeliveries());

    // Volvemos a pedir el perfil fresco: el trigger de Postgres
    // (handle_assignment_completed) puede haber actualizado las cifras
    // despues de que _app.js cargo el perfil por ultima vez.
    supabase.auth.getSession().then(({ data }) => {
      const userId = data.session?.user?.id;
      if (!userId) return;
      supabase
        .from("user_profiles")
        .select("*")
        .eq("id", userId)
        .single()
        .then(({ data: fresh }) => {
          if (fresh) setProfile(fresh);
        });
    });
  }, []);

  const localTotalPayout = deliveries.reduce((sum, d) => sum + d.payout, 0);
  const avgMinutes =
    profile && profile.completed_deliveries > 0
      ? Math.round(profile.total_minutes_worked / profile.completed_deliveries)
      : null;

  return (
    <div className="summary-screen">
      <h1>Tus ganancias</h1>

      <div className="summary-stats">
        <div className="stat-card">
          <p className="stat-value">
            {profile?.completed_deliveries ?? deliveries.length}
          </p>
          <p className="stat-label">Entregas completadas</p>
        </div>
        <div className="stat-card">
          <p className="stat-value">
            $
            {(profile?.total_earnings ?? localTotalPayout).toFixed(0)}
          </p>
          <p className="stat-label">Payout total</p>
        </div>
      </div>

      {profile && (
        <div className="summary-stats">
          <div className="stat-card">
            <p className="stat-value">
              {avgMinutes != null ? `${avgMinutes} min` : "—"}
            </p>
            <p className="stat-label">Tiempo promedio por entrega</p>
          </div>
          <div className="stat-card">
            <p className="stat-value">{profile.late_deliveries}</p>
            <p className="stat-label">Entregas tarde</p>
          </div>
        </div>
      )}

      {deliveries.length === 0 ? (
        <p className="empty-state-hint">
          Todavia no completas ninguna entrega desde este dispositivo.
        </p>
      ) : (
        <ul className="delivery-history">
          {deliveries
            .slice()
            .reverse()
            .map((d) => (
              <li key={d.assignmentId}>
                <span>${d.payout.toFixed(0)}</span>
                <span>
                  {new Date(d.deliveredAt).toLocaleTimeString("es-MX")}
                </span>
              </li>
            ))}
        </ul>
      )}

      <p className="summary-note">
        Las cifras de arriba (entregas completadas, payout total, tiempo
        promedio, entregas tarde) vienen de tu perfil real en Supabase
        (`user_profiles`), que el backend actualiza solo cuando una
        asignacion pasa a "completed". El detalle entrega-por-entrega de la
        lista de abajo sigue guardandose solo en este dispositivo, porque el
        backend todavia no expone un historial linea-por-linea — solo el
        acumulado.
      </p>
    </div>
  );
}
