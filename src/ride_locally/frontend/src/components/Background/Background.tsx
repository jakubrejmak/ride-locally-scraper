export default function Background() {
  return (
    <div className="z-[-1] pointer-events-none absolute inset-0" aria-hidden>
      <div className="absolute inset-0 bg-stripes" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_0%,rgba(249,115,22,0.1),transparent_40%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_100%,rgba(251,146,60,0.06),transparent_35%)]" />
    </div>
  );
}
