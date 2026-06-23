import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

type MenuItem = {
  label: string;
  path: string;
};

const adminMenu: MenuItem[] = [
  { label: "Dashboard", path: "/admin/dashboard" },
  { label: "Apply", path: "/apply" },
  { label: "Reviews", path: "/admin/reviews" },
  { label: "ML Model", path: "/admin/ml-model" },
  { label: "Reports", path: "/admin/reports" },
  { label: "AI Pilot", path: "/admin/ai-pilot" },
  { label: "Create Account", path: "/admin/create-account" },
];

const userMenu: MenuItem[] = [
  { label: "Home", path: "/user/home" },
  { label: "Apply", path: "/apply" },
  { label: "Notification", path: "/user/notifications" },
];

export function AppLayout({ children }: { children: ReactNode }) {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  const menu = user?.role === "admin" ? adminMenu : userMenu;

  const handleSignOut = () => {
    signOut();
    navigate("/login");
  };

  return (
    <main className="min-h-screen bg-slate-100">
      <div className="flex min-h-screen">
        <aside className="hidden w-72 bg-slate-950 p-6 text-white lg:block">
          <div>
            <h1 className="text-2xl font-bold">SmartLoan AI</h1>
            <p className="mt-1 text-sm text-slate-400">
              {user?.role === "admin" ? "Admin Panel" : "User Panel"}
            </p>
          </div>

          <nav className="mt-8 space-y-2">
            {menu.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `block rounded-xl px-4 py-3 text-sm font-medium transition ${
                    isActive
                      ? "bg-blue-600 text-white"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <button
            onClick={handleSignOut}
            className="mt-8 w-full rounded-xl bg-red-600 px-4 py-3 font-semibold text-white hover:bg-red-700"
          >
            Sign out
          </button>
        </aside>

        <section className="flex-1">
          <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
            <div>
              <p className="text-sm text-slate-500">Logged in as</p>
              <h2 className="font-bold text-slate-900">{user?.full_name}</h2>
            </div>

            <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700">
              {user?.role.toUpperCase()}
            </div>
          </header>

          <div className="p-6">{children}</div>
        </section>
      </div>
    </main>
  );
}
