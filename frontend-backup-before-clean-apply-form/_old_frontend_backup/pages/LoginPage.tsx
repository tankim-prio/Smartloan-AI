import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function LoginPage() {
  const { user, login } = useAuth();

  const [email, setEmail] = useState("admin@smartloan.ai");
  const [password, setPassword] = useState("12345678");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) {
    return <Navigate to={user.role === "admin" ? "/admin/dashboard" : "/user/home"} replace />;
  }

  const handleLogin = async () => {
    setError("");
    setLoading(true);

    try {
      await login(email, password);
    } catch {
      setError("Invalid email or password. Make sure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-6">
      <section className="w-full max-w-md rounded-3xl bg-white p-8 shadow-xl">
        <p className="text-sm font-semibold text-blue-700">Part 3: Protected Dashboard</p>

        <h1 className="mt-3 text-4xl font-bold text-slate-900">SmartLoan AI</h1>
        <p className="mt-2 text-slate-600">Login to continue to your dashboard.</p>

        <div className="mt-6 space-y-4">
          <div>
            <label className="text-sm font-semibold text-slate-700">Email</label>
            <input
              className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-blue-600"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div>
            <label className="text-sm font-semibold text-slate-700">Password</label>
            <input
              className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-blue-600"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          {error && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}

          <button
            onClick={handleLogin}
            disabled={loading}
            className="w-full rounded-xl bg-blue-700 px-4 py-3 font-semibold text-white hover:bg-blue-800 disabled:opacity-60"
          >
            {loading ? "Logging in..." : "Login"}
          </button>
        </div>

        <div className="mt-6 grid gap-3">
          <button
            onClick={() => {
              setEmail("admin@smartloan.ai");
              setPassword("12345678");
            }}
            className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-left text-sm text-blue-900 hover:bg-blue-100"
          >
            Use Admin: admin@smartloan.ai / 12345678
          </button>

          <button
            onClick={() => {
              setEmail("user@smartloan.ai");
              setPassword("12345678");
            }}
            className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-left text-sm text-green-900 hover:bg-green-100"
          >
            Use User: user@smartloan.ai / 12345678
          </button>
        </div>
      </section>
    </main>
  );
}
