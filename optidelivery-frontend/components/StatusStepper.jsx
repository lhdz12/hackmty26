export const DELIVERY_STEPS = [
  { key: "assigned", label: "Yendo al restaurante", action: "Llegue al restaurante" },
  { key: "at_restaurant", label: "Esperando el pedido", action: "Recogi el pedido" },
  { key: "picked_up", label: "En camino al cliente", action: "Entregado" },
  { key: "delivered", label: "Entregado", action: null },
];

export default function StatusStepper({ status, onAdvance }) {
  const index = DELIVERY_STEPS.findIndex((s) => s.key === status);
  const current = DELIVERY_STEPS[index] || DELIVERY_STEPS[0];

  return (
    <div className="stepper">
      <div className="stepper-track">
        {DELIVERY_STEPS.map((s, i) => (
          <div
            key={s.key}
            className={`stepper-dot ${i <= index ? "stepper-dot--done" : ""}`}
          />
        ))}
      </div>
      <p className="stepper-label">{current.label}</p>
      {current.action && (
        <button type="button" className="btn-primary btn-big" onClick={onAdvance}>
          {current.action}
        </button>
      )}
    </div>
  );
}
