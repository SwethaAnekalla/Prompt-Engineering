import { useState } from "react";

import { supabase } from "../lib/supabase";
import "./Signup.css";



export default function Signup({ onLogin }) { {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [loading, setLoading] = useState(false);

  async function handleSignup(e) {
    e.preventDefault();

    if (password !== confirmPassword) {
      alert("Passwords do not match.");
      return;
    }

    setLoading(true);

    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: name,
        },
      },
    });

    setLoading(false);

    if (error) {
      alert(error.message);
    } else {
     alert("Account created successfully. Please verify your email before logging in.");
onLogin();
      setName("");
      setEmail("");
      setPassword("");
      setConfirmPassword("");
    }
  }

  return (
    <div className="signup-page">
      <div className="overlay">

        <div className="brand">
          <div className="logo">M</div>
          <h1>MinutesAI</h1>
          <p>AI Meeting Intelligence Platform</p>
        </div>

        <div className="signup-card">

          <h2>Create Account 🚀</h2>
          <p>Join MinutesAI today</p>

          <form onSubmit={handleSignup}>

            <label>Full Name</label>

            <input
              type="text"
              placeholder="Enter Full Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />

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
                placeholder="Create Password"
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

            <label>Confirm Password</label>

            <div className="password-box">
              <input
                type={showConfirmPassword ? "text" : "password"}
                placeholder="Confirm Password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />

              <span
                className="eye"
                onClick={() =>
                  setShowConfirmPassword(!showConfirmPassword)
                }
              >
                {showConfirmPassword ? "🙈" : "👁"}
              </span>
            </div>

            <button type="submit">
              {loading ? "Creating Account..." : "Create Account"}
            </button>

          </form>

         <div className="bottom-text">
  Already have an account?

  <span
    className="switch-link"
    onClick={onLogin}
  >
    Login
  </span>
</div>

        </div>

      </div>
    </div>
  );
}
}