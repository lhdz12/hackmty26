export default function WeatherBadge({ weather }) {
  if (!weather) return null;

  const isRain = Boolean(weather.rain);
  const temp = Math.round(weather.temperature_c);

  return (
    <span className={`weather-badge ${isRain ? "weather-badge--rain" : ""}`}>
      <span className="weather-dot" aria-hidden="true" />
      {temp}°C · {isRain ? "lluvia" : weather.weather_description || "despejado"}
    </span>
  );
}
