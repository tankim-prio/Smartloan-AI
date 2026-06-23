import { AppLayout } from "../../components/AppLayout";

export function AdminDashboardPage() {
  const cards = [
    ["Total Applications", "0"],
    ["Pending Reviews", "0"],
    ["Approved", "0"],
    ["Rejected", "0"],
  ];

  return (
    <AppLayout>
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Admin Dashboard</h1>
        <p className="mt-2 text-slate-600">
          Overview of applications, reviews, ML predictions, and reports.
        </p>

        <div className="mt-6 grid gap-4 md:grid-cols-4">
          {cards.map(([title, value]) => (
            <div key={title} className="rounded-2xl bg-white p-6 shadow">
              <p className="text-sm font-medium text-slate-500">{title}</p>
              <h2 className="mt-3 text-3xl font-bold text-slate-900">{value}</h2>
            </div>
          ))}
        </div>

        <div className="mt-6 rounded-2xl bg-white p-6 shadow">
          <h2 className="text-xl font-bold text-slate-900">Next Work</h2>
          <p className="mt-2 text-slate-600">
            Part 4 will build the Apply Page multi-step application form.
          </p>
        </div>
      </div>
    </AppLayout>
  );
}
