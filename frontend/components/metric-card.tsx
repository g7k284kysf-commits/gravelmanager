export function MetricCard({ label, value, unit, accent = false }: { label: string; value: string | number; unit?: string; accent?: boolean }) {
  return (
    <article className={`rounded-3xl p-6 shadow-card ${accent ? "bg-gravel" : "bg-white"}`}>
      <p className="text-xs font-bold uppercase tracking-[.2em] text-moss/50">{label}</p>
      <p className="mt-4 text-4xl font-black tracking-[-.05em]">{value}<span className="ml-1 text-base font-bold text-moss/40">{unit}</span></p>
    </article>
  );
}

