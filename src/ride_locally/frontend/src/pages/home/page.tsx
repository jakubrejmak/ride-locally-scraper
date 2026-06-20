import Layout from "../../components/Layout/Layout";
import Background from "../../components/Background/Background";

export default function Home() {
  return (
    <Layout>
      <Background />
      <div className="panel">
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.2em] text-accent-light/80">
          Dashboard
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-white">
          Welcome back
        </h1>
        <p className="mt-2 max-w-xl text-sm text-white/60">
          Placeholder home view
        </p>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {[
            { label: "Active targets", value: "—" },
            { label: "Last scrape", value: "—" },
            { label: "Pending jobs", value: "—" },
          ].map((card) => (
            <div key={card.label} className="card">
              <p className="text-sm text-white/50">{card.label}</p>
              <p className="mt-2 text-2xl font-semibold text-white">
                {card.value}
              </p>
            </div>
          ))}
        </div>
      </div>
    </Layout>
  );
}
