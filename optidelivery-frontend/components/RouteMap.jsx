export default function RouteMap({ origin, destination, apiKey }) {
  const hasCoords =
    origin && destination && origin.lat != null && destination.lat != null;

  if (!hasCoords) {
    return <div className="route-map route-map--empty">Ubicando la ruta…</div>;
  }

  if (!apiKey) {
    const mapsUrl = `https://www.google.com/maps/dir/?api=1&origin=${origin.lat},${origin.lng}&destination=${destination.lat},${destination.lng}`;
    return (
      <a
        className="route-map route-map--fallback"
        href={mapsUrl}
        target="_blank"
        rel="noreferrer"
      >
        Abrir ruta en Google Maps
      </a>
    );
  }

  const src = `https://www.google.com/maps/embed/v1/directions?key=${apiKey}&origin=${origin.lat},${origin.lng}&destination=${destination.lat},${destination.lng}&mode=driving`;

  return (
    <iframe
      className="route-map"
      src={src}
      loading="lazy"
      referrerPolicy="no-referrer-when-downgrade"
      allowFullScreen
      title="Ruta de la entrega"
    />
  );
}
