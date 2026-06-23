import { AppLayout } from "../components/AppLayout";

type PlaceholderPageProps = {
  title: string;
  description: string;
};

export function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <AppLayout>
      <div className="rounded-2xl bg-white p-8 shadow">
        <h1 className="text-3xl font-bold text-slate-900">{title}</h1>
        <p className="mt-3 text-slate-600">{description}</p>
      </div>
    </AppLayout>
  );
}
