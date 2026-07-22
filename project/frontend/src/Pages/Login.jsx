import { useState } from "react";
import { supabase } from "../lib/supabase";
import "./Login.css";

export default function Login({ onSignup }) { {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);

    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    setLoading(false);

    if (error) {
      alert(error.message);
    } else {
      // No code needed here.
// Supabase automatically updates the session.
// App.jsx will detect it and show the dashboard.
if (error) {
  alert(error.message);
}
    }
  };

  return (
    <div className="login-page">
      <div className="overlay">

        <div className="brand">
          <div className="logo">M</div>
          <h1>MinutesAI</h1>
          <p>AI Meeting Intelligence Platform</p>
        </div>

        <div className="login-card">

          <h2>Welcome Back 👋</h2>
          <p>Login to continue</p>

          <form onSubmit={handleLogin}>

            <label>Email</label>

            <input
              type="email"
              placeholder="Enter Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

            <label>Password</label>

            <div className="password-box">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Enter Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />

              <span
                className="eye"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? "🙈" : "👁"}
              </span>
            </div>

            <button type="submit">
              {loading ? "Logging In..." : "Login"}
            </button>

          </form>

          <div className="bottom-text">
  Don't have an account?

  <span
    className="switch-link"
    onClick={onSignup}
  >
    Sign Up
  </span>
</div>
        </div>

      </div>
    </div>
  );
}
}