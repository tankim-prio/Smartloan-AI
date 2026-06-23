import { AppLayout } from "../../components/AppLayout";

export function UserHomePage() {
  return (
    <AppLayout>
      <div>
        <h1 className="text-3xl font-bold text-slate-900">User Home</h1>
        <p className="mt-2 text-slate-600">
          Submit application, track status, and check notifications.
        </p>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl bg-white p-6 shadow">
            <p className="text-sm font-medium text-slate-500">Application Status</p>
            <h2 className="mt-3 text-2xl font-bold text-slate-900">Not Submitted</h2>
          </div>

          <div className="rounded-2xl bg-white p-6 shadow">
            <p className="text-sm font-medium text-slate-500">Latest Notification</p>
            <h2 className="mt-3 text-2xl font-bold text-slate-900">No updates</h2>
          </div>

          <div className="rounded-2xl bg-white p-6 shadow">
            <p className="text-sm font-medium text-slate-500">Next Step</p>
            <h2 className="mt-3 text-2xl font-bold text-slate-900">Apply</h2>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
