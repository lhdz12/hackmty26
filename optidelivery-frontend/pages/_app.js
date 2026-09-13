import { useEffect, useState, useCallback } from "react";
import Header from "../components/Header";
import BottomNav from "../components/BottomNav";
import AuthGate from "../components/AuthGate";
import CourierLinkGate from "../components/CourierLinkGate";
import { supabase } from "../lib/supabaseClient";
import { api } from "../lib/api";
import "../styles/globals.css";

export default function App({ Component, pageProps }) {
  const [mounted, setMounted] = useState(false);
  const [session, setSession] = useState(null);
  const [profile, setProfile] = useState(null);
  const [courier, setCourier] = useState(null);
  const [courierError, setCourierError] = useState(null);
  const [weather, setWeather] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(false);

  // Trae el perfil (user_profiles) y, para el courier, primero intenta
  // encontrar una fila en `couriers` con user_id == este usuario. Si no
  // existe todavia, la CREA automaticamente -- asi "mi vehiculo y mi
  // courier ID" quedan ligados a mi correo desde el primer login, sin
  // tener que elegir de una lista de couriers simulados. Si por lo que sea
  // el INSERT falla (ej. la tabla `couriers` en tu Supabase real pide
  // alguna columna extra que no estamos mandando), caemos de vuelta al
  // flujo manual de CourierLinkGate para no dejar a nadie bloqueado.
  const loadProfileAndCourier = useCallback(async (sessionUser) => {
    setLoadingProfile(true);
    setCourierError(null);
    const userId = sessionUser.id;

    const { data: profileData } = await supabase
      .from("user_profiles")
      .select("*")
      .eq("id", userId)
      .single();
    setProfile(profileData || null);

    try {
      const couriers = await api.getCouriers();
      const linked = couriers.find((c) => c.user_id === userId);

      if (linked) {
        setCourier(linked);
      } else {
        const vehicleType =
          sessionUser.user_metadata?.vehicle_type || "bicycle";

        const { data: created, error: insertError } = await supabase
          .from("couriers")
          .insert({
            user_id: userId,
            vehicle_type: vehicleType,
            status: "available",
            // Monterrey, como punto de partida razonable hasta que el
            // dispositivo del courier reporte su ubicacion real.
            current_lat: 25.6866,
            current_lng: -100.3161,
          })
          .select()
          .single();

        if (insertError) throw insertError;
        setCourier(created);
      }
    } catch (err) {
      setCourier(null);
      setCourierError(err.message);
    }

    setLoadingProfile(false);
  }, []);

  useEffect(() => {
    setMounted(true);

    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      if (data.session) loadProfileAndCourier(data.session.user);
    });

    const { data: listener } = supabase.auth.onAuthStateChange(
      (_event, newSession) => {
        setSession(newSession);
        if (newSession) {
          loadProfileAndCourier(newSession.user);
        } else {
          setProfile(null);
          setCourier(null);
        }
      }
    );

    return () => listener.subscription.unsubscribe();
  }, [loadProfileAndCourier]);

  useEffect(() => {
    let active = true;
    function poll() {
      api
        .getWeather()
        .then((w) => {
          if (active) setWeather(w);
        })
        .catch(() => {});
    }
    poll();
    const interval = setInterval(poll, 5 * 60 * 1000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  async function handleLogout() {
    await supabase.auth.signOut();
    setProfile(null);
    setCourier(null);
  }

  function handleLinked(linkedCourier) {
    setCourier(linkedCourier);
  }

  if (!mounted) {
    return <div className="app-loading">Cargando OptiDelivery…</div>;
  }

  if (!session) {
    return <AuthGate />;
  }

  if (loadingProfile) {
    return <div className="app-loading">Cargando tu perfil…</div>;
  }

  if (!courier) {
    return (
      <CourierLinkGate
        userId={session.user.id}
        autoProvisionError={courierError}
        onLinked={handleLinked}
      />
    );
  }

  return (
    <div className="app-shell">
      <Header
        weather={weather}
        courier={courier}
        profile={profile}
        onLogout={handleLogout}
      />
      <main className="app-main">
        <Component {...pageProps} courier={courier} profile={profile} />
      </main>
      <BottomNav />
    </div>
  );
}
