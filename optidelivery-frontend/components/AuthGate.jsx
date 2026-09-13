import { useState } from "react";
import { supabase } from "../lib/supabaseClient";

export default function AuthGate() {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [age, setAge] = useState("");
  const [vehicleType, setVehicleType] = useState("bicycle");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  function switchMode(next) {
    setMode(next);
    setError(null);
    setNotice(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setLoading(true);

    try {
      if (mode === "signup") {
        const { error: signUpError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            // Esto llega como raw_user_meta_data al trigger de Postgres
            // (handle_new_user) que crea la fila en user_profiles.
            data: {
              first_name: firstName,
              last_name: lastName,
              age: age ? Number(age) : null,
              vehicle_type: vehicleType,
            },
          },
        });
        if (signUpError) throw signUpError;
        setNotice(
          "Cuenta creada. Si tu proyecto de Supabase pide confirmar el correo, revisa tu bandeja antes de poder entrar."
        );
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (signInError) throw signInError;
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="picker-screen">
      <div className="picker-card">
        <h1>OptiDelivery</h1>
        <p className="picker-subtitle">
          {mode === "login"
            ? "Entra con tu correo y contraseña."
            : "Crea tu cuenta de courier."}
        </p>

        <div className="auth-tabs">
          <button
            type="button"
            className={`auth-tab ${mode === "login" ? "auth-tab--active" : ""}`}
            onClick={() => switchMode("login")}
          >
            Entrar
          </button>
          <button
            type="button"
            className={`auth-tab ${mode === "signup" ? "auth-tab--active" : ""}`}
            onClick={() => switchMode("signup")}
          >
            Crear cuenta
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === "signup" && (
            <>
              <div className="auth-row">
                <input
                  className="auth-input"
                  placeholder="Nombre"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  required
                />
                <input
                  className="auth-input"
                  placeholder="Apellido"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  required
                />
              </div>
              <input
                className="auth-input"
                type="number"
                min="16"
                max="100"
                placeholder="Edad"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                required
              />
              <select
                className="auth-input"
                value={vehicleType}
                onChange={(e) => setVehicleType(e.target.value)}
              >
                <option value="bicycle">Bicicleta</option>
                <option value="motorcycle">Moto</option>
                <option value="car">Carro</option>
              </select>
            </>
          )}

          <input
            className="auth-input"
            type="email"
            placeholder="Correo"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className="auth-input"
            type="password"
            placeholder="Contraseña"
            autoComplete={mode === "signup" ? "new-password" : "current-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={6}
            required
          />

          {error && (
            <p className="picker-status picker-status--error">{error}</p>
          )}
          {notice && <p className="picker-status">{notice}</p>}

          <button
            type="submit"
            className="btn-primary btn-big"
            disabled={loading}
          >
            {loading
              ? "Un momento…"
              : mode === "signup"
              ? "Crear cuenta"
              : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
