import WeatherBadge from "./WeatherBadge";

export default function Header({ weather, courier, profile, onLogout }) {
  return (
    <header className="app-header">
      <span className="brand">OptiDelivery</span>
      <div className="header-right">
        <WeatherBadge weather={weather} />
        {courier && (
          <span className="courier-chip">
            {courier.vehicle_type} · #{courier.id.slice(0, 4)}
          </span>
        )}
        <button
          type="button"
          className="logout-btn"
          onClick={onLogout}
          aria-label="Cerrar sesión"
        >
          {profile?.first_name || "Salir"} ⏻
        </button>
      </div>
    </header>
  );
}
