function minutesUntil(iso) {
  const diffMs = new Date(iso).getTime() - Date.now();
  return Math.round(diffMs / 60000);
}

export default function OrderCard({ order, restaurant, onChoose, choosing }) {
  const minsLeft = minutesUntil(order.restaurant_deadline);
  const isUrgent = minsLeft <= 10;

  return (
    <div className="order-card">
      <div className="order-card-row">
        <div className="order-card-main">
          <h3>{restaurant?.name || "Restaurante"}</h3>
          <p className="order-card-meta">
            ${order.payout.toFixed(0)}
            {restaurant?.rating ? ` · ${restaurant.rating}★` : ""}
          </p>
        </div>
        <div
          className={`order-card-deadline ${
            isUrgent ? "order-card-deadline--urgent" : ""
          }`}
        >
          {minsLeft > 0 ? `${minsLeft} min` : "vence ya"}
        </div>
      </div>
      {onChoose && (
        <button
          type="button"
          className="btn-primary btn-choose-route"
          onClick={() => onChoose(order)}
          disabled={choosing}
        >
          {choosing ? "Eligiendo…" : "Elegir esta ruta"}
        </button>
      )}
    </div>
  );
}
